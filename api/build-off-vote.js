/* Build-off reader vote: a Vercel serverless function.
 *
 * GET  /api/build-off-vote?build_off=01-ski-sim   the tally
 * POST /api/build-off-vote {build_off, choice}    cast or change a vote, answers with the tally
 *
 * A vote is one small private blob in the project's Vercel Blob store at
 * build-off-votes/<build_off>/<choice>/<voter>.json. The tally is the number
 * of blobs under each choice, so there is no counter to race on. Voting again
 * moves the voter's blob to the new choice.
 *
 * <voter> is an HMAC-SHA256 of the caller's network address and the build-off,
 * keyed with BUILD_OFF_VOTE_KEY or, when that is unset, the Blob token. The
 * address itself is never stored and the hash cannot be reversed without the
 * key. One vote per address is a courtesy limit, not security: the tally is a
 * reader poll, and the page says so.
 *
 * Preview deployments write under build-off-votes-preview/, so trying a
 * preview never changes the published tally.
 *
 * Locally, with no token and BUILD_OFF_VOTES_FILE set, votes are kept in that
 * JSON file instead (see scripts/waitlist_dev.js). In production with no
 * token the function answers 500, never a silent drop.
 */
"use strict";

const crypto = require("crypto");
const fs = require("fs");

// Every build-off that takes votes, with its entries in page order. A page's
// data-build-off and data-choice attributes must match (scripts/test_build_offs.py).
const BUILD_OFFS = {
  "01-ski-sim": ["chamonix-ski-sim", "fall-line"],
};

function root() {
  return process.env.VERCEL_ENV === "production" ? "build-off-votes" : "build-off-votes-preview";
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    if (req.body !== undefined) return resolve(req.body);
    let data = "";
    req.setEncoding("utf8");
    req.on("data", (chunk) => {
      data += chunk;
      if (data.length > 2000) {
        reject(new Error("body too large"));
        req.destroy();
      }
    });
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

function parseFields(raw) {
  if (raw && typeof raw === "object") return raw;
  try {
    const parsed = JSON.parse(typeof raw === "string" && raw ? raw : "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (e) {
    return {};
  }
}

function voterId(req, buildOff) {
  const forwarded = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim();
  const address = forwarded || (req.socket && req.socket.remoteAddress) || "unknown";
  const key = process.env.BUILD_OFF_VOTE_KEY || process.env.BLOB_READ_WRITE_TOKEN || "local-preview-only";
  return crypto.createHmac("sha256", key).update(buildOff + "|" + address).digest("hex");
}

function localFile() {
  if (process.env.BUILD_OFF_VOTES_FILE && process.env.VERCEL_ENV !== "production") return process.env.BUILD_OFF_VOTES_FILE;
  return null;
}

function readLocal(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    return {};
  }
}

async function castVote(buildOff, choice, voter) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (token) {
    const { put, del } = require("@vercel/blob");
    const record = { build_off: buildOff, choice, created_at: new Date().toISOString() };
    await put(`${root()}/${buildOff}/${choice}/${voter}.json`, JSON.stringify(record) + "\n", {
      access: "private",
      addRandomSuffix: false,
      allowOverwrite: true,
      contentType: "application/json",
      token,
    });
    const others = BUILD_OFFS[buildOff].filter((c) => c !== choice).map((c) => `${root()}/${buildOff}/${c}/${voter}.json`);
    try {
      await del(others, { token });
    } catch (e) {
      // The new vote is stored; a leftover old one would count this voter twice, so make the failure visible.
      console.error("build-off vote: could not remove the earlier vote:", e && e.message ? e.message : e);
    }
    return;
  }
  const file = localFile();
  if (!file) throw new Error("no vote store: connect a Vercel Blob store (BLOB_READ_WRITE_TOKEN)");
  const all = readLocal(file);
  all[buildOff] = all[buildOff] || {};
  all[buildOff][voter] = choice;
  fs.writeFileSync(file, JSON.stringify(all, null, 1) + "\n");
}

async function tally(buildOff) {
  const counts = {};
  for (const choice of BUILD_OFFS[buildOff]) counts[choice] = 0;
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (token) {
    const { list } = require("@vercel/blob");
    for (const choice of BUILD_OFFS[buildOff]) {
      let cursor;
      do {
        const page = await list({ prefix: `${root()}/${buildOff}/${choice}/`, cursor, token, limit: 1000 });
        counts[choice] += page.blobs.length;
        cursor = page.hasMore ? page.cursor : undefined;
      } while (cursor);
    }
    return counts;
  }
  const file = localFile();
  if (!file) throw new Error("no vote store: connect a Vercel Blob store (BLOB_READ_WRITE_TOKEN)");
  for (const choice of Object.values(readLocal(file)[buildOff] || {})) {
    if (choice in counts) counts[choice] += 1;
  }
  return counts;
}

function send(res, status, body, cache) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", cache || "no-store");
  res.end(JSON.stringify(body));
}

function result(buildOff, counts, choice) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const body = { ok: true, build_off: buildOff, counts, total };
  if (choice) body.choice = choice;
  return body;
}

function sameSite(req) {
  // A browser sends Origin on a cross-site POST; only this site's own pages may cast votes.
  const origin = req.headers.origin;
  if (!origin) return true;
  try {
    return new URL(origin).host === req.headers.host;
  } catch (e) {
    return false;
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== "GET" && req.method !== "POST") {
    res.setHeader("Allow", "GET, POST");
    send(res, 405, { ok: false, error: "method" });
    return;
  }

  let fields;
  if (req.method === "GET") {
    fields = { build_off: new URL(req.url, "http://localhost").searchParams.get("build_off") };
  } else {
    if (!sameSite(req)) {
      send(res, 403, { ok: false, error: "origin" });
      return;
    }
    try {
      fields = parseFields(await readBody(req));
    } catch (e) {
      send(res, 400, { ok: false, error: "body" });
      return;
    }
  }

  const buildOff = String(fields.build_off || "");
  if (!Object.prototype.hasOwnProperty.call(BUILD_OFFS, buildOff)) {
    send(res, 400, { ok: false, error: "build_off" });
    return;
  }

  try {
    if (req.method === "GET") {
      // The tally lists the store, so let the CDN answer repeat reads for a few seconds.
      send(res, 200, result(buildOff, await tally(buildOff)), "public, s-maxage=15, stale-while-revalidate=60");
      return;
    }
    const choice = String(fields.choice || "");
    if (!BUILD_OFFS[buildOff].includes(choice)) {
      send(res, 400, { ok: false, error: "choice" });
      return;
    }
    await castVote(buildOff, choice, voterId(req, buildOff));
    send(res, 200, result(buildOff, await tally(buildOff), choice));
  } catch (e) {
    console.error("build-off vote failed:", e && e.message ? e.message : e);
    send(res, 500, { ok: false, error: "store" });
  }
};

module.exports.BUILD_OFFS = BUILD_OFFS;
