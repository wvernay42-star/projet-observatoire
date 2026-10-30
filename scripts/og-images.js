// Images de partage (1200×630) des pages fixes, sur le modèle de scripts/generate-og-images.js
// de Votona : une par candidat 2027 (web/beta/og/candidats/<votona_id>.jpg) et une par famille
// de sujets (web/beta/og/sujets/<famille>.jpg). Aucun chiffre ni verdict dessus : elles restent
// justes d'un jour à l'autre. build_beta les copie dans site/assets/og/, build_pages les utilise
// quand elles existent (sinon l'image générale assets/og.jpg).
//
// Les images existantes ne sont jamais réécrites (--force pour tout refaire). Demande Node,
// Playwright + Chromium (présents dans les sessions cloud) et l'accès à Google Fonts.
//
// Usage : node scripts/og-images.js [--force]

const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const BETA = path.join(ROOT, "web", "beta");
const OUT = path.join(BETA, "og");
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const hex = (c, fallback) => (/^#[0-9a-fA-F]{3,8}$/.test(c || "") ? c : fallback);
const img = (rel, type = "webp") => `data:image/${type};base64,` + fs.readFileSync(path.join(BETA, rel)).toString("base64");

// Familles : mêmes couleurs et fichiers que THEME de pipeline/build_pages.py.
const FAMILIES = [
  ["economie", "Économie & travail", "#FFB703", "economie"], ["social", "Protection sociale", "#3A86FF", "protection-sociale"],
  ["securite", "Sécurité & immigration", "#FF6B6B", "securite"], ["ecologie", "Écologie", "#06D6A0", "ecologie"],
  ["europe", "Europe & institutions", "#6C5CE7", "europe"], ["societe", "Société", "#FF5DA2", "societe"],
  ["defense", "Défense & numérique", "#00B4D8", "defense"],
];

function readCsv(file) {
  const rows = [];
  let row = [], cell = "", quoted = false;
  const text = fs.readFileSync(file, "utf8");
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n") { row.push(cell.replace(/\r$/, "")); rows.push(row); row = []; cell = ""; }
    else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const [head, ...body] = rows.filter((r) => r.some(Boolean));
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] || ""])));
}

const LOGO = img("logo-head.webp");
const FONTS = `<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@700;800&family=Work+Sans:wght@600;700&family=IBM+Plex+Mono:wght@600&display=block" rel="stylesheet">`;
const BASE_CSS = `
*{margin:0;box-sizing:border-box}
body{width:1200px;height:630px;overflow:hidden;position:relative;font-family:'Work Sans',sans-serif;color:#fff;}
.head{position:absolute;left:70px;top:56px;display:flex;align-items:center;gap:14px}
.head img{width:58px;height:auto;filter:drop-shadow(0 4px 10px rgba(0,0,0,.25))}
.brand{font-family:'Baloo 2',sans-serif;font-weight:800;font-size:32px;line-height:1}
.sub{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:15px;color:rgba(255,255,255,.75);letter-spacing:.1em;margin-top:4px}
.foot{position:absolute;left:70px;top:548px;font-weight:700;font-size:20px;color:rgba(255,255,255,.75)}
.art{position:absolute;filter:drop-shadow(0 12px 22px rgba(0,0,0,.35))}
.lens{position:absolute;left:820px;top:120px;width:330px;height:330px}`;
const HEAD = `<div class="head"><img src="${LOGO}" alt=""><div><div class="brand">Votona</div><div class="sub">OBSERVATOIRE</div></div></div>`;
// Loupe avec coche : le même pictogramme que le lien « Observatoire » de votona.fr, en grand.
const LENS = `<svg class="lens" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.92)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7" fill="rgba(255,255,255,.10)"/><path d="M8.2 11l2 2 3.6-3.8"/><line x1="16.2" y1="16.2" x2="21" y2="21" stroke-width="2.4"/></svg>`;

