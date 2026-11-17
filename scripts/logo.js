#!/usr/bin/env node
/*
 * Logo de l'Observatoire (17 nov. 2026, dessin choisi par le porteur, généré
 * avec Gemini puis redessiné en vectoriel) : même famille que le logo de
 * Votona (cercle indigo ouvert), avec un œil, une loupe dont le manche sort
 * du cercle, une courbe et des étincelles.
 *   web/beta/logo-mark.svg        logo (fonds clairs : en-tête)
 *   web/beta/logo-mark-white.svg  version blanche (images de partage, fonds sombres)
 *   web/beta/favicon.svg          logo sur carré blanc (puis node scripts/favicons.js)
 * Relancer après une retouche : node scripts/logo.js && node scripts/favicons.js
 */
const fs = require("fs");
const path = require("path");
const BETA = path.join(__dirname, "..", "web", "beta");
const INDIGO = "#463BB1", NAVY = "#2A1D62";

function star(x, y, r) {
  const k = r * 0.28;
  return `M${x} ${y - r}Q${x + k} ${y - k} ${x + r} ${y}Q${x + k} ${y + k} ${x} ${y + r}Q${x - k} ${y + k} ${x - r} ${y}Q${x - k} ${y - k} ${x} ${y - r}Z`;
}
function mark(ring, ink, accent, id) {
  const handle = "M59.5 61.5L80 82";
  return `<defs><mask id="${id}"><rect x="-10" y="-10" width="120" height="120" fill="#fff"/>` +
    `<path d="${handle}" stroke="#000" stroke-width="15" stroke-linecap="round"/></mask>` +
    `<mask id="${id}e"><rect x="-10" y="-10" width="120" height="120" fill="#fff"/><circle cx="47" cy="49" r="21" fill="#000"/></mask></defs>` +
    // cercle ouvert là où passe le manche de la loupe
    `<circle cx="50" cy="50" r="45" fill="none" stroke="${ring}" stroke-width="5.2" mask="url(#${id})"/>` +
    // œil (interrompu autour de la loupe)
    `<path d="M14 50Q50 18 86 50Q50 82 14 50Z" fill="none" stroke="${ink}" stroke-width="4.6" stroke-linejoin="round" mask="url(#${id}e)"/>` +
    // loupe
    `<circle cx="47" cy="49" r="16.5" fill="none" stroke="${ink}" stroke-width="5.2"/>` +
    `<path d="${handle}" stroke="${ink}" stroke-width="6.4" stroke-linecap="round"/>` +
    // courbe qui traverse la loupe
    `<path d="M33 54C37 44 41 43 45 51S54 59 58 45S64 31 69 29" fill="none" stroke="${ink}" stroke-width="3.6" stroke-linecap="round"/>` +
    `<path d="M33 54C37 44 41 43 45 51" fill="none" stroke="${accent}" stroke-width="3.6" stroke-linecap="round"/>` +
    // étincelles
    `<g fill="${accent}"><path d="${star(65, 25, 4.2)}"/><path d="${star(75, 37, 3)}"/><path d="${star(48, 41, 2.6)}"/><path d="${star(60, 56, 2.4)}"/></g>`;
}
const svg = (inner, vb = "0 0 100 100", size = 100) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}" width="${size}" height="${size}">${inner}</svg>\n`;

fs.writeFileSync(path.join(BETA, "logo-mark.svg"), svg(mark(INDIGO, NAVY, INDIGO, "o")));
fs.writeFileSync(path.join(BETA, "logo-mark-white.svg"), svg(mark("#fff", "#fff", "rgba(255,255,255,.75)", "w")));
fs.writeFileSync(path.join(BETA, "favicon.svg"), svg(`<rect x="-12" y="-12" width="124" height="124" fill="#fff"/>${mark(INDIGO, NAVY, INDIGO, "f")}`, "-12 -12 124 124", 48));
console.log("Logo de l'Observatoire écrit dans web/beta/");
