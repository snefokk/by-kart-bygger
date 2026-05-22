#!/usr/bin/env python3
"""Bygg et printbart A4-kart-HTML fra en JSON-konfig og en mal.

Brukseksempel:
    python3 build_html.py \\
        --config arbeid/config.json \\
        --template templates/kart_template.html \\
        --output outputs/vadso-turistkart.html

Konfig-JSON-struktur (forenklet):

{
  "tittel": "Vadsø Turistkart",
  "brand": {
    "tittel_topp": "VADSØ",
    "tittel_bunn": "Turistkart",
    "logo_url": null,
    "font_url": "https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;700&display=swap",
    "font_family": "'Quicksand', system-ui, sans-serif",
    "farger": {
      "primary":   "#2D4F3E",
      "secondary": "#F4F1E8",
      "accent":    "#C9A961",
      "text":      "#1A1A1A"
    }
  },
  "categories": [
    {"id": "eat",      "label_no": "Spisesteder",     "label_en": "Eateries"},
    {"id": "stay",     "label_no": "Overnatting",     "label_en": "Accommodation"},
    {"id": "museum",   "label_no": "Severdigheter",   "label_en": "Sights"},
    {"id": "shop",     "label_no": "Butikker",        "label_en": "Shops"},
    {"id": "beauty",   "label_no": "Salonger & velvære","label_en": "Beauty & wellness"},
    {"id": "activity", "label_no": "Aktiviteter & natur","label_en": "Activities & nature"},
    {"id": "other",    "label_no": "Annet",           "label_en": "Other"}
  ],
  "areas": [
    {
      "title": "Vadsø sentrum",
      "bounds": [[70.0655, 29.7000], [70.0845, 29.7825]],
      "places": [
        {"id": 1, "cat": "eat", "lat": 70.0745, "lng": 29.7522, "name": "Vadsø Hotell Restaurant"}
      ],
      "inset": {
        "bounds": [[70.0718, 29.7475], [70.0756, 29.7572]],
        "force_inset_ids": [80],
        "force_main_ids": [64]
      }
    }
  ],
  "qr_url": "https://vadsoby.com/visit-vadso",
  "qr_label": "Se mer på vadsoby.com"
}
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULTS = {
    "tittel": "Kommunekart",
    "qr_url": None,
    "qr_label": "Mer info",
    "brand": {
        "tittel_topp": "KOMMUNEN",
        "tittel_bunn": "Turistkart",
        "logo_url": None,
        "font_url": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap",
        "font_family": "'Inter', system-ui, sans-serif",
        "farger": {
            "primary":   "#2D4F3E",
            "secondary": "#F4F1E8",
            "accent":    "#C9A961",
            "text":      "#1A1A1A",
        },
    },
}


def _merge(dst: dict, src: dict) -> dict:
    """Dyp merge — verdier fra src overstyrer dst, men strukturen i dst beholdes."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def fyll_inn_mal(template: str, config: dict) -> str:
    """Erstatt placeholderne i malen med verdier fra config."""
    brand = config["brand"]
    f = brand["farger"]
    erstatninger = {
        "__TITLE__": config.get("tittel", "Kommunekart"),
        "__FONT_URL__": brand["font_url"],
        "__FONT_FAMILY__": brand["font_family"],
        "__COLOR_PRIMARY__":   f["primary"],
        "__COLOR_SECONDARY__": f["secondary"],
        "__COLOR_ACCENT__":    f["accent"],
        "__COLOR_TEXT__":      f["text"],
        "__CONFIG_JSON__": json.dumps(config, ensure_ascii=False),
    }
    output = template
    for k, v in erstatninger.items():
        output = output.replace(k, str(v))
    return output


def main() -> int:
    p = argparse.ArgumentParser(description="Bygg printbart kart-HTML fra JSON-konfig.")
    p.add_argument("--config", required=True, help="Sti til config.json")
    p.add_argument("--template", required=True, help="Sti til kart_template.html")
    p.add_argument("--output", required=True, help="Sti hvor HTML-en skal skrives")
    args = p.parse_args()

    config_path = Path(args.config)
    template_path = Path(args.template)
    output_path = Path(args.output)

    if not config_path.exists():
        print(f"Feil: config-fil mangler: {config_path}", file=sys.stderr)
        return 1
    if not template_path.exists():
        print(f"Feil: mal-fil mangler: {template_path}", file=sys.stderr)
        return 1

    user_config = json.loads(config_path.read_text(encoding="utf-8"))
    config = _merge(json.loads(json.dumps(DEFAULTS)), user_config)

    template = template_path.read_text(encoding="utf-8")
    output = fyll_inn_mal(template, config)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    print(f"Skrev {output_path} ({len(output)} tegn)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
