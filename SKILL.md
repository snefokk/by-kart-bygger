---
name: by-kart-bygger
description: Lag et printbart A4-turistkart/bykart for en norsk kommune basert på et gammelt kart (foto/PDF) eller fra bunnen av. Skillen tolker det gamle kartet, verifiserer at bedriftene fortsatt er aktive via Brønnøysundregistrene, slår opp riktige koordinater i Google Maps, spør kommunen om tillegg, og bygger en ferdig HTML-fil klar til print. Bruk denne skillen når brukeren sier "lag bykart", "lag turistkart", "oppdater det gamle kartet vårt", "vi har et gammelt kart vi vil ha digitalt", "generer kommunekart for X", "lag printbart kart for kommunen", eller laster opp et bilde/PDF av et gammelt kart og vil ha det fornyet. Bruk også hvis noen ber om et POI-kart, næringskart, sentrumskart, eller A4-kart med bedrifter/severdigheter — selv om de ikke eksplisitt bruker ordet "skill" eller "kommunekart".
---

# By-kart-bygger – printbart turist-/bykart for en norsk kommune

Denne skillen tar deg gjennom hele prosessen med å lage et oppdatert, printbart A4-kart for en kommune: tolke et gammelt kart, verifisere at bedriftene fortsatt finnes, plassere dem riktig, og bygge HTML-en.

All kommunikasjon med brukeren skjer på **norsk**.

## Hva trenger du før du starter

- **Claude in Chrome** (eller tilsvarende nettleser-MCP) — for Google Maps-oppslag
- **Bash/Python** — for å kjøre BRREG-oppslag og bygge HTML-en
- **Workspace-tilgang** — alle filer lagres i brukerens workspace-mappe

Sjekk at disse er tilgjengelige før du begynner; hvis ikke, gi brukeren beskjed.

**Filplassering:** `scripts/`, `templates/` og `references/` ligger i skillens basemappe — bruk full sti fra basemappen når du kjører kommandoer. Arbeidsfiler og ferdige kart (`outputs/...`) lagres i brukerens workspace-mappe.

## Overordnet flyt

```
1. Samle utgangspunktet  →  gammelt kart? hvilke punkter?
2. Verifiser hver bedrift mot Brønnøysundregistrene
3. Slå opp koordinater i Google Maps (eller bekreft eksisterende)
4. Spør brukeren om tillegg
5. Bestem områder/sider (auto-clustering)
6. Velg branding (kommunens nettside eller snefokk-generisk)
7. Kartfliser (CARTO Voyager tiles — ingen SVG-generering nødvendig)
8. Bygg HTML-en med templates/kart_template.html + scripts/build_html.py
9. Lever ferdig fil
```

Ikke hopp over trinn — selv om brukeren virker utålmodig, vil verifiserings­trinnene spare dem for å trykke et kart med døde bedrifter.

## Trinn 1: Samle utgangspunktet

Først, fastslå utgangspunktet ved å sjekke om brukeren har lastet opp et gammelt kart (bilde/PDF) som vedlegg i meldingen, eller referert til en lokal fil.

**Hvis det er et gammelt kart**:

- For PDF: bruk `pdf`-skillen til å konvertere til bilder eller hent ut tekst først
- For bilde: les bildet direkte med Read-verktøyet (modellen kan se bilder native)
- Identifiser alle POIs (Points of Interest): bedrifter, severdigheter, overnatting, spisesteder, butikker, museer
- Forsøk å lese kategori, navn og posisjon for hvert punkt

**Hvis det ikke er et gammelt kart**:

- Spør brukeren via AskUserQuestion hvilke type punkter de vil ha med (kategorier) og om de har en liste
- Eller spør om navnet på kommunen og foreslå at du kan starte fra Google Maps + lokal næringsforening

**Sett opp en arbeids-liste** med foreløpige punkter slik:

```json
{
  "kommune": "Vadsø",
  "punkter": [
    { "navn": "Vadsø Kino", "kategori": "activity", "kilde": "gammelt kart", "lat": null, "lng": null, "brreg_status": null },
    ...
  ]
}
```

Lagre dette i `outputs/kart-arbeid/punkter-utkast.json` for å holde oversikt.

## Trinn 2: Verifiser hver bedrift mot Brønnøysundregistrene

For hvert punkt som ser ut som en næringsbedrift (ikke kirker, museer, naturpunkter), kjør oppslag mot BRREG. Bruk `scripts/brreg_lookup.py`:

```bash
python3 scripts/brreg_lookup.py "Vadsø Hotell" --kommune Vadsø
```

