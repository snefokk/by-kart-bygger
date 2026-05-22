#!/usr/bin/env python3
"""
osm_to_svg.py — Last ned OSM-data og generer et stilisert SVG-kart.

Bruk:
  python3 osm_to_svg.py --bounds "70.368,31.086,70.382,31.128" \
                         --output kart.svg \
                         --width 800 --padding 20

Pipeline:
  1. Overpass API → veier, bygninger, vann, landuse, steder
  2. Mercator-projeksjon → SVG-koordinater
  3. SVG med CSS-klasser for Budapest-stil farger
"""

import argparse
import json
import math
import sys
import urllib.request
import urllib.parse

# ============================================================
#  OVERPASS QUERY
# ============================================================

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def build_query(south, west, north, east):
    """Bygg Overpass QL-query for et gitt bounds."""
    bbox = f"{south},{west},{north},{east}"
    return f"""
[out:json][timeout:60];
(
  // Veier
  way["highway"]["highway"!~"proposed|construction|raceway"]["area"!="yes"]({bbox});
  // Bygninger
  way["building"]({bbox});
  // Vann (lukkede arealer)
  way["natural"="water"]({bbox});
  relation["natural"="water"]({bbox});
  way["natural"="coastline"]({bbox});
  // Landuse
  way["landuse"~"grass|meadow|forest|cemetery|recreation_ground|village_green"]({bbox});
  way["leisure"~"park|garden|pitch"]({bbox});
  way["natural"~"wood|scrub|heath"]({bbox});
  // Havneområder
  way["natural"="bay"]({bbox});
  way["waterway"]({bbox});
  // Stedsnavn
  node["place"~"city|town|village|hamlet|suburb|neighbourhood"]({bbox});
);
out body;
>;
out skel qt;
"""

