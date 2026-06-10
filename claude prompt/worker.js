/**
 * LawPhil Case Downloader — Cloudflare Worker backend
 * ---------------------------------------------------
 *   GET /fetch?url=<lawphil decision URL>   -> raw page bytes (with CORS)
 *   GET /resolve?gr=<number>                -> { "url": "https://lawphil.net/..." | null }
 *
 * The front end works without this for the "By LawPhil link" tab (it uses a public
 * relay). Deploy this for reliable G.R.-number lookup and a relay you control.
 *
 * Deploy:  npx wrangler deploy   (or paste into the Cloudflare dashboard editor)
 *
 * Optional secrets for reliable /resolve (Google Programmable Search, 100/day free):
 *   GOOGLE_CSE_KEY , GOOGLE_CSE_CX
 * Without them, /resolve falls back to a best-effort DuckDuckGo scrape.
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

/* /fetch : guarded passthrough. Returns the ORIGINAL bytes so the browser can
   decode the right charset (LawPhil's older pages are Windows-1252, e.g. ñ). */
async function handleFetch(params) {
  const target = params.get("url") || "";
  let u;
  try { u = new URL(target); } catch { return json({ error: "Bad URL." }, 400); }
  if (!/(^|\.)lawphil\.net$/i.test(u.hostname))
    return json({ error: "Only lawphil.net URLs are allowed." }, 403);

  const res = await fetch(u.toString(), {
    headers: { "User-Agent": "Mozilla/5.0 (LawPhil-Case-Downloader)" },
    cf: { cacheTtl: 86400, cacheEverything: true },
  });
  if (!res.ok) return json({ error: `LawPhil returned ${res.status}.` }, res.status);

  return new Response(res.body, {
    headers: {
      ...CORS,
      "Content-Type": res.headers.get("content-type") || "text/html",
    },
  });
}

/* /resolve : G.R. number -> main decision URL (prefers the decision over opinions) */
async function handleResolve(params, env) {
  const gr = (params.get("gr") || "").replace(/\D/g, "");
  if (!gr) return json({ error: "Provide ?gr=<number>." }, 400);

  let urls = [];
  if (env.GOOGLE_CSE_KEY && env.GOOGLE_CSE_CX) urls = await viaGoogle(gr, env);
  if (!urls.length) urls = await viaDuckDuckGo(gr);

  // prefer the main decision file: gr_<num>_<year>.html, not gr_<num>_<justice>.html
  const main = urls.find(u => new RegExp(`gr[_l-]*${gr}_\\d{4}\\.html$`, "i").test(u));
  return json({ gr, url: main || urls[0] || null });
}

async function viaGoogle(gr, env) {
  const api = `https://www.googleapis.com/customsearch/v1?key=${env.GOOGLE_CSE_KEY}` +
              `&cx=${env.GOOGLE_CSE_CX}&q=${encodeURIComponent(`G.R. No. ${gr}`)}`;
  const r = await fetch(api);
  if (!r.ok) return [];
  const data = await r.json();
  return (data.items || []).map(i => i.link)
    .filter(l => /lawphil\.net\/judjuris\/.+\.html?$/i.test(l || ""));
}

async function viaDuckDuckGo(gr) {
  const q = `site:lawphil.net judjuris "G.R. No. ${gr}"`;
  const r = await fetch("https://html.duckduckgo.com/html/?q=" + encodeURIComponent(q),
                        { headers: { "User-Agent": "Mozilla/5.0" } });
  if (!r.ok) return [];
  const html = await r.text();
  const direct  = [...html.matchAll(/https?:\/\/(?:www\.)?lawphil\.net\/judjuris\/[^\s"'<>]+\.html?/gi)].map(m => m[0]);
  const wrapped = [...html.matchAll(/uddg=([^&"]+)/g)]
    .map(m => { try { return decodeURIComponent(m[1]); } catch { return ""; } })
    .filter(u => /lawphil\.net\/judjuris\/.+\.html?$/i.test(u));
  return [...direct, ...wrapped];
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { ...CORS, "Content-Type": "application/json" },
  });
}