`--kommune` sender kommunenavnet direkte til BRREG-API-et (`forretningsadresse.kommune`). Ingen lokal kommunenummer-tabell er nødvendig — API-et matcher kommunenavn uavhengig av store/små bokstaver. Bruk `--kommunenummer` kun hvis kommunenavnet gir feil treff (f.eks. ved navneendring etter kommunesammenslåing).

**VIKTIG:** BRREG `forretningsadresse` er **juridisk adresse** — ofte regnskapsfører, hjemadresse, eller hovedkontor. Den er IKKE nødvendigvis besøksadressen. Bruk aldri BRREG-adresser som koordinatkilde for kartet — det er Trinn 3 sin jobb (Google Maps).

Scriptet returnerer JSON med:

- `funnet: true/false` — om bedriften finnes i registeret
- `aktiv: true/false` — om den er aktiv (ikke slettet, ikke konkurs, ikke under avvikling)
- `navn_offisielt` — registrert navn (kan avvike fra kallenavnet)
- `adresse` — juridisk adresse (IKKE besøksadresse!)
- `kommune` — registrert kommune
- `slettedato` — hvis slettet, dato for sletting

**Behandling av resultater**:

- `aktiv: true` → behold punktet
- `aktiv: false` (slettet/konkurs) → flagg for fjerning, vis brukeren listen til slutt så de kan bekrefte
- `funnet: false` → kan være enkeltpersonforetak under privat navn, eller ikke-næring. Flagg som «trenger manuell sjekk» men ikke fjern automatisk

Oppdater `punkter-utkast.json` med BRREG-status for hvert punkt.

## Trinn 3: Hent koordinater fra Google Maps

Som nevnt i Trinn 2: BRREG-adressen er juridisk adresse, ikke besøksadresse. Bruk derfor Google Maps som primær kilde for koordinater på turistkartet.

Prioriteringen er:

1. **Brukerinput** — hvis brukeren gir deg en spesifikk adresse, bruk den
2. **Google Maps via Claude in Chrome** — autoritativ for besøksadresse
3. **OSM Nominatim med bedriftsnavn** — gratis fallback hvis Google blokkerer
4. **BRREG forretningsadresse** — siste utvei, men flagg som lav-konfidens

**Google Maps-flyten:**

For hvert POI uten verifisert besøksadresse, bruk Claude in Chrome:

1. `navigate` til `https://www.google.com/maps/search/<bedriftsnavn>+<kommune>`
2. `wait` 5 sekunder for at kartet skal laste
3. `screenshot` (for å se hva Google fant)
4. Les den nye URL-en — Google legger koordinater på formen `/@LAT,LNG,ZOOM/` etter at kartet sentrerer

**Tre mulige utfall ved Google Maps-oppslag:**

a) **Eksakt match (place URL)** — `/maps/place/<navn>/@LAT,LNG,17z/...`
   → Direkte treff. Bruk koordinatene. Sjekk samtidig om Google sier «Permanently closed» — i så fall flagg for fjerning.

b) **Bare søkeresultater (search URL)** — `/maps/search/<query>/@LAT,LNG,15z/`
   → Generelt område, ikke spesifikk match. Sjekk screenshot for alternative navn — Google kan ha bedriften under et annet navn (f.eks. «Coop» → «Extra Båtsfjord», «Sparebank» → «Nokas Minibank»). Søk igjen med det nye navnet.

c) **Ingen relevant treff** — søkeresultatet er irrelevant eller tomt
   → Legg POI-en i en `ikke_funnet`-liste. IKKE bare bruk BRREG-adressen som fallback uten å fortelle brukeren.

### Ikke-funn-rapportering

Etter at Google Maps-runden er ferdig, presenter en oppsummering:

- POIs som ble flyttet til riktig besøksadresse (med før/etter-koordinater)
- POIs som ble omdøpt (f.eks. «Coop Marked» → «Extra Båtsfjord»)
- POIs flagget som permanent stengt (fjern automatisk eller spør)
- **POIs som ikke ble funnet** — vis listen i samtalen og still ett tydelig spørsmål: «Disse fant jeg ikke i Google Maps: [liste]. Vil du fjerne dem, eller har du riktig adresse for noen av dem?» Brukeren svarer i fritekst per punkt. Punkter uten avklaring fjernes; punkter brukeren eksplisitt vil beholde uten adresse markeres som uverifisert anslag.

Sett `displayLat`/`displayLng` lik `lat`/`lng` som standard — overstyringer for visuell plassering håndteres senere ved tett klynging.

For hvert POI, lagre også:

