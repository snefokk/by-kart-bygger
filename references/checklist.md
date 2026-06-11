# Sjekkliste for by-kart-bygger

Bruk denne listen for å holde tritt mens du går gjennom flyten.

## Start

- [ ] Bekreftet kommune-navn og -nummer
- [ ] Mottatt gammelt kart (PDF/bilde) eller bekreftet at vi starter blankt
- [ ] Identifisert alle synlige POIs fra gammelt kart
- [ ] Lagt til flyplass, togstasjon og havn/hurtigrutekai hvis kommunen har dem
- [ ] Lagret utkast i `outputs/kart-arbeid/punkter-utkast.json`

## Verifisering

- [ ] Kjørt `brreg_lookup.py` på alle bedriftspunkter
- [ ] Flagget døde/konkursbedrifter for fjerning
- [ ] Bekreftet med brukeren hvilke som skal fjernes
- [ ] Slått opp koordinater i Google Maps for alle gjenværende punkter
- [ ] **Visuelt verifisert HVERT punkt** i Google Maps:
  - [ ] Pinnen ligger på land (ikke i sjøen)
  - [ ] Pinnen treffer riktig bygning/sted (ikke parkeringen, nabotomten, eller feil side av veien)
  - [ ] Gateadressen fra Google stemmer med forventet adresse
- [ ] Korrigert alle feilplasserte koordinater og logget endringene
- [ ] Dobbeltsjekket punkter med avrundede koordinater (f.eks. 70.365, 31.091 — disse er ofte feil)
- [ ] Kjørt duplikat-koordinat-sjekk (gruppér etter lat/lng, rapporter grupper med 2+)
- [ ] For hver duplikat-gruppe: verifisert om de faktisk er i samme bygg, eller om koordinater er feilkopiert
- [ ] Informert brukeren om duplikat-resultatet (spurt bare ved tvil)

## Tillegg

- [ ] Spurt brukeren om punkter som mangler
- [ ] Verifisert hvert tilleggspunkt (BRREG + Google Maps)

## Layout

- [ ] Geografisk clustering ferdig — bestemt antall sider
- [ ] Hver side har en områdetittel
- [ ] For tette sentrum: bestemt om inset-kart trengs
- [ ] For små tettsteder (< ~1 km): satt `single_map: true` med auto-rotasjon
- [ ] Sjekket at auto-rotasjon gir fornuftig resultat (evt. satt `rotation` manuelt)
- [ ] POIs utenfor synsfeltet håndteres automatisk som pilmarkører

## Branding

- [ ] Spurt brukeren om kilde (nettside vs standard)
- [ ] Hentet farger / font / logo
- [ ] Lagret i `outputs/kart-arbeid/brand.json`

## Bygging

- [ ] Bygget HTML med `build_html.py`
- [ ] Åpnet HTML i nettleser og bekreftet at alle markører er synlige
- [ ] Sjekket debug-overlayet: zoom 16, bearing, antall synlige/utenfor
- [ ] Sjekket at pilmarkører peker riktig retning og ikke overlapper
- [ ] Sjekket at gatenavn er skarpe (retina-tiles)
- [ ] Sjekket at kategori-listene i sidekolonnen ikke overlapper med kartet
- [ ] Konsollen viser `[qr-sjekk] OK` (QR-koden er dekodbar)
- [ ] Print-preview: bekreftet at side-skift fungerer

## Levering

- [ ] Kopiert ferdig HTML til kommunens workspace-mappe
- [ ] Gitt brukeren en klikkbar lenke til filen
- [ ] Forklart hvordan de printer (Save as PDF for ekstra kvalitet)