def fetch_osm(south, west, north, east):
    """Hent OSM-data fra Overpass API med lokal caching."""
    import hashlib, os
    cache_key = hashlib.md5(f"{south},{west},{north},{east}".encode()).hexdigest()
    cache_file = f"/tmp/osm_cache_{cache_key}.json"

    # Sjekk cache
    if os.path.exists(cache_file):
        print(f"Bruker cached OSM-data fra {cache_file}", file=sys.stderr)
        with open(cache_file, "r") as f:
            elements = json.load(f)
        print(f"  {len(elements)} elementer fra cache", file=sys.stderr)
        return elements

    query = build_query(south, west, north, east)
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    print(f"Henter OSM-data for bounds ({south},{west})→({north},{east})...", file=sys.stderr)
    req = urllib.request.Request(OVERPASS_URL, data=data,
                                headers={"User-Agent": "kommunekart-svg/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    elements = result.get("elements", [])
    print(f"  Mottok {len(elements)} elementer", file=sys.stderr)

    # Lagre til cache
    with open(cache_file, "w") as f:
        json.dump(elements, f)
    print(f"  Cached til {cache_file}", file=sys.stderr)

    return elements


# ============================================================
#  MERCATOR PROJEKSJON
# ============================================================

def lat_to_y(lat):
    """Konverter latitude til Mercator y-verdi."""
    lat_rad = math.radians(lat)
    return math.log(math.tan(math.pi / 4 + lat_rad / 2))

def project(lat, lng, bounds, width, height, padding):
    """Projiser lat/lng til SVG pikselkoordinater."""
    south, west, north, east = bounds
    # Mercator-projeksjon
    x_frac = (lng - west) / (east - west)
    y_top = lat_to_y(north)
    y_bot = lat_to_y(south)
    y_frac = (y_top - lat_to_y(lat)) / (y_top - y_bot)
    x = padding + x_frac * width
    y = padding + y_frac * height
    return x, y


# ============================================================
#  PARSE OSM-ELEMENTER
# ============================================================

def parse_elements(elements, bounds, width, height, padding):
    """Parse OSM-elementer til kategoriserte SVG-data."""
    nodes = {}
    ways = []
    places = []

    # Først: indekser alle noder
    for el in elements:
        if el["type"] == "node":
            nodes[el["id"]] = el

    # Deretter: prosesser ways
    for el in elements:
        if el["type"] == "way":
            tags = el.get("tags", {})
            node_ids = el.get("nodes", [])

            # Bygg punktliste
            points = []
            for nid in node_ids:
                if nid in nodes:
                    n = nodes[nid]
                    x, y = project(n["lat"], n["lon"], bounds, width, height, padding)
                    points.append((x, y))

            if not points:
                continue

            # Klassifiser
            css_class = classify_way(tags)
            is_area = node_ids[0] == node_ids[-1] if len(node_ids) > 2 else False

            way_data = {
                "points": points,
                "class": css_class,
                "is_area": is_area,
                "tags": tags,
            }

            # Samle gatenavn for veier
            road_name = tags.get("name", "")
            if road_name and css_class.startswith("road"):
                way_data["road_name"] = road_name

            ways.append(way_data)

        elif el["type"] == "node" and "tags" in el:
            tags = el.get("tags", {})
            if tags.get("place"):
                x, y = project(el["lat"], el["lon"], bounds, width, height, padding)
                places.append({
                    "x": x, "y": y,
                    "name": tags.get("name", ""),
                    "class": "place-" + tags.get("place", "other"),
                })

    return ways, places


def classify_way(tags):
    """Klassifiser en way basert på tags."""
    hw = tags.get("highway", "")
    if hw in ("motorway", "trunk", "primary", "secondary"):
        return "road-major"
    if hw in ("tertiary", "unclassified", "residential"):
        return "road-minor"
    if hw in ("service", "living_street", "pedestrian"):
        return "road-service"
    if hw in ("footway", "path", "cycleway", "steps", "track"):
        return "road-path"
    if hw:
        return "road-minor"

    if tags.get("building"):
        return "building"
    if tags.get("natural") == "water" or tags.get("natural") == "bay":
        return "water"
    if tags.get("natural") == "coastline":
        return "coastline"
    if tags.get("waterway"):
        return "waterway"
    if tags.get("landuse") in ("grass", "meadow", "cemetery", "recreation_ground", "village_green"):
        return "green"
    if tags.get("landuse") in ("forest",) or tags.get("natural") in ("wood", "scrub", "heath"):
        return "forest"
    if tags.get("leisure") in ("park", "garden", "pitch"):
        return "green"

    return "other"


# ============================================================
#  GENERER SVG
# ============================================================

# ============================================================
#  FARGEPALETTER
# ============================================================

PALETTES = {
    "snefokk": {
        "name": "Snefokk",
        "description": "Standard Snefokk — warm cream, sage water, brown roads. The default.",
        "land":         "#EDE4D8",
        "water":        "#a9c0af",
        "water_stroke": "#95b09e",
        "green":        "#c5ceaf",
        "forest":       "#b5c4a8",
        "building":     "#E0D5C7",
        "bldg_outline": "#D0C3B2",
        "road_major":   "#8B7055",
        "road_minor":   "#C4B49E",
        "road_service": "#D4C4AE",
        "road_path":    "#D4C4AE",
        "other_stroke": "#D0C3B2",
        "text_main":    "#5C4E3C",
        "text_minor":   "#8A7C6A",
        "text_water":   "#7A8A6A",
        "label_major":  "#6B5D4E",
        "label_minor":  "#8A7C6A",
    },
    "amsterdam": {
        "name": "Amsterdam",
        "description": "Icy mint monochrome — clean, minimal, light sage-green tones.",
        "land":         "#EDF2EE",
        "water":        "#C0D0D0",
        "water_stroke": "#A8BEC0",
        "green":        "#B0C8B5",
        "forest":       "#9ABB9E",
        "building":     "#D8E2DA",
        "bldg_outline": "#C5D0C8",
        "road_major":   "#3E5E52",
        "road_minor":   "#8AA598",
        "road_service": "#A8BCAE",
        "road_path":    "#A8BCAE",
        "other_stroke": "#C5D0C8",
        "text_main":    "#2A4A40",
        "text_minor":   "#5A7A6E",
        "text_water":   "#4A6E70",
        "label_major":  "#3A5A4E",
        "label_minor":  "#5A7A6E",
    },
    "berlin": {
        "name": "Berlin",
        "description": "Warm sand — beige monochrome, white water, charcoal roads. Elegant neutral.",
        "land":         "#DDD5CA",
        "water":        "#F0EBE4",
        "water_stroke": "#E0D8CE",
        "green":        "#C8C2B0",
        "forest":       "#BAB4A2",
        "building":     "#D0C8BC",
        "bldg_outline": "#C0B8AA",
        "road_major":   "#4A4540",
        "road_minor":   "#908880",
        "road_service": "#A8A098",
        "road_path":    "#A8A098",
        "other_stroke": "#C0B8AA",
        "text_main":    "#3A3530",
        "text_minor":   "#6A645E",
        "text_water":   "#8A8478",
        "label_major":  "#4A4540",
        "label_minor":  "#6A645E",
    },
    "klassisk": {
        "name": "Klassisk",
        "description": "Google Maps-inspired — light gray, blue water, green parks, gray roads.",
        "land":         "#F0F0F0",
        "water":        "#AADAFF",
        "water_stroke": "#88C4EE",
        "green":        "#C8E6C0",
        "forest":       "#A8D8A0",
        "building":     "#E0E0E0",
        "bldg_outline": "#C8C8C8",
        "road_major":   "#FFFFFF",
        "road_minor":   "#FFFFFF",
        "road_service": "#F8F8F8",
        "road_path":    "#E0E0E0",
        "other_stroke": "#D0D0D0",
        "text_main":    "#333333",
        "text_minor":   "#666666",
        "text_water":   "#4A80B0",
        "label_major":  "#444444",
        "label_minor":  "#777777",
    },
}

DEFAULT_PALETTE = "snefokk"


def build_css(palette_name=None, road_scale=1.0):
    """Generer SVG CSS fra en navngitt palett.

    road_scale: Skaleringsfaktor for veibredder og gatenavn-størrelse.
                1.0 = standard (for overview), 2.0 = dobbel (for inset zoom 16).
    """
    name = palette_name or DEFAULT_PALETTE
    p = PALETTES.get(name, PALETTES[DEFAULT_PALETTE])
    cls = f"kart-{name}"
    rs = road_scale  # kortform
    return f"""
  .{cls} {{
    font-family: 'Newsreader', 'Noto Serif', Georgia, serif;
  }}
  .{cls} .water    {{ fill: {p['water']}; stroke: none; }}
  .{cls} .waterway {{ fill: none; stroke: {p['water_stroke']}; stroke-width: {1.5 * rs:.1f}; stroke-linecap: round; }}
  .{cls} .coastline {{ fill: none; stroke: {p['water_stroke']}; stroke-width: {1 * rs:.0f}; }}
  .{cls} .green    {{ fill: {p['green']}; stroke: none; opacity: 0.7; }}
  .{cls} .forest   {{ fill: {p['forest']}; stroke: none; opacity: 0.5; }}
  .{cls} .building {{ fill: {p['building']}; stroke: {p['bldg_outline']}; stroke-width: {0.3 * rs:.1f}; }}
  .{cls} .road-major   {{ fill: none; stroke: {p['road_major']}; stroke-width: {2.5 * rs:.1f}; stroke-linecap: round; stroke-linejoin: round; }}
  .{cls} .road-minor   {{ fill: none; stroke: {p['road_minor']}; stroke-width: {1.5 * rs:.1f}; stroke-linecap: round; stroke-linejoin: round; }}
  .{cls} .road-service {{ fill: none; stroke: {p['road_service']}; stroke-width: {1.0 * rs:.1f}; stroke-linecap: round; stroke-linejoin: round; }}
  .{cls} .road-path    {{ fill: none; stroke: {p['road_path']}; stroke-width: {0.5 * rs:.1f}; stroke-dasharray: {2 * rs:.0f},{2 * rs:.0f}; stroke-linecap: round; }}
  .{cls} .other    {{ fill: none; stroke: {p['other_stroke']}; stroke-width: {0.3 * rs:.1f}; }}
  .{cls} .place-city text,
  .{cls} .place-town text {{ font-size: {14 * rs:.1f}px; font-weight: 700; fill: {p['text_main']}; }}
  .{cls} .place-village text,
  .{cls} .place-hamlet text {{ font-size: {10 * rs:.1f}px; font-weight: 400; fill: {p['text_main']}; }}
  .{cls} .place-suburb text,
  .{cls} .place-neighbourhood text {{ font-size: {8 * rs:.1f}px; font-weight: 400; fill: {p['text_minor']}; text-transform: uppercase; letter-spacing: 1px; }}
  .{cls} .road-label {{ font-size: {6 * rs:.1f}px; font-family: 'Inter', 'Helvetica Neue', sans-serif; font-weight: 400; fill: {p['label_minor']}; letter-spacing: 0.5px; }}
  .{cls} .road-label-major {{ font-size: {7.5 * rs:.1f}px; font-family: 'Inter', 'Helvetica Neue', sans-serif; font-weight: 500; fill: {p['label_major']}; letter-spacing: 0.3px; }}
"""

def points_to_path(points):
    """Konverter punktliste til SVG path d-attributt."""
    parts = []
    for i, (x, y) in enumerate(points):
        cmd = "M" if i == 0 else "L"
        parts.append(f"{cmd}{x:.1f},{y:.1f}")
    return " ".join(parts)


def point_in_polygon(x, y, polygon):
    """Ray-casting test: er (x,y) innenfor polygon?"""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def stitch_coastlines(coastlines):
    """
    Sy sammen kystlinje-segmenter til lukkede ringer.
    OSM kystlinjer har konvensjon: land til venstre, hav til høyre.
    Segmenter som deler endepunkter sys sammen.
    """
    if not coastlines:
        return []

    # Hvert segment er en liste med punkter
    segments = [list(c["points"]) for c in coastlines]
    rings = []

    # Prøv å sy segmenter sammen basert på nære endepunkter
    TOLERANCE = 5.0  # piksler

    def points_close(p1, p2):
        return abs(p1[0] - p2[0]) < TOLERANCE and abs(p1[1] - p2[1]) < TOLERANCE

    used = [False] * len(segments)

    while True:
        # Finn et ubrukt segment å starte med
        start_idx = None
        for i, u in enumerate(used):
            if not u and len(segments[i]) >= 2:
                start_idx = i
                break
        if start_idx is None:
            break

        # Bygg en kjede fra dette segmentet
        chain = list(segments[start_idx])
        used[start_idx] = True

        # Prøv å forlenge kjeden
        changed = True
        while changed:
            changed = False
            for i, seg in enumerate(segments):
                if used[i] or len(seg) < 2:
                    continue
                # Sjekk om seg-start kobler til chain-slutt
                if points_close(chain[-1], seg[0]):
                    chain.extend(seg[1:])
                    used[i] = True
                    changed = True
                # Sjekk om seg-slutt kobler til chain-start
                elif points_close(seg[-1], chain[0]):
                    chain = seg[:-1] + chain
                    used[i] = True
                    changed = True
                # Sjekk reversert segment
                elif points_close(chain[-1], seg[-1]):
                    chain.extend(reversed(seg[:-1]))
                    used[i] = True
                    changed = True
                elif points_close(seg[0], chain[0]):
                    chain = list(reversed(seg[1:])) + chain
                    used[i] = True
                    changed = True

        if len(chain) >= 3:
            rings.append(chain)

    return rings


def build_land_mask(ways, width, height, padding):
    """
    Bygg landmasker fra kystlinjer.
    Strategi: havet er bakgrunn (salvie-grønn), land tegnes oppå som krem.
    Returnerer en liste med SVG path d-attributter, en per landmasse.

    For kystlinjer som forlater bounds: lukk polygon langs kanten av SVG.
    """
    coastlines = [w for w in ways if w["class"] == "coastline"]
    if not coastlines:
        return []

    total_w = width + 2 * padding
    total_h = height + 2 * padding

    rings = stitch_coastlines(coastlines)
    if not rings:
        return []

    print(f"  Kystlinje: {len(coastlines)} segmenter → {len(rings)} ringer", file=sys.stderr)

    paths = []
    for ring in rings:
        # Sjekk om ringen er lukket (start ≈ slutt)
        is_closed = (abs(ring[0][0] - ring[-1][0]) < 5 and
                     abs(ring[0][1] - ring[-1][1]) < 5)

        if not is_closed:
            # Kystlinje som forlater bounds — lukk langs kantene
            # Legg til hjørner av SVG for å lukke polygonen
            # Finn nærmeste kant for start- og sluttpunkt
            ring = close_ring_along_edges(ring, total_w, total_h)

        d = points_to_path(ring) + " Z"
        paths.append(d)

    return paths


def close_ring_along_edges(ring, total_w, total_h):
    """
    Lukk en åpen kystlinje-ring ved å følge SVG-kantene.
    Start- og sluttpunkt kobles via nærmeste kanter med klokken.
    """
    def nearest_edge_point(x, y):
        """Finn nærmeste punkt på SVG-kanten."""
        candidates = [
            (x, 0, abs(y)),                    # topp
            (x, total_h, abs(y - total_h)),    # bunn
            (0, y, abs(x)),                    # venstre
            (total_w, y, abs(x - total_w)),    # høyre
        ]
        candidates.sort(key=lambda c: c[2])
        return (candidates[0][0], candidates[0][1])

    def edge_id(x, y):
        """Hvilken kant er punktet på? 0=topp, 1=høyre, 2=bunn, 3=venstre"""
        dists = [abs(y), abs(x - total_w), abs(y - total_h), abs(x)]
        return dists.index(min(dists))

    # Projiser start/slutt til kanten
    end_pt = ring[-1]
    start_pt = ring[0]
    end_edge = nearest_edge_point(end_pt[0], end_pt[1])
    start_edge = nearest_edge_point(start_pt[0], start_pt[1])

    # Følg kantene med klokken fra end_edge til start_edge
    corners = [
        (total_w, 0),       # øvre høyre
        (total_w, total_h), # nedre høyre
        (0, total_h),       # nedre venstre
        (0, 0),             # øvre venstre
    ]

    end_eid = edge_id(end_edge[0], end_edge[1])
    start_eid = edge_id(start_edge[0], start_edge[1])

    result = list(ring)
    result.append(end_edge)

    # Prøv begge retninger (med og mot klokken) og velg den korteste
    # for å sikre at vi omslutter land, ikke hav
    for direction in [1, -1]:  # 1 = med klokken, -1 = mot klokken
        path = [end_edge]
        eid = end_eid
        safety = 0
        while safety < 8:
            if eid == start_eid:
                break
            next_idx = eid if direction == 1 else (eid - 1) % 4
            path.append(corners[next_idx])
            eid = (eid + direction) % 4
            safety += 1
        path.append(start_edge)

        if direction == 1:
            cw_path = path
        else:
            ccw_path = path

    # Velg korteste vei (land er vanligvis den kortere omveien)
    if len(cw_path) <= len(ccw_path):
        result.extend(cw_path[1:])  # Skip end_edge (allerede lagt til)
    else:
        result.extend(ccw_path[1:])

    return result


def generate_svg(ways, places, width, height, padding, palette_name=None, skip_label_filter=False, road_scale=1.0):
    """Generer SVG-streng med valgt fargepalett."""
    p = PALETTES.get(palette_name or DEFAULT_PALETTE, PALETTES[DEFAULT_PALETTE])
    css = build_css(palette_name, road_scale=road_scale)

    total_w = width + 2 * padding
    total_h = height + 2 * padding

    # Sorter layers: arealer først, deretter veier, deretter tekst
    area_order = ["water", "coastline", "forest", "green", "building"]
    line_order = ["waterway", "road-path", "road-service", "road-minor", "road-major", "other"]

    areas = [w for w in ways if w["is_area"] and w["class"] in area_order]
    lines = [w for w in ways if not w["is_area"] or w["class"] in line_order]

    # Sorter arealer etter prioritet
    areas.sort(key=lambda w: area_order.index(w["class"]) if w["class"] in area_order else 99)
    lines.sort(key=lambda w: line_order.index(w["class"]) if w["class"] in line_order else 99)

    # Bygg landmaske fra kystlinjer
    land_mask = build_land_mask(ways, width, height, padding)

    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.0f} {total_h:.0f}" width="{total_w:.0f}" height="{total_h:.0f}">')
    svg_parts.append(f'<style>{css}</style>')
    palette_cls = f"kart-{palette_name or DEFAULT_PALETTE}"
    svg_parts.append(f'<g class="{palette_cls}">')

    # Bakgrunn: hav — alt som ikke er kystlinje er hav
    svg_parts.append(f'<rect width="100%" height="100%" fill="{p["water"]}"/>')

    # Landmasse oppå havet — kystlinjepolygoner fyller land
    if land_mask:
        svg_parts.append(f'<!-- Landmasse fra kystlinje -->')
        for i, mask_d in enumerate(land_mask):
            svg_parts.append(f'<path d="{mask_d}" fill="{p["land"]}" stroke="none"/>')
    else:
        # Ingen kystlinje funnet — alt er land (innlandskart)
        svg_parts.append(f'<rect width="100%" height="100%" fill="{p["land"]}"/>')

    # Arealer (vann, grønt, bygninger)
    svg_parts.append('<!-- Arealer -->')
    for w in areas:
        d = points_to_path(w["points"])
        if w["is_area"]:
            d += " Z"
        svg_parts.append(f'<path class="{w["class"]}" d="{d}"/>')

    # Linjer (veier, stier)
    svg_parts.append('<!-- Veier -->')
    road_label_paths = []
    road_label_id = 0
    seen_road_names = {}  # Dedupliser gatenavn
    for w in lines:
        if w["class"].startswith("road") or w["class"] == "waterway":
            d = points_to_path(w["points"])
            road_name = w.get("road_name", "")

            # Lagre path med id for textPath-label
            if road_name and w["class"] in ("road-major", "road-minor"):
                # Beregn veilengde for å filtrere korte segmenter
                pts = w["points"]
                seg_len = sum(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])
                              for i in range(len(pts)-1))

                # Dedupliser: behold lengste segment per gatenavn
                if road_name not in seen_road_names or seg_len > seen_road_names[road_name][1]:
                    path_id = f"road-{road_label_id}"
                    road_label_id += 1
                    seen_road_names[road_name] = (path_id, seg_len, d, w["class"], pts)

            svg_parts.append(f'<path class="{w["class"]}" d="{d}"/>')

    # Parse land_mask polygoner for punkt-i-polygon-test
    land_polygons = []
    for mask_d in land_mask:
        # Parse path d-attributt til punktliste
        coords = []
        for token in mask_d.replace('M', ' ').replace('L', ' ').replace('Z', '').split():
            if ',' in token:
                parts = token.split(',')
                try:
                    coords.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    pass
        if coords:
            land_polygons.append(coords)

    def is_on_land(x, y):
        """Sjekk om punkt er innenfor noen av landmaskene."""
        if not land_polygons:
            return True  # Ingen kystlinje = alt er land
        for poly in land_polygons:
            if point_in_polygon(x, y, poly):
                return True
        return False

    # Gatenavn langs veier (textPath)
    svg_parts.append('<!-- Gatenavn -->')
    svg_parts.append('<defs>')
    for name, (path_id, seg_len, d, css_class, pts) in seen_road_names.items():
        if seg_len < 40:  # Skip for korte veisegmenter
            continue
        # Sjekk om midtpunktet av veien er på land (skip for sentrum-zoom)
        if not skip_label_filter:
            mid_idx = len(pts) // 2
            mid_x, mid_y = pts[mid_idx]
            if not is_on_land(mid_x, mid_y):
                continue  # Skip labels i sjøen
        # Sørg for at tekst løper venstre-til-høyre
        if pts[-1][0] < pts[0][0]:
            # Reverser path
            reversed_pts = list(reversed(pts))
            d = points_to_path(reversed_pts)
        svg_parts.append(f'<path id="{path_id}" d="{d}"/>')
        road_label_paths.append((path_id, name, css_class, seg_len))
    svg_parts.append('</defs>')

    for path_id, name, css_class, seg_len in road_label_paths:
        label_class = "road-label-major" if css_class == "road-major" else "road-label"
        # Plasser tekst omtrent midt på veien
        offset_pct = max(5, int(50 - len(name) * 1.5))
        svg_parts.append(
            f'<text class="{label_class}">'
            f'<textPath href="#{path_id}" startOffset="{offset_pct}%">{name}</textPath>'
            f'</text>'
        )

    # Stedsnavn
    svg_parts.append('<!-- Stedsnavn -->')
    for p in places:
        if p["name"]:
            svg_parts.append(
                f'<g class="{p["class"]}" transform="translate({p["x"]:.1f},{p["y"]:.1f})">'
                f'<text text-anchor="middle" dy="0.35em">{p["name"]}</text>'
                f'</g>'
            )

    svg_parts.append('</g>')
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