- `adresse`: gateadresse for `spreadByAddress()` (POIs i samme bygg plasseres ved siden av hverandre)
- `coord_kilde`: «Google Maps» / «OSM» / «BRREG» / «anslag»
- `coord_note`: kort beskrivelse av hva som ble bekreftet

### Koordinat-verifisering (OBLIGATORISK)

**Alle koordinater SKAL verifiseres visuelt — også de som allerede finnes i en eksisterende config, kommer fra et gammelt kart, eller er oppgitt av brukeren.** Avrundede eller gjettede koordinater ender ofte i sjøen, på feil side av veien, eller på en parkeringsplass.

For HVERT punkt, gjør følgende:

1. **Søk opp koordinatene i Google Maps** — naviger til `https://www.google.com/maps/search/<lat>,+<lng>` og ta screenshot
2. **Sjekk at pinnen treffer riktig sted:**
   - Ligger den på land? (Ikke i sjøen, innsjøen, eller elven)
   - Ligger den på/ved riktig bygning? (Ikke på parkeringsplassen ved siden av, ikke på nabotomten)
   - Stemmer gateadressen som Google viser med det du forventer?
3. **Sjekk Plus-koden** — Google Maps viser en Plus-kode for hvert punkt. Sammenlign med evt. kjent Plus-kode.
4. **Flagg og korriger** feil:
   - Hvis pinnen er i sjøen → koordinatene er feil. Søk opp stedsnavnet i Google Maps og bruk de riktige koordinatene.
   - Hvis pinnen er mer enn ~50 m fra bygningen → juster til riktig posisjon.
   - Logg korreksjonen: `coord_note: "Korrigert fra 70.365/31.091 (sjøen) til 70.3639/31.0946 (verifisert Google Maps)"`

**Typiske feil du skal fange:**

- Koordinater med for få desimaler (f.eks. `70.365, 31.091`) — disse er ofte avrundet og havner feil
- Koordinater kopiert fra feil kilde (BRREG-adresse vs. besøksadresse)
- Koordinater fra et gammelt kart som var unøyaktige i utgangspunktet
- Naturpunkter (gapahuker, utsiktspunkter, vindskjul) som ofte ikke har nøyaktig adresse og lett havner i sjøen

**Denne verifiseringen gjelder ALLE punkter, HVER gang — ikke bare nye.** Hvis du får en ferdig config-fil med koordinater, verifiser dem likevel. Det er billigere å bruke 2 minutter per punkt nå enn å trykke et kart med feilplasserte markører.

### Duplikat-koordinater (OBLIGATORISK sjekk)

**Før du bygger kartet, kjør en automatisk sjekk for punkter med identiske koordinater.** Bruk et enkelt Python-script som grupperer alle punkter etter `(lat, lng)` og rapporterer grupper med 2+ punkter.

Identiske koordinater kan bety:

- **Samme bygg** — f.eks. et kjøpesenter med flere butikker, eller en bygning med hotell + galleri + treningssenter. Da er koordinatene riktige, og `spreadByAddress()` i templaten fanner dem ut visuelt. Logg som bekreftet.
- **Lat/lng kopiert fra et annet punkt** — en vanlig feil når noen legger inn data manuelt og glemmer å oppdatere koordinatene. Slå opp hvert punkt individuelt i Google Maps for å verifisere.
- **Standardverdi / placeholder** — f.eks. `0, 0` eller kommunesenteret. Disse MÅ rettes.

**Fremgangsmåte:**

1. Kjør duplikat-sjekken:
   
   ```python
   coords = {}
   for p in places:
    key = (p['lat'], p['lng'])
    coords.setdefault(key, []).append(p)
   for key, group in coords.items():
    if len(group) > 1:
        print(f"DUPLIKAT {key}: {[p['name'] for p in group]}")
   ```

2. For hver duplikat-gruppe, spør deg selv: **er det sannsynlig at disse er i samme bygg?**
   
   - «Vardø Motell» + «Galleri Luna» + «Treningssenter» → kanskje samme bygningskompleks, men sjekk i Google Maps
   - «Vitusapotek» + «Strandgata Blomster» → sannsynligvis naboer i samme handlegate, men sjekk
   - «Rema 1000» + «Vardøhus festning» → helt usannsynlig — en av dem er feil

3. **Slå opp hvert punkt i duplikat-gruppen individuelt i Google Maps** og verifiser at de faktisk er på samme sted. Hvis ikke, korriger koordinatene.

4. Informer brukeren kort om resultatet: hvilke duplikat-grupper som ble bekreftet (samme bygg) og hvilke koordinater som ble korrigert. Spør bare hvis Google Maps-oppslaget ikke ga et entydig svar.

