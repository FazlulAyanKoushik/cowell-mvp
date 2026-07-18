# 🚀 GitHub Pages Deployment Guide — Cowell OCR MVP (POC Demo)

> **Target audience:** You want to show your CEO a working prototype **right now** without spending money on AWS.
> **What you get:** A live URL like `https://yourname.github.io/cowell-mvp/` that your CEO can open on any device.
> **Cost:** **$0** (GitHub Pages is free).

---

## ⚠️ Important Limitations — Read This First

GitHub Pages can only serve **static files** (HTML, CSS, JavaScript). It **cannot** run a Python backend.

This means:

| Feature | Works? | Why |
|---------|--------|-----|
| ✅ View the upload page | ✅ Yes | It's static HTML |
| ✅ Navigation between pages | ✅ Yes | React Router handles this client-side |
| ✅ Show the app layout, form, buttons | ✅ Yes | Everything is in the frontend code |
| ❌ **Upload a PDF** | ❌ No | Needs the backend to process the file |
| ❌ **Run OCR** | ❌ No | Needs the Python backend + Gemini API |
| ❌ **Register to Google Sheet** | ❌ No | Needs the backend |

**But it's still useful for a CEO demo:**

1. **Show the UI/UX flow** — all 4 pages, the upload zone, the edit table, the done page
2. **Demonstrate the concept** — "This is what the tool looks like. Upload PDFs here, edit data here, sheets are created here"
3. **Show the edit page with mock data** — you can pre-load sample data to show the table working
4. **Get buy-in before investing in backend deployment** — CEO sees the vision, approves Phase 2

> 💡 **Better alternative for a live demo:** If your CEO wants to see it fully working, use the **AWS deployment guides** (`deploy-aws-console.md` or `deploy-aws-cli.md`) — they deploy the full stack including the backend.

---

## Table of Contents

