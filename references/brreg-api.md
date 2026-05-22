# Brønnøysundregistrene – API-referanse

Skillen bruker det åpne API-et fra Brønnøysundregistrene for å verifisere
at bedrifter fortsatt er aktive. API-et krever ingen autentisering og er
gratis å bruke.

## Endepunkt

```
GET https://data.brreg.no/enhetsregisteret/api/enheter
```

## Nyttige spørringsparametere

| Parameter | Beskrivelse |
|-----------|-------------|
| `navn` | Fritekstsøk på bedriftsnavn (delvis match) |
| `forretningsadresse.kommunenummer` | Filtrer på kommune-nummer (f.eks. 5607 for Vadsø) |
| `organisasjonsnummer` | Direkte oppslag |
| `size` | Maks antall treff (default 20) |

## Viktige felt i responsen

| Felt | Hva det betyr |
|------|---------------|
| `navn` | Offisielt registrert navn |
| `organisasjonsnummer` | 9-sifret org.nr |
| `forretningsadresse` | Registrert besøksadresse |
| `slettedato` | Hvis satt → bedriften er slettet |
| `konkurs` | Hvis `true` → bedriften er konkurs |
| `underAvvikling` | Hvis `true` → under avvikling |
| `underTvangsavviklingEllerTvangsopplosning` | Tvangsoppløsning pågår |
| `organisasjonsform.beskrivelse` | F.eks. "Aksjeselskap", "Forening/lag/innretning" |
| `naeringskode1.beskrivelse` | Hva bedriften driver med |

## Behandling av status

```
slettedato satt       → SLETTET     (fjern fra kartet, men bekreft med bruker)
konkurs = true        → KONKURS     (fjern fra kartet, men bekreft med bruker)
underAvvikling = true → AVVIKLER    (advar bruker, kan velge å beholde)
ellers                → AKTIV       (behold)
```

## Begrensninger

- **Ikke alle aktiviteter er registrert.** Enkeltpersonforetak som
  drives under privatnavn (f.eks. en frilans guide) er ofte ikke i
  registeret. «Ikke funnet» betyr derfor ikke nødvendigvis at bedriften
  ikke finnes — flagg som «trenger manuell sjekk».
- **Søket er løst.** "Hotell" gir treff på alle bedrifter med "hotell"
  i navnet. `brreg_lookup.py` har derfor en streng beste-treff-logikk
  som krever overlapp på diskriminerende ord.
- **Adressen kan være regnskapsadresse.** For konsern kan registrert
  adresse være hovedkontoret, ikke butikken. Bruk alltid Google Maps for
  selve plasseringen på kartet.

## Kommunenummer-tabell

Et utvalg av relevante kommuner ligger hardkodet i `scripts/brreg_lookup.py`.
Hvis kommunen mangler, finn nummeret på
[Wikipedia – Norske kommuner](https://no.wikipedia.org/wiki/Liste_over_norske_kommunenummer)
eller via SSBs kommunekatalog.