## Trinn 4: Spør brukeren om tilleggspunkter

Når listen er verifisert og koordinat-satt, presenter den for brukeren via AskUserQuestion eller direkte i samtalen, og spør:

- «Er det noen punkter du vil legge til?»
- «Er det noen kategorier som mangler?»
- «Skal vi fjerne disse som ser ut til å være slettet i BRREG: [liste]?»

La brukeren legge til punkter i fritekst — du tar dem så gjennom samme verifisering (BRREG + Google Maps).

## Trinn 5: Bestem områder og sider

Cluster punktene geografisk for å avgjøre hvor mange A4-sider kartet trenger:

- **Bare ett tett cluster** → én side, én kart, evt. inset for sentrum
- **Sentrum + ett mindre tettsted** → to sider eller to kart på samme side
- **Flere spredte tettsteder** → flere sider (én per tettsted)

Bruk DBSCAN-lignende logikk: punkter innenfor ~2 km av hverandre er samme cluster. Hvis et cluster har 15+ punkter og diameter under 500 m, foreslå et inset-kart for det tette området.

Spør brukeren om område-titler («Vadsø sentrum», «Vestre Jakobselv», osv.).

### Trinn 5a: Velg mellom overview+inset eller single-map

**Tommelfingerregel for size-thresholds**:

| Hovedklynge (POI-bbox)                                                        | Render-modus       | Begrunnelse                                                                                                                                                                                              |
| ----------------------------------------------------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| < ~1 km diameter, alle POIs i sentrum                                         | `single_map: true` | Tettstedet er så lite at alt passer i ett kart ved zoom 16. Eksempel: Båtsfjord.                                                                                                                         |
| 1–3 km, POIs spredt over et større område med viktige punkter utenfor sentrum | overview + inset   | Viktige severdigheter (festninger, memorialer, utsiktspunkter) som ligger utenfor sentrum må vises ordentlig — ikke bare som en pil. Eksempel: Vardø med Vardøhus festning, Steilneset Memorial, Skagen. |
| > 3 km (flere tettsteder)                                                     | flere sider        | Bruk én side per tettsted.                                                                                                                                                                               |

**VIKTIG: Velg overview+inset når viktige POIs ellers bare ville blitt piler.** En pilmarkør ved kanten sier «dette finnes der borte» — men for en festning, et memorial, eller en annen hovedattraksjon er det ikke godt nok. Brukeren trenger å se disse på et ordentlig kart. Bruk `single_map` bare når ALLE viktige POIs faktisk passer innenfor synsfeltet ved zoom 16.

Beregn POI-bbox SLIK at outliers (et hotell 5 km utenfor sentrum, en flyplass, en parkeringsplass i kommunegrensen) ikke teller. I `single_map`-modus oppdager templaten automatisk hvilke POIs som er utenfor synsfeltet og rendrer dem som pilmarkører ved kanten — du trenger IKKE sette `arrow` manuelt.

Når du velger `single_map`-modus:

- Sett `area.single_map: true` i config-JSON
- Kartet bruker **fast zoom 16.0** (Vadsø inset-standard) — dette gir konsistente, lesbare gatenavn på tvers av alle kommuner
- **Auto-rotasjon**: templaten prøver alle vinkler ±90° fra nord og velger den som gir flest POIs innenfor synsfeltet. Sett `area.rotation` for å overstyre (grader med klokken fra nord)
- POIs innenfor synsfeltet → vanlige markører
- POIs utenfor synsfeltet → automatiske pilmarkører (↑↓←→) ved kanten som peker mot ekte plassering, med avstandsinfo i tooltip
- Pilmarkører de-overlappes automatisk i pikselrom slik at de ikke sitter oppå hverandre
- Legenden er smal (48mm) for å gi kartet maksimal plass

### Trinn 5b: Spør brukeren hvilket område som skal være «sentrum» / inset

VIKTIG — ikke gjett hva sentrum er. Det varierer fra by til by hva folk regner som «sentrum», og det er ofte ikke det samme som det geometriske midtpunktet av punktene. Bygg derfor først et midlertidig kart over hele kommunen (uten inset), del det med brukeren, og still et eksplisitt spørsmål om detaljområdet.

Bruk `AskUserQuestion` med 3–4 forhåndsforeslåtte avgrensninger basert på hvor punktene ligger, f.eks.:

