/* Eval suite builder waitlist: a Vercel serverless function.
 *
 * POST /api/waitlist with JSON or form fields {email, repo, website}.
 * One JSON record per signup is written to the project's Vercel Blob store at
 * waitlist/<sha256 of the normalized email>.json, so a second submit from the
 * same address overwrites instead of duplicating. The store is connected in
 * the Vercel dashboard (Storage tab), which sets BLOB_READ_WRITE_TOKEN.
 *
 * Locally, with no token and WAITLIST_FILE set, records are appended to that
 * file instead (see scripts/waitlist_dev.js). In production with no token the
 * function answers 500 so a misconfiguration is visible, never a silent drop.
 *
 * "website" is a honeypot: humans never see it, so a filled value is a bot.
 * Those get a success answer and nothing is stored.
 *
 * With SLACK_WAITLIST_WEBHOOK set (a Slack incoming webhook URL, added as an
 * environment variable in the Vercel dashboard), each stored signup is also
 * posted to that channel with the running total. The post is best effort: a
 * Slack failure is logged and never fails the signup.
 */
"use strict";

const crypto = require("crypto");
const fs = require("fs");

const PAGE = "/eval-suite-builder.html";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function readBody(req) {
  return new Promise((resolve, reject) => {
    if (req.body !== undefined) return resolve(req.body);
    let data = "";
    req.setEncoding("utf8");
    req.on("data", (chunk) => {
      data += chunk;
      if (data.length > 10000) {
        reject(new Error("body too large"));
        req.destroy();
      }
    });
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

function parseFields(raw, contentType) {
  if (raw && typeof raw === "object") return raw;
  const text = typeof raw === "string" ? raw : "";
  if (/application\/json/i.test(contentType)) {
    try {
      return JSON.parse(text || "{}");
    } catch (e) {
      return {};
    }
  }
  const fields = {};
  for (const [key, value] of new URLSearchParams(text)) fields[key] = value;
  return fields;
}

function str(value, max) {
  return String(value == null ? "" : value).trim().slice(0, max);
}

async function store(record) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (token) {
    const { put } = require("@vercel/blob");
    await put(`waitlist/${record.id}.json`, JSON.stringify(record) + "\n", {
      access: "private",
      addRandomSuffix: false,
      allowOverwrite: true,
      contentType: "application/json",
      token,
    });
    return "blob";
  }
  if (process.env.WAITLIST_FILE && process.env.VERCEL_ENV !== "production") {
    fs.appendFileSync(process.env.WAITLIST_FILE, JSON.stringify(record) + "\n");
    return "file";
  }
  throw new Error("no waitlist store: connect a Vercel Blob store (BLOB_READ_WRITE_TOKEN)");
}

async function countSignups(where) {
  if (where === "blob") {
    const { list } = require("@vercel/blob");
    const token = process.env.BLOB_READ_WRITE_TOKEN;
    let count = 0;
    let cursor;
    do {
      const page = await list({ prefix: "waitlist/", cursor, token, limit: 1000 });
      count += page.blobs.length;
      cursor = page.hasMore ? page.cursor : undefined;
    } while (cursor);
    return count;
  }
  const text = fs.readFileSync(process.env.WAITLIST_FILE, "utf8");
  return text.split("\n").filter(Boolean).length;
}

function slackEscape(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function notifySlack(record, where) {
  const url = process.env.SLACK_WAITLIST_WEBHOOK;
  if (!url) return false;
  let total = "";
  try {
    total = ` That makes ${await countSignups(where)}.`;
  } catch (e) {
    console.error("waitlist count failed:", e && e.message ? e.message : e);
  }
  const repo = record.repo ? ` (${slackEscape(record.repo)})` : "";
  const text = `New eval suite builder waitlist signup: ${slackEscape(record.email)}${repo}.${total}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error(`slack answered ${response.status}`);
  return true;
}

function send(res, status, wantsJson, body, redirectQuery) {
  if (wantsJson) {
    res.statusCode = status;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.end(JSON.stringify(body));
  } else {
    res.statusCode = 303;
    res.setHeader("Location", PAGE + "?" + redirectQuery + "#waitlist");
    res.end();
  }
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") {
    res.statusCode = 405;
    res.setHeader("Allow", "POST");
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ ok: false, error: "method" }));
    return;
  }
  const contentType = req.headers["content-type"] || "";
  const wantsJson = /application\/json/i.test(req.headers.accept || "") || /application\/json/i.test(contentType);

  let fields;
  try {
    fields = parseFields(await readBody(req), contentType);
  } catch (e) {
    send(res, 400, wantsJson, { ok: false, error: "body" }, "error=body");
    return;
  }

  const email = str(fields.email, 254);
  const repo = str(fields.repo, 300);
  const honeypot = str(fields.website, 100);

  if (!EMAIL_RE.test(email)) {
    send(res, 400, wantsJson, { ok: false, error: "email" }, "error=email");
    return;
  }
  if (honeypot) {
    send(res, 200, wantsJson, { ok: true }, "joined=1");
    return;
  }

  const normalized = email.toLowerCase();
  const record = {
    id: crypto.createHash("sha256").update(normalized).digest("hex"),
    email: normalized,
    repo,
    created_at: new Date().toISOString(),
    source: "vulcanbench.com" + PAGE,
  };

  let where;
  try {
    where = await store(record);
  } catch (e) {
    console.error("waitlist store failed:", e && e.message ? e.message : e);
    send(res, 500, wantsJson, { ok: false, error: "store" }, "error=store");
    return;
  }
  try {
    await notifySlack(record, where);
  } catch (e) {
    console.error("waitlist slack post failed:", e && e.message ? e.message : e);
  }
  send(res, 200, wantsJson, { ok: true }, "joined=1");
};
