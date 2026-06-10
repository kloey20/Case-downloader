/**
 * LawPhil Case Downloader — Cloudflare Worker backend
 * ---------------------------------------------------
 * Two jobs the browser can't do itself:
 *   GET /fetch?url=<lawphil decision URL>   -> returns the page HTML (with CORS)
 *   GET /resolve?gr=<number>                -> { "url": "https://lawphil.net/..." } or { "url": null }
 *
 * Deploy:  npx wrangler deploy   (or paste into the Cloudflare dashboard editor)
 *
 * Optional, for a RELIABLE /resolve, set these as Worker variables/secrets:
 *   GOOGLE_CSE_KEY  – a Google Programmable Search JSON API key
 *   GOOGLE_CSE_CX   – a Programmable Search Engine ID scoped to lawphil.net
 * Without them, /resolve falls back to a best-effort DuckDuckGo scrape, which
 * works often but can be rate-limited. The "By LawPhil link" tab never needs this.
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
  "Access-Control-Allow-Headers": "*",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });

    const { pathname, searchParams } = new URL(request.url);

    try {
      if (pathname === "/fetch")   return await handleFetch(searchParams);
      if (pathname === "/resolve") return await handleResolve(searchParams, env);
      return json({ ok: true, routes: ["/fetch?url=", "/resolve?gr="] });
    } catch (err) {
      return json({ error: String(err.message || err) }, 502);
    }
  },
};

/* ---- /fetch : guarded passthrough of a lawphil page ---- */
async function handleFetch(params) {
  const target = params.get("url") || "";
  let u;
  try { u = new URL(target); } catch { return json({ error: "Bad URL." }, 400); }

  // SSRF guard: only ever fetch lawphil.net
  if (!/(^|\.)lawphil\.net$/i.test(u.hostname)) {
    return json({ error: "Only lawphil.net URLs are allowed." }, 403);
  }

  const res = await fetch(u.toString(), {
    headers: { "User-Agent": "Mozilla/5.0 (LawPhil-Case-Downloader)" },
    cf: { cacheTtl: 86400, cacheEverything: true },
  });
  if (!res.ok) return json({ error: `LawPhil returned ${res.status}.` }, res.status);

  const html = await res.text();
  return new Response(html, {
    headers: { ...CORS, "Content-Type": "text/html; charset=utf-8" },
  });
}

/* ---- /resolve : G.R. number -> lawphil decision URL ---- */
async function handleResolve(params, env) {
  const gr = (params.get("gr") || "").replace(/\D/g, "");
  if (!gr) return json({ error: "Provide ?gr=<number>." }, 400);

  let url = null;
  if (env.GOOGLE_CSE_KEY && env.GOOGLE_CSE_CX) {
    url = await resolveViaGoogle(gr, env);
  }
  if (!url) url = await resolveViaDuckDuckGo(gr);

  return json({ gr, url });
}

async function resolveViaGoogle(gr, env) {
  const q = `G.R. No. ${gr}`;
  const api = `https://www.googleapis.com/customsearch/v1?key=${env.GOOGLE_CSE_KEY}` +
              `&cx=${env.GOOGLE_CSE_CX}&q=${encodeURIComponent(q)}`;
  const r = await fetch(api);
  if (!r.ok) return null;
  const data = await r.json();
  for (const item of data.items || []) {
    const link = item.link || "";
    if (/lawphil\.net\/judjuris\/.+\.html?$/i.test(link)) return link;
  }
  return null;
}

async function resolveViaDuckDuckGo(gr) {
  const q = `site:lawphil.net judjuris "G.R. No. ${gr}"`;
  const r = await fetch("https://html.duckduckgo.com/html/?q=" + encodeURIComponent(q), {
    headers: { "User-Agent": "Mozilla/5.0" },
  });
  if (!r.ok) return null;
  const html = await r.text();
  // DDG wraps real links in a redirect; pull lawphil judjuris .html targets out
  const matches = [...html.matchAll(/uddg=([^&"]+)/g)].map(m => decodeURIComponent(m[1]));
  const direct  = [...html.matchAll(/https?:\/\/(?:www\.)?lawphil\.net\/judjuris\/[^\s"'<>]+\.html?/gi)].map(m => m[0]);
  const all = [...direct, ...matches.filter(x => /lawphil\.net\/judjuris\/.+\.html?$/i.test(x))];
  return all[0] || null;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}