- **«Hele hovedgata + havna»** (typisk det folk mener med sentrum)
- **«Bare handlegate-stripa»** (smalere, fokus på butikker/spisesteder)
- **«Hele tettstedet inkludert kirken»** (videre, tar med severdigheter i utkanten)
- **«La meg tegne det selv»** — be brukeren oppgi 2 hjørner som lat/lng eller pek ut landemerker som skal være innenfor

Etter at brukeren har valgt, sett `inset.bounds = [[sørLat, vestLng], [nordLat, østLng]]` i config-JSON. `inset.bounds` brukes som et **filter** — alle POIs som ligger innenfor denne firkanten blir med på detaljkartet. Det er IKKE det faktiske rendrede utsnittet.

**Auto-tightening i templaten**: når kartet rendres, regner JavaScript-en ut den tetteste bounding-boxen rundt de POIs som havnet i inset, og bruker den som zoom-target. Det betyr at:

- Det er ingen problem om `inset.bounds` har stor dødplass (vann, parker, ubebygde områder) — kartet zoomer automatisk inn til der POIs faktisk ligger
- Et punkt helt ved kanten av synsfeltet er OK — det er det vi vil ha for maksimal zoom
- Gatenavn blir så lesbare som det fysisk er mulig gitt punktenes spredning

**Inset-optimalisering: Maksimer antall POIs i innsettet (OBLIGATORISK)**

Målet med innsettet er å vise **flest mulig POIs** ved zoom 16 med lesbare gatenavn. Templaten auto-tightener til tetteste bounding-box rundt inset-POIs, så én outlier kan dra hele zoomen utover og gjøre gatenavn uleselige.

**Algoritme — fjern outliers automatisk, informer brukeren etterpå:**

1. Start med alle POIs innenfor `inset.bounds` — kall dette settet S.
2. Beregn bounding-box for S (min/maks lat og lng).
3. For hvert punkt P i S: beregn bounding-box for S minus P. Regn ut hvor mye bounding-boxen krymper (i meter) dersom P fjernes.
4. Finn punktet P* som gir størst krymping. Hvis P* krymper boksen med >30 % i enten bredde eller høyde, er det en outlier.
5. Flytt P* til `force_main_ids` automatisk — ikke spør brukeren.
6. Gjenta fra steg 2 med oppdatert S til ingen enkelt-punkt gir >30 % krymping.
7. Når algoritmen er ferdig, informer brukeren kort: «Jeg flyttet [navn] til oversiktskartet fordi det lå utenfor sentrums-clusteret og dro zoomen utover. Det vises som vanlig markør på det store kartet.»

**Tommelfingerregel**: fjern alltid det punktet som er lengst unna tyngdepunktet av clusteret — IKKE den tette gruppen som utgjør kjernen. Hvis du ser at du er i ferd med å fjerne en gruppe på 3+ punkter som ligger nært hverandre, stopp — da er det feil retning.

**Pass på følgende i tillegg:**

1. Bounds bør ha fornuftig aspect ratio — hvis POIs ligger på en lang stripe (f.eks. én gate), vurder å dele i to inset eller akseptere stripe-formet utsnitt.
2. Etter første bygg: åpne HTML-en og bekreft visuelt at gatenavnene er lesbare. Hvis ikke, kjør outlier-algoritmen på nytt og fjern neste outlier.

Det runtime self-check-et i templaten skriver `console.warn` hvis et POI faller utenfor — sjekk DevTools-konsollen ved tvil.

### Trinn 5c: Fast-skala-motor (VIKTIG)

Templaten bruker en **fast-skala-motor** som sikrer konsistent zoom på tvers av alle kommuner:

