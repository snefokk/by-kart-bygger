# by-kart-bygger

Lag et printbart **A4-turistkart** for et norsk tettsted — bygget med AI, klart til print, med interaktiv web-versjon. En åpen skill for Claude (Cowork / Claude Code).

> **Vil du heller at vi lager kartet for deg?**
> Bestill et ferdig kart på **[snefokk.com/kart](https://snefokk.com/kart)** — så bygger Snefokk det, tilpasser profilen og leverer PDF + web-versjon. Dette repoet er for deg som vil gjøre jobben selv, gratis.

## Hva skillen lager

- **PDF klar til A4-print** — profesjonelt designet, print på en helt vanlig kontorprinter (farger eller sort-hvitt)
- **Steder du selv velger** — severdigheter, spisesteder, overnatting, butikker, museer, parkering, transport — plassert med tydelige markører
- **Egen adresse markert** — marker AirBnb-leiligheten, hotellet eller bedriftens adresse spesielt
- **Tilpasset profil** — farger, logo og typografi tilpasses tettstedet eller bedriften
- **Interaktiv web-versjon** — der besøkende kan søke etter adresser og trykke på markører for mer info

Bedriftene verifiseres som aktive i Brønnøysundregistrene, og koordinater slås opp automatisk under byggingen.

## Hvem det er for

- Kommuner og tettsteder som vil ha lavterskel turistinformasjon
- AirBnb-verter, B&B-er og små hoteller som vil gi gjestene et kart over området
- Vell- og bygdeforeninger, reiselivsorganisasjoner og besøkssentre
- Lokale butikker, kafeer og museer — og næringshager som representerer flere bedrifter

## To måter å få kartet

| Gjør det selv (dette repoet) | La Snefokk gjøre jobben |
| --- | --- |
| Gratis — krever et Claude-abonnement | Bestill på **[snefokk.com/kart](https://snefokk.com/kart)** |
| Du kjører skillen selv i Claude Cowork — bygg og oppdater så ofte du vil | Snefokk bygger, tilpasser profilen og leverer, med én tilbakemeldingsrunde |
| **Ferdig på ~20 minutter** (med god internettforbindelse) | **Klart innen typisk en uke** |

## Hva du trenger (for å gjøre det selv)

- Et aktivt **Claude Pro**-abonnement (eller høyere) — skillen kjører i Claude Cowork / Claude Code
- **Google Chrome** med «Claude in Chrome»-utvidelsen, for koordinatoppslag i Google Maps *(anbefalt — uten Chrome finnes en enklere, litt mindre presis OSM-fallback)*
- **Internett-tilgang**
- **Python 3** — for å bygge selve HTML-en (standardbibliotek, ingen `pip install`; finnes på de fleste maskiner)

Skillen i seg selv er gratis og åpen kildekode.

## Kom i gang (gjør det selv)

1. **Last ned skillen** — klon eller last ned dette repoet.
2. **Installer i Claude Cowork** — pek Cowork mot skill-mappa.
3. **Følg `SKILL.md`** — den tar deg steg for steg gjennom steder, kartavgrensning og selve byggingen.

## Bygg fra en konfig-fil (avansert)

Skillen produserer en `config.json` og bygger HTML-en med et lite Python-skript (kun standardbibliotek — ingen `pip install`):

```bash
python3 scripts/build_html.py \
  --config outputs/kart-arbeid/config.json \
  --template templates/kart_template.html \
  --output outputs/<kommune>-turistkart.html
```

Slå opp en bedrift i Brønnøysundregistrene:

```bash
python3 scripts/brreg_lookup.py "Bedriftsnavn" --kommune Vadsø
```

## Eksempler

Kart bygget med skillen — se alle på **[snefokk.com/kart](https://snefokk.com/kart/#eksempler)**:

- [Vadsø](https://vadsoby.com/visit-vadso/turistkart/)
- [Båtsfjord](https://snefokk.com/kart/batsfjord/)
- [Vardø](https://snefokk.com/kart/vardo/)
- [Berlevåg](https://snefokk.com/kart/berlevag/)

## Lisens

Se [LICENSE](LICENSE). Åpen kildekode — bruk, modifiser og del fritt.
