# Web UI for the LawPhil Case Downloader

A no-install, in-browser version of the downloader. Users open a page, type a
G.R. number, and get a clean, print-ready PDF — no Python, no Selenium, no setup.

## How it's different from the script

The original `lawphil_downloader.py` ran headless Chrome locally: it Google-scraped
to find the case URL, then used Chrome's `printToPDF`. That can't move to a server
as-is — Google blocks datacenter IPs, and a browser can't fetch lawphil.net directly
(no CORS). So the work is split:

| Job | Where it runs | Why |
|-----|---------------|-----|
| UI, HTML cleanup, PDF | the user's **browser** | the browser already *is* the same Chrome PDF engine the script used |
| Resolve G.R. → URL | tiny **Cloudflare Worker** | needs a search step a browser can't do safely |
| Fetch the lawphil page | tiny **Cloudflare Worker** | cross-origin fetch a browser is blocked from |

The browser does the heavy lifting for free; the Worker is a thin proxy.

## Files

- `index.html` — the whole front end. Static, no build step. Host it anywhere
  (GitHub Pages, Netlify, Vercel). Works in **demo mode** with a sample case
  before any backend exists.
- `worker.js` — the Cloudflare Worker. Routes: `/fetch?url=` and `/resolve?gr=`.

## Deploy in three steps

1. **Worker.** Install Wrangler (`npm i -g wrangler`), then `wrangler deploy worker.js`.
   You'll get a URL like `https://lawphil-dl.<you>.workers.dev`.
   *(Or paste `worker.js` into the Cloudflare dashboard's Quick-Edit editor.)*

2. **Front end.** Push `index.html` to a `gh-pages` branch (or drop it on Netlify).
   Open the page, expand **Backend endpoint**, paste your Worker URL. Done —
   it now fetches real cases.

3. **Reliable lookup (recommended).** The keyless lookup uses a DuckDuckGo scrape
   that can rate-limit. For dependable G.R. resolution, add a
   [Google Programmable Search](https://programmablesearchengine.google.com/) engine
   scoped to `lawphil.net` and set two Worker secrets:
   ```
   wrangler secret put GOOGLE_CSE_KEY
   wrangler secret put GOOGLE_CSE_CX
   ```
   The free CSE tier is 100 queries/day. The **By LawPhil link** tab never needs this.

## Honest limitations

- **PDF download is the browser's "Save as PDF" dialog**, not a silent one-click
  save. That's deliberate: it reuses the exact engine the original script used, so
  pagination and typography stay faithful. A one-click `jsPDF` path is possible but
  pages long decisions worse.
- **Caption / date / ponente detection is heuristic.** LawPhil's older pages have
  loose markup; the cleaner extracts paragraphs and guesses the heading. The text is
  always complete — the *labelling* is best-effort.
- **Respect lawphil.net.** This reads public decisions one at a time for a human;
  keep it that way (the Worker caches for a day to be light on their servers).