- **Adaptiv zoom (mål: 16.0, min: 15.0)** — starter på referanse-zoom 16.0 (hentet fra Vadsø turistkart inset, ~0.817 m/px ved lat 70°). Hvis <80 % av POIs er synlige ved zoom 16, stepper templaten ned med 0.25 til ≥80 % passer (minimum 15.0). Beregningen skjer i meter-rom (synkront, uavhengig av Leaflet rendering). Gatenavnene forblir lesbare ned til 15.0.
- **Auto-rotasjon** — prøver alle vinkler ±90° fra nord (aldri opp-ned). For hver vinkel telles hvor mange POIs som faller innenfor synsfelt-rektangelet i meter-rom. Vinkelen med flest POIs vinner; ved likt antall velges den med tettest bounding-box.
- **Pikselbasert synlighetssjekk** — `map.getBounds().contains()` er upålitelig med roterte kart. Templaten bruker `map.latLngToContainerPoint()` for å sjekke om et punkt faktisk er synlig.
- **Retina-tiles** — bruker `{r}` i tile-URL for skarpe gatenavn på HiDPI/Retina-skjermer.
- **4-retnings pilmarkører** — POIs utenfor kartet får pil (↑↓←→) som peker mot faktisk posisjon. Gjelder BÅDE single_map-modus OG oversiktskartet i overview+inset.
- **Kant-de-overlap** — pilmarkører skyves fra hverandre i pikselrom (min 24px avstand) så de ikke overlapper.
- **Målestokk-bar** — beregnes fra mpp (meters per pixel) ved referanse-zoom.
- **Auto-tight oversiktskart** — i overview+inset-modus beregner templaten zoom-nivået fra de ~60 % nærmeste POIs (kjerne-clusteret), ikke alle POIs. Outlier-POIs på oversiktskartet vises som pilmarkører ved kanten, akkurat som i single_map-modus. Dette gir mer innzoomet oversiktskart med mindre tomrom. `area.bounds` brukes IKKE lenger for zoom — det er POI-fordelingen som styrer.
- **Nordpil-kollisjon** — nordpila prøver fire hjørner (øverst høyre → nederst høyre → nederst venstre → øverst venstre) og velger det første hjørnet uten overlapp med en POI-markør. Øverst venstre hoppes alltid over på inset-kart fordi «Sentrum / Town centre»-labelen ligger der. Gjelder alle kartmoduser (overview, inset, single_map).
- **Lik kartstørrelse** — i overview+inset-modus skal oversiktskartet og innsettet ALLTID ha lik størrelse på siden (begge `flex: 1`). Aldri gi det ene kartet mer plass enn det andre.

Config-felter for `single_map`-modus:

```json
{
  "single_map": true,
  "rotation": null,
  "places": [...]
}
```

- `rotation: null` → auto-beregning (anbefalt)
- `rotation: 45` → tvunget 45° med klokken fra nord
- Du trenger IKKE sette `arrow` på enkelt-POIs — synlighet og piler beregnes automatisk ved rendering

### Trinn 5d: Nord-pil og målestokk

Alle kart får automatisk:

- **Nord-pil** i øvre høyre hjørne — beregnes fra Leaflets projeksjon slik at den er korrekt selv med roterte kart. Bruker `--brand-accent`-fargen.
- **Målestokk-bar** i nedre venstre hjørne — viser avstand i meter/km basert på faktisk zoom-nivå.

## Trinn 6: Velg branding

Spør brukeren hvilken visuell stil de vil ha:

**Alternativ A: Hent fra kommunens nettside (standard)**

- Brukeren oppgir URL (f.eks. kommunens nettside eller næringsforeningens)
- Bruk Claude in Chrome til å navigere til nettsiden og hent ut branding **automatisk** med JavaScript:

**Steg 1: Hent font**
Kjør dette i nettleseren via `javascript_tool`:

```javascript
// Sjekk for Google Fonts-lenker
const fontLinks = Array.from(document.querySelectorAll('link[href*="fonts.google"]')).map(l => l.href);
// Sjekk beregnet font på body
const bodyFont = getComputedStyle(document.body).fontFamily;
JSON.stringify({ fontLinks, bodyFont });
```

- Hvis det finnes en Google Fonts-lenke → bruk den som `font_url` og fontnavnet som `font_family`
- Hvis det ikke finnes en Google Fonts-lenke → sjekk om `bodyFont` inneholder en kjent webfont (Open Sans, Roboto, Lato, etc.) og generer en tilsvarende Google Fonts URL
- Hvis bare system-fonts → bruk system-ui stack og dropp `font_url`

**Steg 2: Hent farger**
Kjør dette i nettleseren:

```javascript
const body = getComputedStyle(document.body);
// Finn primærfarge: typisk header/nav bakgrunn (den mørke fargen)
const allDivs = document.querySelectorAll('div, nav, header, ul');
let primary = null;
for (const el of allDivs) {
  const bg = getComputedStyle(el).backgroundColor;
  if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== body.backgroundColor && bg !== 'rgb(255, 255, 255)') {
    const m = bg.match(/rgb\((\d+), (\d+), (\d+)\)/);
    if (m) {
      const [_, r, g, b] = m.map(Number);
      // Mørk farge = sannsynlig header/nav
      if (r + g + b < 400) { primary = bg; break; }
    }
  }
}
JSON.stringify({
  primary: primary,
  secondary: body.backgroundColor,
  text: body.color
});
```

- `primary` → header/nav-bakgrunn (den dominerende mørke fargen)
- `secondary` → side-bakgrunn (typisk lys)
- `accent` → se etter knapper, logofarger, eller lenkefarger som skiller seg ut. Hvis du ikke finner noen tydelig accent, bruk en komplementærfarge til primary.
- `text` → body tekstfarge