const initials = (name) => String(name || "").split(/[\s-]+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join("").toUpperCase();

function candidateHtml(c) {
  const color = hex(c.color, "#7C3AED");
  return `<!DOCTYPE html><html><head><meta charset="utf-8">${FONTS}
<style>${BASE_CSS}
body{background:linear-gradient(115deg, ${color} 0%, #14121F 100%);}
.who{position:absolute;left:70px;top:200px;width:700px;height:270px;display:flex;align-items:center;gap:28px}
.av{flex:none;width:112px;height:112px;border-radius:50%;background:#fff;color:${color};display:flex;align-items:center;justify-content:center;font-family:'Baloo 2',sans-serif;font-weight:800;font-size:44px;box-shadow:0 6px 24px rgba(0,0,0,.2)}
.name{font-family:'Baloo 2',sans-serif;font-weight:800;font-size:62px;line-height:1.02}
.party{margin-top:10px;font-weight:700;font-size:24px;color:rgba(255,255,255,.85)}
.kick{margin-top:16px;display:inline-block;padding:7px 16px;border-radius:99px;background:#fff;color:#191d2b;font-weight:700;font-size:18px}
</style></head><body>${HEAD}${LENS}
<div class="who"><div class="av">${esc(initials(c.name))}</div><div><div class="name">${esc(c.name)}</div><div class="party">${esc(c.votona_party)}</div><div class="kick">Ses déclarations vérifiées</div></div></div>
<div class="foot">Le verdict des fact-checkers, avec le lien vers chaque article - observatoire.votona.fr</div></body></html>`;
}

function familyHtml([, label, color, file]) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8">${FONTS}
<style>${BASE_CSS}
body{background:linear-gradient(115deg, color-mix(in srgb, ${color} 72%, #14121F) 0%, #14121F 100%);}
.cat{position:absolute;left:70px;top:186px;display:flex;align-items:center;gap:12px;padding:9px 20px 9px 16px;border-radius:99px;background:#fff;color:#191d2b;font-weight:700;font-size:19px;letter-spacing:.06em;text-transform:uppercase}
.dot{width:14px;height:14px;border-radius:50%;background:${color}}
.t{position:absolute;left:70px;width:720px;top:256px;font-family:'Baloo 2',sans-serif;font-weight:800;font-size:72px;line-height:1.05}
.s{position:absolute;left:70px;width:700px;top:430px;font-weight:700;font-size:26px;color:rgba(255,255,255,.88)}
</style></head><body>${HEAD}
<img class="art" src="${img("characters/" + file + ".webp")}" style="left:842px;top:150px;height:450px" alt="">
<img class="art" src="${img("props/" + file + ".webp")}" style="left:1040px;top:96px;width:120px;transform:rotate(12deg)" alt="">
<div class="cat"><span class="dot"></span>Sujet</div>
<div class="t">${esc(label)}</div>
<div class="s">Les déclarations politiques vérifiées par les fact-\u2060checkers</div>
<div class="foot">Le verdict de chaque rédaction, jamais le nôtre - observatoire.votona.fr</div></body></html>`;
}

async function main() {
  const force = process.argv.includes("--force");
  const jobs = [];
  for (const c of readCsv(path.join(ROOT, "data", "seeds", "candidates_2027.csv"))) {
    if (!/^[a-z0-9-]+$/.test(c.votona_id)) continue;
    jobs.push({ out: path.join(OUT, "candidats", c.votona_id + ".jpg"), html: candidateHtml(c) });
  }
  for (const f of FAMILIES) jobs.push({ out: path.join(OUT, "sujets", f[0] + ".jpg"), html: familyHtml(f) });
  const todo = jobs.filter((j) => force || !fs.existsSync(j.out));
  if (!todo.length) { console.log("Images de partage : rien à créer."); return; }
  const { chromium } = require("playwright");
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  for (const job of todo) {
    await page.setContent(job.html, { waitUntil: "networkidle" }).catch(() => {});
    await page.evaluate(() => document.fonts.ready);
    fs.mkdirSync(path.dirname(job.out), { recursive: true });
    await page.screenshot({ path: job.out, type: "jpeg", quality: 88 });
    console.log("Image de partage créée : " + path.relative(ROOT, job.out));
  }
  await browser.close();
}

main().catch((e) => { console.error(e); process.exit(1); });
