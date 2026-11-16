#!/usr/bin/env node
// Icônes de l'Observatoire (favicons PNG, icône Apple, favicon.ico) rendues
// depuis web/beta/favicon.svg avec le Chromium de Playwright.
// Relancer après une retouche du logo : node scripts/favicons.js
const fs = require("fs");
const path = require("path");
const BETA = path.join(__dirname, "..", "web", "beta");
let chromium;
try { ({ chromium } = require("playwright")); } catch (e) { ({ chromium } = require("/opt/node22/lib/node_modules/playwright")); }

function ico(pngs) {
  const head = Buffer.alloc(6); head.writeUInt16LE(1, 2); head.writeUInt16LE(pngs.length, 4);
  const dir = Buffer.alloc(16 * pngs.length); let off = 6 + dir.length;
  pngs.forEach(({ size, buf }, i) => {
    const o = i * 16; dir.writeUInt8(size, o); dir.writeUInt8(size, o + 1); dir.writeUInt16LE(1, o + 4); dir.writeUInt16LE(32, o + 6);
    dir.writeUInt32LE(buf.length, o + 8); dir.writeUInt32LE(off, o + 12); off += buf.length;
  });
  return Buffer.concat([head, dir, ...pngs.map((p) => p.buf)]);
}

(async () => {
  const svg = fs.readFileSync(path.join(BETA, "favicon.svg"), "utf8");
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const out = {};
  for (const size of [32, 48, 96, 180, 192]) {
    out[size] = Buffer.from(await page.evaluate(async ({ svg, size }) => {
      const img = new Image(); img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg); await img.decode();
      const c = document.createElement("canvas"); c.width = c.height = size;
      c.getContext("2d").drawImage(img, 0, 0, size, size);
      return c.toDataURL("image/png").split(",")[1];
    }, { svg, size }), "base64");
  }
  await browser.close();
  fs.writeFileSync(path.join(BETA, "favicon-48.png"), out[48]);
  fs.writeFileSync(path.join(BETA, "favicon-96.png"), out[96]);
  fs.writeFileSync(path.join(BETA, "favicon-192.png"), out[192]);
  fs.writeFileSync(path.join(BETA, "apple-touch-icon.png"), out[180]);
  fs.writeFileSync(path.join(BETA, "favicon.ico"), ico([{ size: 32, buf: out[32] }, { size: 48, buf: out[48] }]));
  console.log("Icônes refaites depuis web/beta/favicon.svg");
})();