**Steg 3: Konverter til hex**
RGB-verdier fra `getComputedStyle` er på formen `rgb(15, 47, 111)` — konverter til hex (`#0F2F6F`) for config-filen.

**VIKTIG: Bruk ALLTID fonten fra den oppgitte nettsiden.** Ikke hardkod Quicksand eller noen annen font. Hvert kart skal ha fonten som matcher kommunens/oppdragsgiverens nettside.

**Alternativ B: Snefokk-generisk** (bare hvis brukeren ikke har en nettside)

- Bruk `templates/snefokk-generisk/style.json`
- Dette gir en pen, nøytral grønn-cream-stil

Brand-JSON-strukturen er:

```json
{
  "navn": "Berlevåg kommune",
  "logo_url": null,
  "farger": {
    "primary":   "#0F2F6F",
    "secondary": "#F5FAFE",
    "accent":    "#E8B830",
    "text":      "#333333"
  },
  "font_url": "https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap",
  "font_family": "'Open Sans', system-ui, sans-serif",
  "tittel_topp": "BERLEVÅG",
  "tittel_bunn": "Bykart · City Map"
}
```

**QR-kode:** Spør samtidig hvilken nettside QR-koden på kartet skal peke til (typisk kommunens turistside eller næringsforeningens side). Lagre URL-en som `qr_url` og en kort visningstekst som `qr_label` i config-en.

## Trinn 7: Kartfliser (tiles)

Kartet bruker **Leaflet med CARTO Voyager-fliser** som kartbakgrunn. Dette gir OSM sine native stiler med lesbare gatenavn og korrekt kystlinje/vann ved alle zoom-nivåer, med retina-støtte via `{r}` i tile-URL-en. Du trenger ikke generere noe kartbakgrunn selv.

Tile-URL: `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png`

Templaten legger på et subtilt sepia/desaturerings-filter (`sepia(0.22) saturate(0.7) brightness(1.03)`) for å gi flisene et varmere, print-vennlig utseende.

Merk: flisene lastes fra CARTO sin tile-server, så HTML-en krever internettforbindelse ved første visning (flisene caches i nettleseren).

## Trinn 8: Bygg HTML-en

Bygg ved hjelp av `templates/kart_template.html` og `scripts/build_html.py`. Lag en config-JSON med alle data:

```json
{
  "tittel": "Vardø Turistkart",
  "qr_url": "https://www.vardo.kommune.no/turist-og-besokende",
  "qr_label": "vardo.kommune.no",
  "brand": {
    "tittel_topp": "VARDØ",
    "tittel_bunn": "Turistkart · Tourist map",
    "logo_url": null,
    "font_url": "https://fonts.googleapis.com/css2?family=...",
    "font_family": "'Inter', system-ui, sans-serif",
    "farger": {
      "primary":   "#1A1A1A",
      "secondary": "#F3EEEA",
      "accent":    "#3D1F4D",
      "text":      "#1A1A1A"
    }
  },
  "categories": [
    { "id": "eat",      "label_no": "Spisesteder",         "label_en": "Eateries",         "color": "#B85C38" },
    { "id": "stay",     "label_no": "Overnatting",          "label_en": "Accommodation",    "color": "#5B7B6D" },
    { "id": "museum",   "label_no": "Severdigheter",        "label_en": "Sights & museums", "color": "#7B5E7B" },
    { "id": "shop",     "label_no": "Butikker",             "label_en": "Shops",            "color": "#C49A5C" },
    { "id": "beauty",   "label_no": "Salonger & velvære",   "label_en": "Beauty & wellness","color": "#B56576" },
    { "id": "activity", "label_no": "Aktiviteter & natur",  "label_en": "Activities & nature","color": "#6B8055" },
    { "id": "other",    "label_no": "Service & transport",   "label_en": "Service & transport","color": "#7D7068" }
  ],
  "areas": [
    {
      "title": null,
      "bounds": [[70.361, 31.075], [70.390, 31.130]],
      "places": [
        { "id": 1, "cat": "eat", "lat": 70.0745, "lng": 29.7522, "name": "Eksempel Restaurant" }
      ],
      "inset": {
        "bounds": [[70.3690, 31.0930], [70.3760, 31.1140]],
        "label": "Sentrum / Town centre",
        "force_inset_ids": [],
        "force_main_ids": []
      }
    }
  ]
}
```

Bygg HTML-en med build-scriptet:

