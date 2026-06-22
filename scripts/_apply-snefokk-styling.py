#!/usr/bin/env python3
"""
Tar et original-kart fra by-kart-bygger og påfører Snefokk-styling:
- Newsreader + Inter fonter
- Lilla aksent (#3D1F4D), krem (#F3EEEA), sort (#1A1A1A)
- Stor serif-tittel uten all caps
- Subtil map-container med shadow
- Snefokk POI-paletten
- Print-knapper i header
- "Din adresse"-søk med Nominatim
- Legend "Din adresse"-blokk
- Snefokk-footer

Usage: python3 _apply-snefokk-styling.py <source.html> <dest.html> [--title-cap]

--title-cap betyr at tittelen er ALL CAPS i original og skal bli proper-case.
"""
import sys
import re
import argparse

def apply_snefokk(content):
    # 1. Bytt font-import (Quicksand → Newsreader + Inter)
    content = re.sub(
        r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/css2\?family=Quicksand[^"]+">',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,700;1,6..72,400;1,6..72,500&family=Inter:wght@400;500;600&display=swap">',
        content
    )

    # 2. Bytt :root branding-variabler til Snefokk
    content = re.sub(
        r'(:root\s*\{[^}]*?--brand-dark:)\s*#[0-9A-Fa-f]+;',
        r'\1    #1A1A1A;',
        content
    )
    content = re.sub(
        r'(--brand-cream:)\s*#[0-9A-Fa-f]+;',
        r'\1   #F3EEEA;',
        content
    )
    content = re.sub(
        r'(--brand-accent:)\s*#[0-9A-Fa-f]+;',
        r'\1  #3D1F4D;',
        content
    )
    content = re.sub(
        r"(--brand-font:)\s*'Quicksand'[^;]*;",
        r"\1    'Inter', system-ui, sans-serif;\n    --brand-serif:   'Newsreader', Georgia, serif;",
        content
    )

    # 2b. Sørg for at --brand-serif alltid er definert i :root, uavhengig av
    #     hvilken font kilden brukte (token __FONT_FAMILY__, Quicksand, e.l.).
    if '--brand-serif' not in content:
        content = re.sub(
            r"(--brand-font:[^\n]*\n)",
            r"\1    --brand-serif:   'Newsreader', Georgia, serif;\n",
            content,
            count=1
        )

    # 3. Bytt POI-kategorier til Snefokk-paletten
    cat_colors = {
        '--cat-eat': '#8B3A2F',
        '--cat-stay': '#3A4F6B',
        '--cat-museum': '#3D1F4D',
        '--cat-shop': '#B58A50',
        '--cat-beauty': '#8B4A6F',
        '--cat-activity': '#4A6B3F',
        '--cat-other': '#555555',
    }
    for var, color in cat_colors.items():
        content = re.sub(
            rf'({re.escape(var)}:)\s*#[0-9A-Fa-f]+;',
            rf'\1       {color};',
            content
        )

    # 4. Header CSS: cream bg, serif title, no caps
    content = re.sub(
        r'(\.header\s*\{)\s*background:\s*var\(--brand-dark\);\s*color:\s*var\(--brand-cream\);',
        r'\1\n    background: var(--brand-cream);\n    color: var(--brand-text);\n    border-bottom: 1px solid var(--brand-accent);',
        content
    )

    # 5. .header .title-top — stor serif, no letter-spacing
    content = re.sub(
        r'\.header \.title-top\s*\{[^}]*\}',
        '''.header .title-top {
    font-family: var(--brand-serif);
    font-size: 48pt;
    font-weight: 500;
    letter-spacing: -0.015em;
    color: var(--brand-text);
    margin-bottom: 2mm;
    line-height: 1.05;
  }''',
        content
    )

    # 6. .header .title-bottom — mindre, dempet
    content = re.sub(
        r'\.header \.title-bottom\s*\{[^}]*\}',
        '''.header .title-bottom {
    font-family: var(--brand-font);
    font-size: 13pt;
    font-weight: 400;
    color: var(--brand-text);
    opacity: 0.65;
  }''',
        content
    )

    # 7. .map-container — subtle border + shadow
    content = re.sub(
        r'(\.map-container\s*\{[^}]*?)border:\s*1px solid var\(--brand-dark\);(\s*border-radius:[^;]+;)',
        r'\1border: 1px solid rgba(26, 26, 26, 0.18);\2',
        content
    )
    content = re.sub(
        r'(\.map-container\s*\{[^}]*?)background:\s*#[0-9A-Fa-f]+;([^}]*?\})',
        r'\1background: #ffffff;\n    box-shadow: 0 3mm 8mm -3mm rgba(26, 26, 26, 0.15);\2',
        content
    )

    # 8. .area-title — serif, lilla underline, transparent bg
    content = re.sub(
        r'\.area-title\s*\{[^}]*\}',
        '''.area-title {
    background: transparent;
    color: var(--brand-text);
    font-family: var(--brand-serif);
    font-size: 12pt;
    font-weight: 500;
    letter-spacing: -0.005em;
    padding: 0 0 1.5mm 0;
    border-bottom: 1px solid var(--brand-accent);
    border-radius: 0;
  }''',
        content
    )

    # 9. .qr-box — flex column centering
    content = re.sub(
        r'\.qr-box\s*\{[^}]*\}\s*\.qr-box canvas[^}]*\}',
        '''.qr-box {
    margin-top: auto;
    align-self: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-size: 7pt;
    width: 100%;
  }
  .qr-box > div {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .qr-box canvas {
    display: block;
    margin: 0 auto 1mm;
    background: transparent !important;
  }''',
        content,
        flags=re.DOTALL
    )

    # 10. QR colorLight: #ffffff → #F3EEEA
    content = re.sub(
        r"colorLight:\s*'#ffffff'",
        "colorLight: '#F3EEEA'",
        content
    )
    content = re.sub(
        r"colorDark:\s*'#000'",
        "colorDark: '#1A1A1A'",
        content
    )
    # Også fjern eventuelle condition-uttrykk for colorLight
    content = re.sub(
        r"colorLight:\s*CONFIG\.brand\.farger\s*\?\s*'#ffffff'\s*:\s*'#ffffff'",
        "colorLight: '#F3EEEA'",
        content
    )

    # 11. Print-toolbar: skjul den gamle standalone og legg til ny header-print-controls
    snefokk_extra_css = '''
  /* Skjul den gamle standalone print-toolbaren — vi flytter inn i header. */
  .print-toolbar { display: none; }

  /* Print-knapper inne i header, høyrejustert ved siden av tittelen. */
  .header-print-controls {
    display: flex;
    gap: 6mm;
    align-items: center;
    flex-shrink: 0;
  }
  .header-print-controls button {
    background: transparent;
    color: var(--brand-text);
    border: 1px solid var(--brand-text);
    border-radius: 999px;
    padding: 1.8mm 4mm;
    font-family: var(--brand-font);
    font-size: 9pt;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }
  .header-print-controls button:hover {
    background: var(--brand-accent);
    border-color: var(--brand-accent);
    color: var(--brand-cream);
  }

  /* Adresse-søk-rad (skjult på print) */
  .address-bar {
    display: flex;
    align-items: center;
    gap: 2mm;
    padding: 2mm 3mm;
    background: rgba(61, 31, 77, 0.05);
    border: 1px solid rgba(61, 31, 77, 0.25);
    border-radius: 1.5mm;
    margin-bottom: 3mm;
    font-family: var(--brand-font);
    font-size: 9pt;
  }
  .address-bar label { font-weight: 500; color: var(--brand-text); flex-shrink: 0; white-space: nowrap; }
  .address-bar input {
    flex: 1; min-width: 80px;
    padding: 1.5mm 2.5mm;
    font-family: var(--brand-font); font-size: 9pt;
    border: 1px solid rgba(26, 26, 26, 0.2);
    border-radius: 1mm;
    background: var(--brand-cream); color: var(--brand-text);
  }
  .address-bar input:focus {
    outline: none; border-color: var(--brand-accent);
    box-shadow: 0 0 0 1px var(--brand-accent);
  }
  .address-bar button {
    padding: 1.5mm 4mm;
    font-family: var(--brand-font); font-size: 8.5pt;
    font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase;
    background: var(--brand-accent); color: var(--brand-cream);
    border: 1px solid var(--brand-accent); border-radius: 999px;
    cursor: pointer; flex-shrink: 0;
    transition: background 0.15s ease, border-color 0.15s ease;
  }
  .address-bar button:hover { background: var(--brand-text); border-color: var(--brand-text); }
  .address-bar button:disabled { opacity: 0.6; cursor: wait; }
  .address-bar .remove-btn {
    background: transparent; color: var(--brand-text);
    border-color: rgba(26, 26, 26, 0.4); display: none;
  }
  .address-bar .remove-btn:hover {
    background: var(--brand-text); color: var(--brand-cream); border-color: var(--brand-text);
  }

  /* Highlight-marker + you-here */
  .poi-marker.cat-custom, .poi-marker.highlight {
    background: var(--brand-accent); border: 2px solid #fff;
    box-shadow: 0 0 0 2px var(--brand-accent), 0 2px 6px rgba(0,0,0,0.35);
    width: 24px; height: 24px; font-size: 11px;
  }
  .legend-num.cat-custom, .legend-num.highlight { background: var(--brand-accent); }

  /* "Din adresse"-blokk i legenden */
  .legend-youhere {
    margin-bottom: 3mm; padding-bottom: 2mm;
    border-bottom: 1px solid var(--brand-accent);
  }
  .legend-youhere h3 { color: var(--brand-accent) !important; border-bottom-color: var(--brand-accent) !important; }
  .legend-youhere ol { list-style: none; padding: 0; margin: 0; }
  .legend-youhere li {
    display: grid; grid-template-columns: 16px 1fr; gap: 4px;
    align-items: start; font-size: 8pt; line-height: 1.3;
  }
  .legend-youhere-icon {
    width: 14px; height: 14px; border-radius: 50%;
    background: var(--brand-accent); border: 1.5px solid #fff;
    box-shadow: 0 0 0 0.5px var(--brand-accent);
    display: inline-flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 1px;
  }
  .legend-youhere-icon svg { width: 8px; height: 8px; fill: #fff; }
  .legend-youhere-address-text { font-weight: 400; color: var(--brand-text); word-break: break-word; }

  /* "Din adresse"-markør på kartet */
  .you-here-marker {
    width: 26px; height: 26px; border-radius: 50%;
    background: var(--brand-accent); border: 2px solid #fff;
    box-shadow: 0 0 0 1px var(--brand-accent), 0 2px 8px rgba(0,0,0,0.4);
    display: inline-flex; align-items: center; justify-content: center;
  }
  .you-here-marker svg { width: 14px; height: 14px; fill: #fff; }

  /* Snefokk-footer */
  .snefokk-footer {
    margin-top: 3mm; padding-top: 2mm;
    border-top: 1px solid var(--brand-accent);
    font-family: var(--brand-font); font-size: 7pt;
    color: var(--brand-text); opacity: 0.7;
    text-align: center; line-height: 1.4;
  }
  .snefokk-footer a { color: var(--brand-accent); text-decoration: none; font-weight: 500; }
  .snefokk-footer a:hover { text-decoration: underline; }

  /* Snefokk-typografi-overrides */
  h1, h2, h3 {
    font-family: var(--brand-serif) !important;
    font-weight: 500 !important;
    letter-spacing: -0.005em;
  }

'''

    # Sett inn ekstra CSS rett før </style> i hovedstyles
    content = content.replace('</style>\n</head>', snefokk_extra_css + '</style>\n</head>', 1)

    # 12. @media print: skjul nye elementer
    content = re.sub(
        r'(@media print\s*\{[^}]*?\.print-toolbar\s*\{\s*display:\s*none\s*![^}]*\})',
        r'''\1
    .header-print-controls { display: none !important; }
    .address-bar { display: none !important; }''',
        content
    )

    # 13. renderArea: legg til print-controls i header
    # Håndter både multi-line if (med {...}) og inline if uten braces
    print_controls_decl = '''  const printControlsHtml = areaIdx === 0 ? `
    <div class="header-print-controls">
      <button onclick="printColor()">Print farger</button>
      <button onclick="printBW()">Print s/h</button>
    </div>
  ` : '';
  header.innerHTML'''

    content = re.sub(
        r"(let logoHtml = '';\s*if \(CONFIG\.brand\.logo_url\)[^\n]*?\}\s*)header\.innerHTML",
        rf"\1{print_controls_decl}",
        content,
        flags=re.DOTALL
    )
    # Også for inline if (uten braces)
    content = re.sub(
        r"(let logoHtml = '';\s*if \(CONFIG\.brand\.logo_url\)\s+logoHtml = `[^`]*`;\s*)header\.innerHTML",
        rf"\1{print_controls_decl}",
        content
    )

    # Endre header.innerHTML til å inkludere printControlsHtml
    content = re.sub(
        r"(header\.innerHTML = `\s*<div class=\"title-block\">\s*<div class=\"title-top\">\$\{CONFIG\.brand\.tittel_topp\}</div>\s*<div class=\"title-bottom\">\$\{CONFIG\.brand\.tittel_bunn\}</div>\s*</div>\s*)(\$\{logoHtml\}\s*`;)",
        r"\1${printControlsHtml}\n    \2",
        content
    )

    # 14. Legg til adresse-bar HTML i renderArea etter page.appendChild(header)
    address_bar_inject = '''  page.appendChild(header);

  /* Adresse-søk (kun på første side, kun på skjerm) */
  if (areaIdx === 0) {
    const addressBar = document.createElement('div');
    addressBar.className = 'address-bar';
    const townHint = CONFIG.brand.tittel_topp || '';
    addressBar.innerHTML = `
      <label for="address-input">Din adresse:</label>
      <input id="address-input" type="text"
             placeholder="F.eks. Strandvegen 14${townHint ? ', ' + townHint : ''}"
             onkeydown="if(event.key==='Enter') placeYouHereFromAddress()">
      <button id="address-search-btn" onclick="placeYouHereFromAddress()">Vis på kart</button>
      <button id="address-remove-btn" class="remove-btn" onclick="removeYouHereMarker()">Fjern</button>
    `;
    page.appendChild(addressBar);
  }'''

    content = re.sub(
        r'(page\.appendChild\(header\);)',
        address_bar_inject,
        content,
        count=1
    )

    # 15. Legg til legend-youhere block etter legendCol-opprettelse
    youhere_legend_inject = '''  const legendCol = document.createElement('div');
  legendCol.className = 'legend-col';

  /* "Din adresse"-blokk i legenden (skjult inntil brukeren plasserer en adresse) */
  if (areaIdx === 0) {
    const youHereBlock = document.createElement('div');
    youHereBlock.className = 'legend-category legend-youhere';
    youHereBlock.id = 'legend-youhere';
    youHereBlock.style.display = 'none';
    const starIcon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2 l2.9 6.6 7.1 .6 -5.4 4.7 1.7 6.9 -6.3 -3.7 -6.3 3.7 1.7 -6.9 -5.4 -4.7 7.1 -.6z"/></svg>';
    youHereBlock.innerHTML = `
      <h3>Din adresse / Your location</h3>
      <ol>
        <li>
          <span class="legend-youhere-icon">${starIcon}</span>
          <span class="legend-youhere-address-text" id="legend-youhere-address"></span>
        </li>
      </ol>
    `;
    legendCol.appendChild(youHereBlock);
  }'''

    content = re.sub(
        r"const legendCol = document\.createElement\('div'\);\s*legendCol\.className = 'legend-col';",
        youhere_legend_inject,
        content,
        count=1
    )

    # 16. Legg til snefokk-footer + register map etter page.appendChild(body)
    snefokk_footer_inject = '''  page.appendChild(body);

  /* Snefokk-footer */
  const snefokkFooter = document.createElement('div');
  snefokkFooter.className = 'snefokk-footer';
  snefokkFooter.innerHTML = `Dersom du vil ha endringer til dette kartet, eller ønsker et eget kart over et annet tettsted &mdash; besøk <a href="https://snefokk.com/kart/">snefokk.com/kart</a>`;
  page.appendChild(snefokkFooter);

  root.appendChild(page);'''

    content = re.sub(
        r'page\.appendChild\(body\);\s*root\.appendChild\(page\);',
        snefokk_footer_inject,
        content,
        count=1
    )

    # 17. Register maps for youHereMaps — etter L.tileLayer på mainMap
    content = re.sub(
        r"(L\.tileLayer\(TILE_URL[^)]+\)\.addTo\(mainMap\);\s*mainMap\.fitBounds\([^)]+\);)",
        r"\1\n  if (window.registerYouHereMap) window.registerYouHereMap(mainMap, area.bounds);",
        content
    )
    content = re.sub(
        r"(L\.tileLayer\(INSET_TILE_URL[^)]+\)\.addTo\(map\);)",
        r"\1\n  if (window.registerYouHereMap) window.registerYouHereMap(map, area.bounds);",
        content
    )

    # 18. Legg til "Din adresse" JS-funksjoner på slutten av script
    youhere_js = '''

/* ============================================================
   "Din adresse" — Snefokk-feature
   ============================================================ */
const youHereMaps = [];
let youHereMarker = null;
let youHereActiveMap = null;

window.registerYouHereMap = function(map, bounds) {
  if (!map) return;
  youHereMaps.push({ map, bounds: bounds ? L.latLngBounds(bounds) : null });
};

function youHereIcon() {
  const starSvg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' +
    '<path d="M12 2 l2.9 6.6 7.1 .6 -5.4 4.7 1.7 6.9 -6.3 -3.7 -6.3 3.7 1.7 -6.9 -5.4 -4.7 7.1 -.6z"/>' +
    '</svg>';
  return L.divIcon({
    className: '',
    html: '<div class="you-here-marker">' + starSvg + '</div>',
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

function chooseYouHereMap(lat, lng) {
  const point = L.latLng(lat, lng);
  for (const entry of youHereMaps) {
    if (entry.bounds && entry.bounds.contains(point)) return entry.map;
  }
  return youHereMaps.length > 0 ? youHereMaps[0].map : null;
}

async function placeYouHereFromAddress() {
  const input = document.getElementById('address-input');
  if (!input) return;
  const addr = input.value.trim();
  if (!addr) { input.focus(); return; }
  const btn = document.getElementById('address-search-btn');
  const origText = btn.textContent;
  btn.textContent = 'Søker…';
  btn.disabled = true;
  try {
    const town = (CONFIG.brand.tittel_topp || '').toLowerCase();
    const includesTown = town && addr.toLowerCase().includes(town);
    const query = includesTown ? addr : `${addr}, ${CONFIG.brand.tittel_topp}, Norway`;
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1&accept-language=no`;
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    const data = await r.json();
    if (!data.length) {
      alert(`Fant ikke adressen «${addr}». Prøv en mer presis formulering med gatenavn og nummer.`);
      return;
    }
    const lat = parseFloat(data[0].lat);
    const lng = parseFloat(data[0].lon);
    placeYouHereAt(lat, lng, data[0].display_name);
  } catch (err) {
    alert('Klarte ikke kontakte adresse-tjenesten. Sjekk nettforbindelsen.');
    console.error(err);
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

function placeYouHereAt(lat, lng, displayName) {
  if (youHereMarker && youHereActiveMap) {
    youHereActiveMap.removeLayer(youHereMarker);
  }
  const targetMap = chooseYouHereMap(lat, lng);
  if (!targetMap) { alert('Kunne ikke finne et kart å plassere markøren på.'); return; }
  youHereActiveMap = targetMap;
  youHereMarker = L.marker([lat, lng], { icon: youHereIcon(), interactive: true, zIndexOffset: 1000 }).addTo(targetMap);
  const userInput = (document.getElementById('address-input').value || '').trim();
  const shortAddr = userInput || (displayName ? displayName.split(',')[0].trim() : 'Din adresse');
  youHereMarker.bindTooltip(shortAddr, { direction: 'top', offset: [0, -12] });
  const legendBlock = document.getElementById('legend-youhere');
  const legendAddr = document.getElementById('legend-youhere-address');
  if (legendBlock) legendBlock.style.display = '';
  if (legendAddr) legendAddr.textContent = shortAddr;
  const removeBtn = document.getElementById('address-remove-btn');
  if (removeBtn) removeBtn.style.display = 'inline-block';
}

function removeYouHereMarker() {
  if (youHereMarker && youHereActiveMap) {
    youHereActiveMap.removeLayer(youHereMarker);
  }
  youHereMarker = null;
  youHereActiveMap = null;
  const removeBtn = document.getElementById('address-remove-btn');
  if (removeBtn) removeBtn.style.display = 'none';
  const input = document.getElementById('address-input');
  if (input) input.value = '';
  const legendBlock = document.getElementById('legend-youhere');
  if (legendBlock) legendBlock.style.display = 'none';
  const legendAddr = document.getElementById('legend-youhere-address');
  if (legendAddr) legendAddr.textContent = '';
}
'''

    # Legg JS-en før </script> rett før </body>
    content = re.sub(
        r'(</script>\s*</body>)',
        youhere_js + r'\1',
        content,
        count=1
    )

    return content


def fix_title_caps(content, original_caps, proper_case):
    """Bytt all-caps tittel til proper case (f.eks. VARDØ → Vardø)"""
    return content.replace(
        f'"tittel_topp": "{original_caps}"',
        f'"tittel_topp": "{proper_case}"'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('dest')
    parser.add_argument('--title-caps-from', help='ALL CAPS-tittel i original')
    parser.add_argument('--title-caps-to', help='Proper case-tittel som skal erstatte')
    args = parser.parse_args()

    with open(args.source, 'r') as f:
        content = f.read()

    content = apply_snefokk(content)

    if args.title_caps_from and args.title_caps_to:
        content = fix_title_caps(content, args.title_caps_from, args.title_caps_to)

    with open(args.dest, 'w') as f:
        f.write(content)

    print(f"OK: {args.source} → {args.dest}")


if __name__ == "__main__":
    main()
