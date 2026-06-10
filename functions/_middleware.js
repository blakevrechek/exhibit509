// Cloudflare Pages Function — gates the Consultant's Corner behind HTTP Basic Auth.
//
// Runs on every request (root middleware), but only enforces auth on the
// /consultants paths; everything else passes straight through. Unlike the old
// client-side reveal, the HTML is never served until the password is supplied,
// so the offer and pricing are not present in public page source.
//
// Password: set a CONSULTANTS_PASSWORD environment variable in the Cloudflare
// Pages project to override; falls back to the existing preview password.
// Any username is accepted; only the password is checked.
export async function onRequest(context) {
  const { request, next, env } = context;
  const path = new URL(request.url).pathname.replace(/\/+$/, "").toLowerCase();

  if (path === "/consultants" || path === "/consultants.html") {
    const expected = (env && env.CONSULTANTS_PASSWORD) || "sell";
    const header = request.headers.get("Authorization") || "";
    const match = header.match(/^Basic\s+(.+)$/i);
    let ok = false;
    if (match) {
      try {
        const decoded = atob(match[1]);            // "username:password"
        const pass = decoded.slice(decoded.indexOf(":") + 1);
        ok = pass === expected;
      } catch (_e) { ok = false; }
    }
    if (!ok) {
      return new Response("Authentication required.", {
        status: 401,
        headers: {
          "WWW-Authenticate": 'Basic realm="Consultant\'s Corner", charset="UTF-8"',
          "Content-Type": "text/plain; charset=utf-8",
          "Cache-Control": "no-store",
        },
      });
    }
  }
  return next();
}