```bash
python3 scripts/build_html.py \
  --config outputs/kart-arbeid/config.json \
  --template templates/kart_template.html \
  --output outputs/<kommune>-turistkart.html
```

Templaten håndterer:

- Print-CSS (A4 portrett, 10 mm margins, page-break mellom områder)
- **Leaflet-kart med CARTO Voyager-tiles** (OSM native stiler, lesbare gatenavn)
- Fast-skala-motor med adaptiv zoom (mål 16.0, min 15.0) og auto-rotasjon
- Pikselbasert synlighetssjekk for POIs
- 4-retnings pilmarkører (↑↓←→) for POIs utenfor synsfelt, med automatisk de-overlap
- Nordpil med kollisjon-unngåelse (prøver 4 hjørner)
- Målestokk-bar beregnet fra faktisk zoom
- Kategorifargede markører (divIcon med tall)
- 2-kolonne kategori-liste i sidekolonnen
- QR-kode (qrcodejs)
- Auto-spread for overlappende markører (spreadByAddress + spreadOverlapping)
- Norsk + engelsk parallellkolonne i legend
- «Marker din adresse»-funksjon — sluttbrukere kan markere en valgfri adresse på kartet (se Spesialtilfeller)
- Snefokk-logo og «snefokk.com»-lenke i bunnen av hver side — innebygd som inline SVG i malen, krever ingen konfigurasjon og ingen bildefiler

## Trinn 9: Lever filen

Kopier den endelige HTML-en til workspace-mappa brukeren har valgt, og presenter filstien som en klikkbar lenke i en kort melding. Foreslå at brukeren:

- Åpner fila i nettleseren for å sjekke at alt ser riktig ut
- Bruker Cmd/Ctrl+P og velger «Save as PDF» for å lage en print-versjon
- Skriver ut på tykt A4-papir (helst 170 g eller mer)

## Spesialtilfeller

### Markører som ligger utenfor kartet

Dette håndteres **automatisk** i alle kartmoduser: templaten sjekker pikselbasert om hver POI er synlig, og plasserer usynlige POIs som pilmarkører (↑↓←→) ved nærmeste kant. Pilene peker mot den faktiske posisjonen, og tooltip-en viser avstand i km. Kantmarkørene de-overlappes automatisk.

Templaten støtter også manuell overstyring per POI (`arrow: 'right'` osv. i config), men sett den ALDRI selv som standard — bruk den bare hvis du visuelt har bekreftet at automatikken plasserer en pil feil.

### Markører som overlapper

`spreadByAddress`-funksjonen grupperer POIs med identiske koordinater i en sirkel. `spreadOverlapping`-funksjonen skyver deretter gjenværende overlapp fra hverandre. Begge kjøres automatisk.

### Punkter helt på kanten av et inset-kart

Bruk `force_inset_ids` / `force_main_ids` i inset-config for å overstyre hvilket kart punktet havner på. Se **Inset-optimalisering** i Trinn 5b for algoritmen som identifiserer hvilke punkter som bør flyttes — fjern alltid outlieren, aldri clusteret.

### Rotasjon som gir for mange POIs utenfor

Hvis auto-rotasjonen ikke gir godt nok resultat (f.eks. en veldig lang, smal by), kan du overstyre med `area.rotation: <grader>`. Test visuelt og justér.

### «Marker din adresse»-funksjonen

Det ferdige kartet har en innebygd funksjon som lar sluttbrukere markere en valgfri adresse på kartet før de printer:

- **Adressefelt** øverst på siden (under print-knappene) med «Marker din adresse»-label og «Vis på kart»-knapp
- **Geocoding** via Nominatim (OpenStreetMap) — kommunenavnet fra `brand.tittel_topp` legges automatisk til søket
- **Stjerne-markør** (★) i accent-farge plasseres på alle kart der adressen er synlig (hovedkart + inset)
- **«Du er her / You are here»**-boks i legend-kolonnen, med adressen — vises bare når en adresse er markert
- **«Fjern»-knapp** fjerner markør og legend-boks
- **Ved print** skjules adresse-verktøylinjen, men markøren og legend-boksen følger med på utskriften

Funksjonen er alltid med i malen og krever ingen konfigurasjon — du trenger IKKE spørre brukeren om noe (f.eks. formål eller målgruppe) for at den skal fungere.

## Referansefiler

Se også:

- `references/brreg-api.md` — detaljer om Brønnøysund-API-et
- `references/checklist.md` — sjekkliste du kan bruke til å holde tritt
- `templates/snefokk-generisk/style.json` — fallback-branding
