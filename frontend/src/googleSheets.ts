import type { SurveyRow } from "./types";

const SCOPES = "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive.file";
const SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets";

interface TokenResponse {
  access_token?: string;
  error?: string;
  error_description?: string;
}

interface TokenClient {
  requestAccessToken: (options?: { prompt?: string }) => void;
}

interface GoogleIdentity {
  oauth2: {
    initTokenClient: (config: {
      client_id: string;
      scope: string;
      callback: (response: TokenResponse) => void;
    }) => TokenClient;
  };
}

declare global {
  interface Window {
    google?: { accounts: GoogleIdentity };
  }
}

function getAccessToken(): Promise<string> {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  if (!clientId) {
    return Promise.reject(
      new Error("VITE_GOOGLE_CLIENT_ID is not configured. Add your Google OAuth Web client ID to frontend/.env."),
    );
  }
  if (!window.google?.accounts) {
    return Promise.reject(new Error("Google sign-in is still loading. Please try again."));
  }

  return new Promise((resolve, reject) => {
    const client = window.google!.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: SCOPES,
      callback: (response) => {
        if (response.access_token) resolve(response.access_token);
        else reject(new Error(response.error_description || response.error || "Google authorization failed"));
      },
    });
    client.requestAccessToken({ prompt: "consent" });
  });
}

async function googleFetch<T>(url: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error?.message || "Google Sheets request failed");
  }
  return response.json() as Promise<T>;
}

export async function createGoogleSheet(rows: SurveyRow[]): Promise<string> {
  const token = await getAccessToken();
  const timestamp = new Intl.DateTimeFormat("sv-SE", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date());
  const spreadsheet = await googleFetch<{ spreadsheetId: string; spreadsheetUrl: string }>(
    SHEETS_API,
    token,
    {
      method: "POST",
      body: JSON.stringify({ properties: { title: `Cowell OCR - ${timestamp}` } }),
    },
  );

  const values = [
    ["フロア", "設置場所", "器具品番", "既設商品名", "写真", "数量", "備考"],
    ...rows.map((row) => [
      row.floor,
      row.location,
      row.fixture_model,
      row.existing_product,
      "",
      row.quantity,
      row.notes,
    ]),
  ];
  await googleFetch(
    `${SHEETS_API}/${spreadsheet.spreadsheetId}/values/A1?valueInputOption=USER_ENTERED`,
    token,
    { method: "PUT", body: JSON.stringify({ values }) },
  );
  await googleFetch(`${SHEETS_API}/${spreadsheet.spreadsheetId}:batchUpdate`, token, {
    method: "POST",
    body: JSON.stringify({
      requests: [{ repeatCell: {
        range: { sheetId: 0, startRowIndex: 0, endRowIndex: 1 },
        cell: { userEnteredFormat: { textFormat: { bold: true } } },
        fields: "userEnteredFormat.textFormat.bold",
      } }],
    }),
  });
  return spreadsheet.spreadsheetUrl;
}