1. [What We'll Build](#1-what-well-build)
2. [Prerequisites](#2-prerequisites)
3. [Step 1: Create a GitHub Repository](#3-step-1-create-a-github-repository)
4. [Step 2: Configure the Frontend for GitHub Pages](#4-step-2-configure-the-frontend-for-github-pages)
5. [Step 3: Add Mock Data for the Demo](#5-step-3-add-mock-data-for-the-demo)
6. [Step 4: Build and Deploy](#6-step-4-build-and-deploy)
7. [Step 5: Enable GitHub Pages](#7-step-5-enable-github-pages)
8. [Bonus: Auto-Deploy on Every Push](#8-bonus-auto-deploy-on-every-push)
9. [Troubleshooting](#9-troubleshooting)
10. [What to Show Your CEO](#10-what-to-show-your-ceo)

---

## 1. What We'll Build

```
                    ┌──────────────────────────┐
                    │    GitHub Pages           │
                    │  (free static hosting)    │
                    │                          │
                    │  https://yourname.github. │
                    │  io/cowell-mvp/           │
                    │                          │
                    │  ┌────────────────────┐   │
                    │  │  React SPA         │   │
                    │  │  - UploadPage (UI) │   │
                    │  │  - ProcessPage (UI)│   │
                    │  │  - EditPage (UI)   │   │
                    │  │  - DonePage (UI)   │   │
                    │  └────────────────────┘   │
                    └──────────────────────────┘

  (Backend: NOT deployed — demo shows UI only)
```

---

## 2. Prerequisites

1. ✅ A **GitHub account** — [github.com](https://github.com)
2. ✅ **Git** installed — check with:
   ```bash
   git --version
   ```
3. ✅ **Node.js** installed — check with:
   ```bash
   node --version  # Should be 18+ or 22+
   npm --version
   ```
4. ✅ This project on your computer:
   ```
   E:\Projects\AONE Properties\cowell-mvp
   ```

---

## 3. Step 1: Create a GitHub Repository

A repository is like a folder on GitHub that holds your code.

### 3.1 — Log into GitHub

Go to [github.com](https://github.com) and log in.

### 3.2 — Create a New Repository

1. Click the **"+"** icon in the top-right corner (next to your profile picture)
2. Click **"New repository"**

   ```
   ┌──────────────────────────────────────────────────┐
   │  Owner: [yourname ▼]                             │
   │                                                  │
   │  Repository name: [cowell-mvp          ]         │
   │                                                  │
   │  Description (optional): Cowell OCR MVP — POC    │
   │                                                  │
   │  ○ Public    ● Private                           │
   │                                                  │
   │  ☐ Add a README file                             │
   │  ☐ Add .gitignore                                │
   │  ☐ Choose a license                              │
   │                                                  │
   │  [Create repository]                             │
   └──────────────────────────────────────────────────┘
   ```

3. **Repository name:** `cowell-mvp`
4. **Description:** `Cowell OCR MVP — POC demo`
5. **Visibility:** Choose **Private** (for CEO demo) or **Public** (if you want anyone to see it)
   - > 💡 **Recommendation:** Start with **Private**. You can make it public later.
6. **DO NOT** check "Add a README file", "Add .gitignore", or "Choose a license"
   - (We already have these locally, checking them will cause merge conflicts)
7. Click **"Create repository"**

After creation, GitHub shows you setup instructions. Keep this page open — we'll use the commands in Step 4.

### 3.3 — Push Your Code to GitHub

Now we connect your local project to the GitHub repository.

Open **Git Bash** in your project folder:

```bash
cd "E:\Projects\AONE Properties\cowell-mvp"
```

**If this is a fresh start (no remote yet):**

```bash
# Check if you already have a remote
git remote -v
# If it shows nothing, add the remote:
git remote add origin https://github.com/YOUR_USERNAME/cowell-mvp.git

# Push to GitHub
git branch -M main
git push -u origin main
```

> Replace `YOUR_USERNAME` with your actual GitHub username.
> If you get an authentication error, see [Troubleshooting](#9-troubleshooting) for GitHub token setup.

---

## 4. Step 2: Configure the Frontend for GitHub Pages

The frontend needs a few changes to work correctly on GitHub Pages.

### 4.1 — Update `vite.config.ts`

GitHub Pages serves your site at a **subfolder** (e.g., `https://yourname.github.io/cowell-mvp/`). We need to tell Vite to use relative paths.

Open `frontend/vite.config.ts` and replace its content:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // ── GitHub Pages needs relative base ──────────────
  // Without this, assets look for /assets/index.js
  // but they should look for /cowell-mvp/assets/index.js
  base: "./",
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

> **What `base: "./"` does:** It makes all paths relative to the current folder instead of the root. This is required for GitHub Pages subfolder hosting.

### 4.2 — Update the API Client to Work Offline

Since there's no backend on GitHub Pages, API calls will fail. We need to make the app gracefully handle this so it still shows the UI.

Open `frontend/src/api/client.ts` and **add this at the bottom**:

```typescript
// ── GitHub Pages demo mode ──────────────────────────────────
// When deployed to GitHub Pages, there's no backend.
// These mock functions let the UI show sample data.

export interface DemoConfig {
  enabled: boolean;
  mockRows: import("../types").SurveyRow[];
}

let _demoConfig: DemoConfig = {
  enabled: false,
  mockRows: [],
};

export function enableDemoMode(config: DemoConfig) {
  _demoConfig = config;
}

export function isDemoMode(): boolean {
  return _demoConfig.enabled;
}

export function getDemoRows(): import("../types").SurveyRow[] {
  return _demoConfig.mockRows;
}
```

### 4.3 — Add a Demo Hook (For Pre-Populated Data)

Create a new file `frontend/src/hooks/useDemo.ts`:

```typescript
/**
 * Demo mode hook — provides mock data when deployed to GitHub Pages
 * without a backend.
 */

import { useEffect, useState } from "react";
import { enableDemoMode, isDemoMode, getDemoRows } from "../api/client";
import type { SurveyRow } from "../types";

export interface DemoState {
  isDemo: boolean;
  sessionId: string;
  rows: SurveyRow[];
  setRows: (rows: SurveyRow[]) => void;
}

const MOCK_SESSION_ID = "demo-session-001";

const MOCK_ROWS: SurveyRow[] = [
  {
    id: 1,
    floor: "1F",
    location: "エントランス",
    fixture_model: "FR-42540-RS",
    existing_product: "φ100DL E17 (L)",
    photo_id: "",
    quantity: "36",
    notes: "調光対応",
  },
  {
    id: 2,
    floor: "1F",
    location: "ロビー",
    fixture_model: "FL-2030-SQ",
    existing_product: "FLR40S・W/M",
    photo_id: "",
    quantity: "12",
    notes: "非常用予備",
  },
  {
    id: 3,
    floor: "2F",
    location: "会議室A",
    fixture_model: "DL-5500-WH",
    existing_product: "LED埋込型 600×600",
    photo_id: "",
    quantity: "8",
    notes: "調光・人感センサー",
  },
  {
    id: 4,
    floor: "2F",
    location: "会議室B",
    fixture_model: "DL-5500-WH",
    existing_product: "LED埋込型 600×600",
    photo_id: "",
    quantity: "6",
    notes: "",
  },
  {
    id: 5,
    floor: "3F",
    location: "執務室",
    fixture_model: "PL-3000-LN",
    existing_product: "ペンダントライト 3000K",
    photo_id: "",
    quantity: "24",
    notes: "調光可能",
  },
  {
    id: 6,
    floor: "RF",
    location: "屋上",
    fixture_model: "OL-1000-WD",
    existing_product: "屋外壁付 防水型",
    photo_id: "",
    quantity: "4",
    notes: "LED 100W相当",
  },
];

export function useDemo(): DemoState {
  const [rows, setRows] = useState<SurveyRow[]>([]);

  useEffect(() => {
    // Detect if we're on GitHub Pages (no backend)
    const onGitHubPages = window.location.hostname.includes("github.io");

    if (onGitHubPages) {
      enableDemoMode({ enabled: true, mockRows: MOCK_ROWS });
      setRows(MOCK_ROWS);
    } else {
      // Not in demo mode
      enableDemoMode({ enabled: false, mockRows: [] });
    }
  }, []);

  return {
    isDemo: isDemoMode(),
    sessionId: MOCK_SESSION_ID,
    rows,
    setRows,
  };
}
```

### 4.4 — Update the Pages to Show Mock Data

Now we need to modify the pages so they work in "demo mode" (no backend).

**`UploadPage.tsx`** — Add a "View Demo" button:

Open `frontend/src/pages/UploadPage.tsx` and find the upload form area. Add a button after the "Run OCR" button (or replace the upload zone if no files detected):

Look for the section where the upload button is, and add:

```tsx
{/* ── Demo mode (GitHub Pages) ───────────────────── */}
{/* Show a "View Demo" button when no backend is available */}
{isDemoMode() && (
  <div className="demo-section">
    <p className="demo-note">
      📋 デモモード — サーバーに接続せずにサンプルデータを表示します
    </p>
    <button
      className="btn btn-demo"
      onClick={() => navigate(`/edit/${"demo-session-001"}?demo=true`)}
    >
      サンプルデータを見る →
    </button>
  </div>
)}
```

You'll also need to import `isDemoMode`:

```typescript
import { isDemoMode } from "../api/client";
```

**`EditPage.tsx`** — Show mock data instead of fetching from API:

Open `frontend/src/pages/EditPage.tsx` and find the `useEffect` that loads rows from the API.

Replace the API fetch with a conditional:

```typescript
useEffect(() => {
  const loadRows = async () => {
    // ── Demo mode: use mock data ──
    if (params.demo === "true" || isDemoMode()) {
      enableDemoMode({ enabled: true, mockRows: MOCK_DATA });
      setRows(MOCK_DATA);
      setLoading(false);
      return;
    }

    // ── Normal mode: fetch from API ──
    try {
      const data = await getRows(sessionId);
      setRows(data.rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rows");
    } finally {
      setLoading(false);
    }
  };
  loadRows();
}, [sessionId]);
```

Add the mock data at the top of the file:

```typescript
import { isDemoMode, enableDemoMode } from "../api/client";

const MOCK_DATA: SurveyRow[] = [
  { id: 1, floor: "1F", location: "エントランス", fixture_model: "FR-42540-RS",
    existing_product: "φ100DL E17 (L)", photo_id: "", quantity: "36", notes: "調光対応" },
  { id: 2, floor: "1F", location: "ロビー", fixture_model: "FL-2030-SQ",
    existing_product: "FLR40S・W/M", photo_id: "", quantity: "12", notes: "非常用予備" },
  // ... (copy the 6 rows from useDemo.ts)
];
```

**`ProcessingPage.tsx`** — Skip the API call in demo mode:

Find where it calls `runOCR()`. Wrap it:

```typescript
useEffect(() => {
  const processDemo = async () => {
    // ── Demo mode: skip OCR, go straight to edit ──
    if (isDemoMode()) {
      await new Promise(r => setTimeout(r, 2000)); // Fake progress bar
      navigate(`/edit/${sessionId}?demo=true`);
      return;
    }

    // ── Normal mode: call OCR API ──
    // ... existing code ...
  };
}, [sessionId]);
```

**`DonePage.tsx`** — Show a "Demo Complete" message:

Find where it shows the sheet URL. Wrap it:

```tsx
// ── Demo mode ──
if (isDemoMode()) {
  return (
    <div className="done-page">
      <h2>✅ デモ完了</h2>
      <p>これはGitHub Pages上のデモです。</p>
      <p>実際の環境では、ここにGoogle Sheetのリンクが表示されます。</p>
      <a href="/" className="btn">トップに戻る</a>
    </div>
  );
}
```

### 4.5 — Add Demo Mode Styles (Optional)

Add to `frontend/src/styles/app.css`:

```css
/* ── Demo mode styles ───────────────────────────── */
.demo-section {
  margin-top: 1.5rem;
  padding: 1.5rem;
  background: #fef9e7;
  border: 2px dashed #f39c12;
  border-radius: 8px;
  text-align: center;
}

.demo-note {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.btn-demo {
  background: #f39c12;
  color: white;
  font-size: 1.1rem;
  padding: 0.75rem 2rem;
}
```

---

## 5. Step 3: Add Mock Data for the Demo (Skip If You Did Step 4.3)

If you created `useDemo.ts` in step 4.3, you already have mock data. You can skip this section.

The mock data shows 6 sample rows from a Japanese building survey — exactly what the OCR would produce. This lets your CEO see:

- All 7 columns (フロア, 設置場所, 器具品番, etc.)
- Editable table rows
- The Register button
- The Done page

---

## 6. Step 4: Build and Deploy

### 6.1 — Build the Frontend

Open **Git Bash** in the project root:

```bash
cd frontend
npm install
npm run build
```

This creates a `frontend/dist/` folder with all the static files.

### 6.2 — Test Locally (Optional)

To see what GitHub Pages will look like:

```bash
npx serve dist
```

Open `http://localhost:3000` in your browser. The app should load with demo mode active.

### 6.3 — Push the dist Folder to GitHub

GitHub Pages needs the built files. There are two approaches:

**Approach A (Recommended): gh-pages branch**

Create a branch that only contains the built files:

```bash
# From the project root
cd frontend

# Install gh-pages tool
npm install --save-dev gh-pages

# Add deploy script to package.json
# (Or run manually)
npx gh-pages -d dist
```

**Approach B (Simpler): Deploy from /docs folder**

1. Copy `dist` contents to a `docs/` folder in the project root
2. Commit and push

We'll use Approach A since it's cleaner.

Add a deploy script to `frontend/package.json`. Open it and find the `"scripts"` section:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "deploy": "gh-pages -d dist"
}
```

Now run:

```bash
cd frontend
npm run build
npm run deploy
```

You'll see:
```
Published
```

> ⚠️ The first deploy creates a `gh-pages` branch on GitHub. If you get an authentication error, see [Troubleshooting](#9-troubleshooting).

---

## 7. Step 5: Enable GitHub Pages

### 7.1 — Go to Repository Settings

1. Go to your repository on GitHub: `https://github.com/YOUR_USERNAME/cowell-mvp`
2. Click the **"Settings"** tab (top row, almost at the end)

   ```
   ┌──────────────────────────────────────────────────┐
   │  <> Code  │  Issues  │  Pull requests  │  Settings │
   └──────────────────────────────────────────────────┘
   ```

### 7.2 — Find Pages Settings

1. In the left sidebar, scroll down to **"Pages"** (under "Code and automation")

   ```
   ┌──────────────────────────────────────────────────┐
   │  ├ Security                                       │
   │  ├ Code and automation                            │
   │  │  ├ Actions                                     │
   │  │  ├ Pages                    ← Click this       │
   │  │  └ Pages (another?)                            │
   └──────────────────────────────────────────────────┘
   ```

### 7.3 — Configure Source

1. Under **"Branch"**, click the dropdown that says "None"
2. Select **`gh-pages`**

   ```
   ┌──────────────────────────────────────────────────┐
   │  Branch                                           │
   │  [gh-pages ▼]  [/(root) ▼]  [Save]              │
   └──────────────────────────────────────────────────┘
   ```

3. Leave the folder as `/(root)`
4. Click **"Save"**

### 7.4 — Wait for Deployment

GitHub will show:

```
┌──────────────────────────────────────────────────┐
│ ⏳ Your site is being deployed...                 │
│                                                  │
│ Once deployed, you'll see:                        │
│ Your site is live at                              │
│ https://YOUR_USERNAME.github.io/cowell-mvp/       │
└──────────────────────────────────────────────────┘
```

Wait 1-2 minutes, then refresh the page. You should see:

```
✅ Your site is live at https://YOUR_USERNAME.github.io/cowell-mvp/
```

### 7.5 — Visit Your Site!

Click the URL or open it in a browser:

```
https://YOUR_USERNAME.github.io/cowell-mvp/
```

If you added the demo mode code, you should see the upload page with a "サンプルデータを見る →" button.

---

## 8. Bonus: Auto-Deploy on Every Push

You can set up GitHub Actions so that every time you `git push`, the frontend automatically rebuilds and redeploys.

### 8.1 — Create the Workflow File

Create this file in your project:

```
.github/workflows/deploy-pages.yml
```

Create the folders first:

```bash
mkdir -p .github/workflows
```

Then create the file with this content:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: ["main"]
    paths:
      - "frontend/**"
      - ".github/workflows/deploy-pages.yml"

  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: "./frontend/package-lock.json"

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./frontend/dist
```

### 8.2 — Push to Trigger

```bash
git add .github/
git commit -m "Add GitHub Pages auto-deploy workflow"
git push
```

Go to your repository → **"Actions"** tab. You'll see a workflow running. Wait for it to complete (green checkmark).

From now on, every `git push` to `main` that changes frontend files will automatically redeploy.

---

## 9. Troubleshooting

### "Git push authentication failed"

**Error:**
```
remote: Support for password authentication was removed on August 13, 2021.
```

**Fix — Use a Personal Access Token (PAT):**

1. Go to GitHub → **Settings** (top-right profile menu) → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
2. **Token name:** `cowell-deploy`
3. **Expiration:** No expiration (or 90 days)
4. **Repository access:** Only select repositories → `cowell-mvp`
5. **Permissions:** Read/write for **Contents** and **Pages**
6. Click **"Generate token"**
7. **Copy the token!** (It starts with `github_pat_`)
8. Now push again using the token as password when prompted

Or use the GitHub CLI for easier auth:
```bash
gh auth login
```

### "Blank page after deploy"

**Causes:**
1. `base: "./"` not set in `vite.config.ts`
2. Assets loading from wrong path

**Fix:** Check your browser's Developer Tools (F12) → Console tab. Look for 404 errors. If assets are loading from `/assets/...` instead of `/cowell-mvp/assets/...`, the `base` setting is wrong.

### "Page shows 404 on refresh"

GitHub Pages serves `index.html` at the root, but React Router paths like `/edit/demo-session-001` don't exist as real files.

**If you're using the gh-pages branch:** Create a `404.html` file in the `dist` folder that redirects to `index.html`:

Create `frontend/public/404.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Cowell OCR</title>
  <script>
    // Redirect SPA routes to index.html
    sessionStorage.redirect = location.href;
  </script>
  <meta http-equiv="refresh" content="0;URL='/'">
</head>
<body></body>
</html>
```

This will be included in the build automatically. When GitHub Pages gets a 404, it serves `404.html`, which redirects to `/` (index.html). React Router then reads the URL from `sessionStorage.redirect` and navigates to the correct page.

### "npm run deploy fails with gh-pages"

**Error:** Permission denied or not a git repository.

**Fix:** Make sure you've committed and pushed your code to GitHub first, then run `npm run deploy` from within the `frontend` folder (which is inside a git repo).

### "Demo mode not activating"

**Cause:** The detection `window.location.hostname.includes("github.io")` might not match.

**Fix:** Open your browser console (`F12` → Console) and type:
```javascript
window.location.hostname
```

Check what it returns. If it doesn't include `github.io`, the detection won't fire. You can override by adding `?demo=true` to the URL manually:

```
https://YOUR_USERNAME.github.io/cowell-mvp/?demo=true
```

### "Styles look different"

GitHub Pages may serve slightly differently than local. The `base: "./"` change can affect CSS background image paths. If styles break, check the browser console for CSS 404 errors.

---

## 10. What to Show Your CEO

Here's a 5-minute demo script:

---

**Screen: Upload Page** (`/`)

> "This is the main screen. Users drag and drop their survey PDFs here on the left, and photos on the right. Then they click 'Run OCR'."

**Click "Sample Data →" button**

---

**Screen: Edit Page** (`/edit/demo-session-001?demo=true`)

> "The OCR extracts all rows from the handwritten survey. Users can edit any cell — see, I can change this quantity from 36 to 40. They can add or delete rows too."
>
> "All 7 columns from the original survey sheet are here: floor, location, fixture model, existing product, photo, quantity, and notes."

**Point to the "Register to Google Sheet" button**

> "When everything looks correct, they click here, and the system creates a properly formatted Google Sheet with all the data and photo references."

---

**Screen: Done Page** (`/done/demo-session-001?demo=true`)

> "This is the final screen. In production, it shows a direct link to the Google Sheet. The whole process takes about 30 seconds instead of hours of manual data entry."

---

**Key talking points:**

| What to emphasize | Why it matters |
|------------------|----------------|
| "One click from PDF → Google Sheet" | Eliminates manual data entry |
| "Editable before finalizing" | Human-in-the-loop for accuracy |
| "Handles merged cells and dittos" | Built for real Japanese survey sheets |
| "Budget-friendly MVP" | Under $1/month to run on AWS |
| "Japanese column headers" | Ready for Japanese clients/teams |

**What to be honest about:**

| Limitation | How to frame it |
|------------|----------------|
| Not yet deployed (this is GitHub Pages) | "This is the UI prototype. The full working version deploys to AWS — I have the deployment plan ready." |
| OCR accuracy isn't 100% | "We'll need a Phase 2 for accuracy improvements, but the core flow works." |
| Single-user | "MVP is single-user. We can add multi-user in Phase 2." |

---

## Summary

```
═════════════════════════════════════════════════════════════════
              GITHUB PAGES DEPLOYMENT — CHEAT SHEET
═════════════════════════════════════════════════════════════════

Prerequisite: GitHub account + Node.js + Git

Key steps:
  1. Push code to GitHub
  2. Update vite.config.ts → base: "./"
  3. Add demo mode code (mock data + detection)
  4. npm run build → npm run deploy
  5. GitHub Settings → Pages → gh-pages branch

Your URL:
  https://YOUR_USERNAME.github.io/cowell-mvp/

To update:
  cd frontend
  npm run build
  npm run deploy

Auto-deploy (optional):
  Add .github/workflows/deploy-pages.yml

Cost: $0 (forever)
═════════════════════════════════════════════════════════════════
```