# ============================================================
#  MAIN
# ============================================================

def bounds_from_center_zoom(center_lat, center_lng, zoom, width_px, height_px):
    """Beregn lat/lng-bounds fra senterpunkt og zoom-nivå.

    Bruker OSM/Leaflet sin standard tile-projeksjon:
      resolution = 156543.03 * cos(lat) / 2^zoom  (meter per piksel)

    Args:
        center_lat, center_lng: Senterpunkt i desimalgrader
        zoom: OSM zoom-nivå (f.eks. 16)
        width_px, height_px: Pikselstørrelse på innholdsområdet (uten padding)

    Returns:
        (south, west, north, east) som desimalgrader
    """
    resolution = 156543.03 * math.cos(math.radians(center_lat)) / (2 ** zoom)
    width_m = width_px * resolution
    height_m = height_px * resolution

    # Konverter meter til grader
    dlat = (height_m / 2) / 111000
    dlng = (width_m / 2) / (111000 * math.cos(math.radians(center_lat)))

    return (center_lat - dlat, center_lng - dlng,
            center_lat + dlat, center_lng + dlng)


def main():
    palette_names = ", ".join(PALETTES.keys())
    parser = argparse.ArgumentParser(
        description="Generer SVG-kart fra OSM-data",
        epilog="""Eksempler:
  # Fra bounds:
  python3 osm_to_svg.py --bounds "70.368,31.086,70.382,31.128" --output kart.svg
  # Fra senterpunkt + fast zoom (anbefalt for inset):
  python3 osm_to_svg.py --center 70.3725,31.1030 --zoom 16 --output inset.svg""",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    bounds_group = parser.add_mutually_exclusive_group(
        required="--list-palettes" not in sys.argv)
    bounds_group.add_argument("--bounds",
                        help="south,west,north,east (f.eks. 70.368,31.086,70.382,31.128)")
    bounds_group.add_argument("--center",
                        help="lat,lng senterpunkt (bruk med --zoom, f.eks. 70.3725,31.1030)")

    parser.add_argument("--zoom", type=float, default=None,
                        help="OSM zoom-nivå (f.eks. 16). Krever --center. "
                             "Beregner bounds automatisk slik at m/px matcher tile-zoom.")
    parser.add_argument("--output", required="--list-palettes" not in sys.argv,
                        help="Output SVG-fil")
    parser.add_argument("--width", type=int, default=800, help="Kartbredde i piksler (default: 800)")
    parser.add_argument("--padding", type=int, default=20, help="Padding rundt kartet (default: 20)")
    parser.add_argument("--palette", default=DEFAULT_PALETTE,
                        help=f"Fargepalett ({palette_names}). Default: {DEFAULT_PALETTE}")
    parser.add_argument("--no-label-filter", action="store_true",
                        help="Ikke filtrer bort gatenavn i sjøen (for sentrum-zoom)")
    parser.add_argument("--road-scale", type=float, default=1.0,
                        help="Skaleringsfaktor for veibredder og gatenavn (default: 1.0). "
                             "Bruk 2.0 for inset ved zoom 16 for tykkere veier og lesbare gatenavn.")
    parser.add_argument("--list-palettes", action="store_true",
                        help="Vis tilgjengelige paletter og avslutt")
    args = parser.parse_args()

    if args.list_palettes:
        for key, pal in PALETTES.items():
            print(f"  {key:12s}  {pal['name']} — {pal['description']}")
        sys.exit(0)

    if args.palette not in PALETTES:
        print(f"Ukjent palett '{args.palette}'. Tilgjengelige: {palette_names}", file=sys.stderr)
        sys.exit(1)

    # --- Beregn bounds ---
    if args.center:
        if args.zoom is None:
            print("Feil: --center krever --zoom", file=sys.stderr)
            sys.exit(1)
        clat, clng = [float(x) for x in args.center.split(",")]

        # Estimer høyde først (trenger content-pixels for bounds-beregning)
        # Bruk Mercator-aspekt fra et lite test-bounds for å finne høyde
        # Iterativ: start med square, beregn bounds, avled aspect, gjenta
        est_height = args.width  # Startgjetning: square
        for _ in range(3):  # Konvergerer på 2-3 iterasjoner
            south, west, north, east = bounds_from_center_zoom(
                clat, clng, args.zoom, args.width, est_height)
            x_range = east - west
            y_range = lat_to_y(north) - lat_to_y(south)
            aspect = y_range / math.radians(x_range)
            est_height = int(args.width * aspect)

        south, west, north, east = bounds_from_center_zoom(
            clat, clng, args.zoom, args.width, est_height)

        resolution = 156543.03 * math.cos(math.radians(clat)) / (2 ** args.zoom)
        print(f"Zoom {args.zoom} @ ({clat:.4f}, {clng:.4f}): "
              f"{resolution:.3f} m/px, "
              f"dekning {args.width * resolution:.0f}m × {est_height * resolution:.0f}m",
              file=sys.stderr)
    else:
        if args.zoom is not None:
            print("Advarsel: --zoom ignorert uten --center", file=sys.stderr)
        south, west, north, east = [float(x) for x in args.bounds.split(",")]

    bounds = (south, west, north, east)

    # Beregn høyde basert på Mercator-projeksjon (bevar proporsjoner)
    x_range = east - west
    y_range = lat_to_y(north) - lat_to_y(south)
    aspect = y_range / (math.radians(x_range))  # Mercator aspect ratio
    height = int(args.width * aspect)

    pal = PALETTES[args.palette]
    print(f"Palett: {pal['name']} — {pal['description']}", file=sys.stderr)
    print(f"Kartdimensjoner: {args.width}x{height} px (+ {args.padding}px padding)", file=sys.stderr)

    # 1. Hent OSM-data
    elements = fetch_osm(south, west, north, east)

    # 2. Parse og projiser
    ways, places = parse_elements(elements, bounds, args.width, height, args.padding)
    print(f"  {len(ways)} ways, {len(places)} stedsnavn", file=sys.stderr)

    # 3. Generer SVG
    svg = generate_svg(ways, places, args.width, height, args.padding,
                       palette_name=args.palette,
                       skip_label_filter=args.no_label_filter,
                       road_scale=args.road_scale)

    # 4. Skriv til fil
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Skrev {args.output} ({len(svg)} tegn)", file=sys.stderr)


if __name__ == "__main__":
    main()
