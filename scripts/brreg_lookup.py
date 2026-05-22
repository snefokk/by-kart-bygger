#!/usr/bin/env python3
"""Slå opp et bedriftsnavn i Brønnøysundregistrene.

Returnerer JSON med status (aktiv/slettet/konkurs/ikke funnet),
offisielt navn, og registrert adresse.

Brukseksempel:
    python3 brreg_lookup.py "Vadsø Hotell" --kommune Vadsø
    python3 brreg_lookup.py "Horisontti" --kommunenummer 5607

Krever bare standardbiblioteket (urllib + json).
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

API_BASE = "https://data.brreg.no/enhetsregisteret/api/enheter"

# Kommunenummer-oppslag for de vanligste kommunene.
# Hvis kommunen mangler her, kan brukeren oppgi --kommunenummer direkte.
KOMMUNE_NR = {
    "vadsø": "5607",
    "vardø": "5634",
    "sør-varanger": "5605",
    "tana": "5621",
    "nesseby": "5630",
    "berlevåg": "5610",
    "båtsfjord": "5612",
    "lebesby": "5618",
    "gamvik": "5624",
    "porsanger": "5620",
    "karasjok": "5622",
    "kautokeino": "5628",
    "alta": "5601",
    "loppa": "5614",
    "hasvik": "5616",
    "måsøy": "5634",
    "nordkapp": "5636",
    "hammerfest": "5603",
    "tromsø": "5401",
    "bodø": "1804",
    "trondheim": "5001",
    "bergen": "4601",
    "stavanger": "1103",
    "oslo": "0301",
}


def søk(navn, kommunenummer=None, kommunenavn=None, size=5):
    """Søk i BRREG på navn. Returnerer rå JSON-respons.

    Støtter filtrering på enten kommunenummer eller kommunenavn.
    Kommunenavn sendes direkte til API-et (f.eks. 'VARDØ', 'VADSØ')
    og krever ingen lokal tabell — API-et matcher uavhengig av store/små bokstaver.
    """
    params = {"navn": navn, "size": str(size)}
    if kommunenummer:
        params["forretningsadresse.kommunenummer"] = kommunenummer
    elif kommunenavn:
        params["forretningsadresse.kommune"] = kommunenavn.upper()
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


STOPP_ORD = {
    # Selskapsformer / generiske
    "as", "asa", "ans", "da", "kommune", "norge", "bedrift", "firma",
    "the", "og", "and", "av", "i", "for", "på", "ved", "med", "&",
    # Bransjeord — alene gir disse for løs match
    "bakeri", "konditori", "kafe", "café", "cafe", "kafeen",
    "restaurant", "restauranten", "spiseri",
    "hotel", "hotell", "hotellet", "gjestgiveri", "pensjonat", "camping",
    "butikk", "butikken", "shop", "store",
    "pub", "bar", "kro",
    "kiosk", "gatekjøkken",
    "salong", "frisør", "frisørsalong",
    "verksted", "bilverksted",
    "klinikk", "tannlege", "lege",
    "museum", "kirke", "kapell",
    "sauna", "spa", "treningssenter",
}


def _ord(navn: str) -> set[str]:
    """Returner et sett av ord (>2 bokstaver, uten stoppord) for sammenligning."""
    rens = "".join(c if c.isalnum() or c.isspace() else " " for c in navn.lower())
    return {w for w in rens.split() if len(w) > 2 and w not in STOPP_ORD}


def beste_treff(data, søkenavn, kommune=None):
    """Velg det mest sannsynlige treffet basert på navnelikhet.

    BRREG-søket er ganske vidåpent og returnerer ofte irrelevante treff
    (f.eks. matcher det "Vadsø Hotell" mot enhver bedrift med "Vadsø" i navnet).
    Vi krever derfor at minst ett INNHOLDS-ord — utover kommunenavnet — fra
    søkenavnet finnes i offisielt navn. Ellers behandler vi det som ikke funnet.
    """
    enheter = data.get("_embedded", {}).get("enheter", [])
    if not enheter:
        return None
    sn = søkenavn.lower().strip()
    søk_ord = _ord(søkenavn)
    # Fjern kommunenavnet fra "diskriminerende" ord — det er for vanlig
    diskriminerende = søk_ord - {kommune.lower()} if kommune else søk_ord

    # 1. Eksakt match på navn
    for e in enheter:
        if e.get("navn", "").lower() == sn:
            return e

    # 2. Søkenavn som substring av offisielt navn
    for e in enheter:
        if sn in e.get("navn", "").lower():
            return e

    # 3. Velg treffet som overlapper med diskriminerende ord
    scored = []
    for e in enheter:
        treff_ord = _ord(e.get("navn", ""))
        overlap = len(diskriminerende & treff_ord)
        if overlap > 0:
            scored.append((overlap, e))
    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    # Ingen meningsfull overlapp → behandle som ikke funnet
    return None


def klassifiser_status(enhet: dict) -> str:
    """Returner én av: 'aktiv', 'konkurs', 'under_avvikling', 'slettet'."""
    if enhet.get("slettedato"):
        return "slettet"
    if enhet.get("konkurs"):
        return "konkurs"
    if enhet.get("underAvvikling") or enhet.get("underTvangsavviklingEllerTvangsopplosning"):
        return "under_avvikling"
    return "aktiv"


def format_resultat(enhet, søkenavn):
    """Bygg den endelige status-dicten som returneres til brukeren."""
    if not enhet:
        return {
            "søkenavn": søkenavn,
            "funnet": False,
            "aktiv": None,
            "status": "ikke_funnet",
            "merknad": (
                "Ikke funnet i Brønnøysundregisteret. Kan være enkeltpersonforetak "
                "registrert på privat navn, eller en aktivitet som ikke krever "
                "næringsregistrering. Trenger manuell sjekk."
            ),
        }
    status = klassifiser_status(enhet)
    adresse = enhet.get("forretningsadresse") or {}
    return {
        "søkenavn": søkenavn,
        "funnet": True,
        "aktiv": status == "aktiv",
        "status": status,
        "organisasjonsnummer": enhet.get("organisasjonsnummer"),
        "navn_offisielt": enhet.get("navn"),
        "organisasjonsform": (enhet.get("organisasjonsform") or {}).get("beskrivelse"),
        "naeringskode": (enhet.get("naeringskode1") or {}).get("beskrivelse"),
        "adresse": " ".join(adresse.get("adresse", [])).strip() or None,
        "postnummer": adresse.get("postnummer"),
        "poststed": adresse.get("poststed"),
        "kommune": adresse.get("kommune"),
        "kommunenummer": adresse.get("kommunenummer"),
        "slettedato": enhet.get("slettedato"),
        "stiftelsesdato": enhet.get("stiftelsesdato"),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Slå opp bedrift i Brønnøysund.")
    p.add_argument("navn", help="Bedriftsnavn å søke etter")
    p.add_argument("--kommune", help="Kommunenavn (sendes direkte til BRREG API)")
    p.add_argument("--kommunenummer", help="Kommunenummer direkte (overstyrer --kommune)")
    p.add_argument("--raw", action="store_true", help="Skriv ut hele BRREG-responsen i stedet for sammendrag")
    args = p.parse_args()

    knr = args.kommunenummer
    kommunenavn = None

    if knr:
        # Eksplisitt kommunenummer har høyest prioritet
        pass
    elif args.kommune:
        # Prøv først å bruke kommunenavnet direkte mot API-et
        # (ingen lokal tabell nødvendig — API-et matcher selv)
        kommunenavn = args.kommune
        # Fallback: sjekk lokal tabell for kommunenummer (legacy)
        knr_fra_tabell = KOMMUNE_NR.get(args.kommune.lower())
        if knr_fra_tabell:
            # Bruk kommunenavn-søk som primær, men logg at tabellen finnes
            pass

    try:
        data = søk(args.navn, kommunenummer=knr, kommunenavn=kommunenavn)
    except Exception as exc:
        print(json.dumps({"feil": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if args.raw:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    treff = beste_treff(data, args.navn, kommune=args.kommune)
    resultat = format_resultat(treff, args.navn)
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
