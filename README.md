# Zoom Attendance Dashboard

Director-facing attendance dashboard (Next.js), deployed on **Vercel**.

## Deploy on Vercel

1. Push this repo to GitHub.
2. [Import on Vercel](https://vercel.com/new) → set **Root Directory** to **`web`**.
3. Add the environment variables below → **Deploy**.

## Vercel environment variables

Add these in **Project → Settings → Environment Variables** (Production, and Preview if you use preview URLs).

### Required

| Key | Where to get the value |
|-----|-------------------------|
| `ZOOM_ACCOUNT_ID` | Zoom Marketplace → your **Server-to-Server OAuth** app → **App credentials** → Account ID |
| `ZOOM_CLIENT_ID` | Same page → Client ID |
| `ZOOM_CLIENT_SECRET` | Same page → Client Secret (View) |
| `ZOOM_USER_EMAIL` | Email of the Zoom **host** whose class sessions you track (not from App credentials) |

### Recommended

| Key | Purpose |
|-----|---------|
| `DASHBOARD_PASSWORD` | Password the director enters to open the site |
| `NEXT_PUBLIC_COLLEGE_NAME` | College name shown in the header (e.g. `ABC College`) |

### Optional

| Key | Purpose |
|-----|---------|
| `ZOOM_USER_ID` | Use instead of `ZOOM_USER_EMAIL` if you know the Zoom user ID |

Do **not** use the numeric account number from your Zoom profile as `ZOOM_ACCOUNT_ID` — use the Account ID on the app’s **App credentials** page.

## After deploy

Open your Vercel URL → sign in with `DASHBOARD_PASSWORD` (if set) → pick a date → view attendance → download CSV.

See [`web/.env.example`](web/.env.example) for a copy-paste template.
