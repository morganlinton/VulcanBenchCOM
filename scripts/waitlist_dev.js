/* Local preview of the site plus the waitlist function, no Vercel login needed.
 *
 *   node scripts/waitlist_dev.js            (http://localhost:8899)
 *   PORT=9000 node scripts/waitlist_dev.js
 *
 * Static files are served from the repository root. POST /api/waitlist runs
 * api/waitlist.js with WAITLIST_FILE pointing at .waitlist-local.jsonl (git
 * ignored), so a signup can be checked end to end without a Blob token.
 */
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const PORT = Number(process.env.PORT || 8899);
process.env.WAITLIST_FILE = process.env.WAITLIST_FILE || path.join(ROOT, ".waitlist-local.jsonl");
delete process.env.VERCEL_ENV;

const handler = require(path.join(ROOT, "api", "waitlist.js"));

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".pdf": "application/pdf",
  ".xml": "application/xml; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".csv": "text/csv; charset=utf-8",
  ".yaml": "text/yaml; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".ico": "image/x-icon",
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname === "/api/waitlist") {
    Promise.resolve(handler(req, res)).catch((e) => {
      res.statusCode = 500;
      res.end(String(e));
    });
    return;
  }
  let rel = decodeURIComponent(url.pathname);
  if (rel.endsWith("/")) rel += "index.html";
  const file = path.normalize(path.join(ROOT, rel));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.statusCode = 404;
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.end(fs.readFileSync(path.join(ROOT, "404.html")));
    return;
  }
  res.setHeader("Content-Type", TYPES[path.extname(file)] || "application/octet-stream");
  fs.createReadStream(file).pipe(res);
});

server.listen(PORT, () => {
  console.log(`VulcanBench.com preview on http://localhost:${PORT}`);
  console.log(`Waitlist signups append to ${process.env.WAITLIST_FILE}`);
});
