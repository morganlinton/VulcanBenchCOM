/* Export the eval suite builder waitlist from the Vercel Blob store as CSV.
 *
 *   BLOB_READ_WRITE_TOKEN=... node scripts/waitlist_export.js > waitlist.csv
 *
 * The token is the one Vercel set on the project when the Blob store was
 * connected (Project > Storage > the store > .env.local tab, or
 * `vercel env pull`). It is read from the environment only; never put it in
 * a file in this repository.
 */
"use strict";

const { list, get } = require("@vercel/blob");

function csv(value) {
  const s = String(value == null ? "" : value);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

async function main() {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    console.error("Set BLOB_READ_WRITE_TOKEN in the environment first.");
    process.exit(2);
  }
  const records = [];
  let cursor;
  do {
    const page = await list({ prefix: "waitlist/", cursor, token, limit: 1000 });
    for (const blob of page.blobs) {
      const result = await get(blob.pathname, { access: "private", token, useCache: false });
      if (!result || !result.stream) continue;
      const text = await new Response(result.stream).text();
      try {
        records.push(JSON.parse(text));
      } catch (e) {
        console.error("skipping unreadable record", blob.pathname);
      }
    }
    cursor = page.hasMore ? page.cursor : undefined;
  } while (cursor);

  records.sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
  process.stdout.write("created_at,email,repo\n");
  for (const r of records) {
    process.stdout.write([r.created_at, r.email, r.repo].map(csv).join(",") + "\n");
  }
  console.error(`${records.length} signups`);
}

main().catch((e) => {
  console.error(e && e.message ? e.message : e);
  process.exit(1);
});
