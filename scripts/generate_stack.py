"""Generate a skillicons.dev-style tech-stack row: real brand icons, no text
labels, no pill backgrounds — just a clean wrapping grid of true-color logos.

Unlike skillicons.dev (unmaintained for 7+ months, a live external service
this README would depend on forever), every icon here is fetched fresh at
generation time and baked into a fully self-contained SVG. Nothing at
render time touches a third party.

Sources, in order of preference:
- devicon "original" variant   — the real, multi-color logo artwork for
                                  languages/frameworks/tools (Python's
                                  blue+yellow snakes, Azure's blue gradient,
                                  Redis's layered stack, etc.)
- simple-icons                 — brand color for marks devicon lacks
                                  (Anthropic, LangChain, CrewAI, Linux)
- Iconify "logos" collection   — OpenAI's mark (simple-icons dropped it;
                                  this collection still carries it)
- Iconify "mdi" collection     — VS Code, recolored to its real brand blue

A handful of brands (OpenAI, GitHub, Anthropic, Flask) are, per their own
official guidelines, monochrome-only: solid black on light backgrounds,
solid white on dark. Those get a small explicit light/dark swap; every
other icon renders in its one true color on both themes.

Usage: python scripts/generate_stack.py
"""

import re
import urllib.request
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

DEVICON = "https://cdn.jsdelivr.net/npm/devicon@latest/icons/{slug}/{slug}-original.svg"
SIMPLE_ICONS = "https://cdn.simpleicons.org/{slug}"
ICONIFY = "https://api.iconify.design/{prefix}:{name}.svg"

MONO_OVERRIDE = {
    # key: (source hex actually baked into the fetched SVG, or None if the
    # icon has no fill of its own at all and needs one injected)
    "openai": None,
    "github": "#181616",
    "anthropic": "#191919",
    "flask": "#010101",
}
MONO_LIGHT = "#161b22"
MONO_DARK = "#f0f6fc"

# (label, loader-kind, slug)
TOOLS = [
    # Ordered by importance to this profile: primary language + its main
    # environment first, then the core GenAI/LLM stack, then ML frameworks,
    # backend/API, cloud, dev infra, and OS last.
    ("Python", "dev", "python"),
    ("OpenAI", "iflogos", "openai-icon"),
    ("Anthropic", "si", "anthropic"),
    ("LangChain", "si", "langchain"),
    ("CrewAI", "si", "crewai"),
    ("FastAPI", "dev", "fastapi"),
    ("Flask", "dev", "flask"),
    ("TensorFlow", "dev", "tensorflow"),
    ("Keras", "dev", "keras"),
    ("scikit-learn", "dev", "scikitlearn"),
    ("Jupyter", "dev", "jupyter"),
    ("Azure", "dev", "azure"),
    ("Docker", "dev", "docker"),
    ("Redis", "dev", "redis"),
    ("Git", "dev", "git"),
    ("GitHub", "dev", "github"),
    ("Postman", "dev", "postman"),
    ("VS Code", "mdi-color", "microsoft-visual-studio-code:#007ACC"),
    ("Linux", "si", "linux"),
    ("Windows", "dev", "windows11"),
]

CANVAS_WIDTH = 1000
OUTER_PAD = 20
ICON_SIZE = 46
GAP = 18


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 stack-generator"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def load_raw(kind, slug):
    if kind == "dev":
        return fetch(DEVICON.format(slug=slug))
    if kind == "si":
        return fetch(SIMPLE_ICONS.format(slug=slug))
    if kind == "iflogos":
        return fetch(ICONIFY.format(prefix="logos", name=slug))
    if kind == "mdi-color":
        name = slug.split(":")[0]
        return fetch(ICONIFY.format(prefix="mdi", name=name))
    raise ValueError(kind)


def parse_viewbox(svg_text):
    m = re.search(r'viewBox="([-\d.]+)\s+([-\d.]+)\s+([\d.]+)\s+([\d.]+)"', svg_text)
    if m:
        return tuple(float(g) for g in m.groups())
    return 0.0, 0.0, 24.0, 24.0


def namespace_and_inline(key, svg_text):
    """Parse an <svg>, prefix every internal id (avoids collisions when many
    icons share one document), return the inner markup as a string."""
    root = ET.fromstring(svg_text)
    id_map = {}
    for el in root.iter():
        old_id = el.get("id")
        if old_id:
            new_id = f"{key}-{old_id}"
            id_map[old_id] = new_id
            el.set("id", new_id)

    url_re = re.compile(r"url\(#([^)]+)\)")
    href_keys = ("href", "{http://www.w3.org/1999/xlink}href")
    for el in root.iter():
        for attr, val in list(el.attrib.items()):
            if attr in href_keys and val.startswith("#") and val[1:] in id_map:
                el.set(attr, "#" + id_map[val[1:]])
            else:
                new_val = url_re.sub(lambda m: f"url(#{id_map.get(m.group(1), m.group(1))})", val)
                if new_val != val:
                    el.set(attr, new_val)

    inner = "".join(ET.tostring(child, encoding="unicode") for child in root)

    # simple-icons puts the brand color on the root <svg fill="...">, not on
    # the inner <path> — that attribute is lost when we drop the wrapper, so
    # re-apply it as a wrapping group before returning.
    root_fill = root.get("fill")
    if root_fill and root_fill.lower() != "none":
        inner = f'<g fill="{root_fill}">{inner}</g>'

    return inner


def load_tool(label, kind, slug):
    key = re.sub(r"[^a-z0-9]", "", label.lower())

    if kind == "mdi-color":
        mdi_slug, hex_color = slug.split(":")
        raw = load_raw(kind, slug)
        raw = raw.replace('fill="currentColor"', f'fill="{hex_color}"')
    else:
        raw = load_raw(kind, slug)

    minx, miny, w, h = parse_viewbox(raw)
    inner = namespace_and_inline(key, raw)
    return key, inner, minx, miny, w, h


def themed_inner(key, inner):
    """Return (light_inner, dark_inner). Identical for true-color icons;
    swapped for the handful of brands that are officially monochrome-only."""
    if key not in MONO_OVERRIDE:
        return inner, inner
    baked_hex = MONO_OVERRIDE[key]
    if baked_hex is None:
        # no native fill (e.g. OpenAI's mark) — inject one via a wrapping <g>
        return (
            f'<g fill="{MONO_LIGHT}">{inner}</g>',
            f'<g fill="{MONO_DARK}">{inner}</g>',
        )
    return (
        inner,
        inner.replace(baked_hex, MONO_DARK).replace(baked_hex.upper(), MONO_DARK),
    )


def layout(n):
    slot = ICON_SIZE + GAP
    usable = CANVAS_WIDTH - 2 * OUTER_PAD
    per_row = max(1, (usable + GAP) // slot)
    rows = []
    for i in range(0, n, per_row):
        rows.append(min(per_row, n - i))
    return rows


def render(theme, loaded):
    rows = layout(len(loaded))
    height = 2 * OUTER_PAD + len(rows) * ICON_SIZE + (len(rows) - 1) * GAP

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{height:.0f}" '
        f'viewBox="0 0 {CANVAS_WIDTH} {height:.0f}">'
    ]

    idx = 0
    for row_i, count in enumerate(rows):
        row_width = count * ICON_SIZE + (count - 1) * GAP
        start_x = (CANVAS_WIDTH - row_width) / 2
        y = OUTER_PAD + row_i * (ICON_SIZE + GAP)
        for c in range(count):
            key, inner, minx, miny, w, h, label = loaded[idx]
            light_inner, dark_inner = themed_inner(key, inner)
            content = dark_inner if theme == "dark" else light_inner

            scale = min(ICON_SIZE / w, ICON_SIZE / h)
            tx = -minx * scale + (ICON_SIZE - w * scale) / 2
            ty = -miny * scale + (ICON_SIZE - h * scale) / 2
            x = start_x + c * (ICON_SIZE + GAP)

            delay = -(idx / len(loaded)) * 5.0
            parts.append(
                f'<g transform="translate({x:.1f},{y:.1f})">'
                f'<animateTransform attributeName="transform" type="translate" '
                f'additive="sum" values="0 0;0 -3;0 0" keyTimes="0;0.5;1" '
                f'dur="3s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
                f'<title>{label}</title>'
                f'<g transform="translate({tx:.2f},{ty:.2f}) scale({scale:.4f})">{content}</g>'
                f"</g>"
            )
            idx += 1

    parts.append("</svg>")
    return "".join(parts)


def main():
    loaded = []
    for label, kind, slug in TOOLS:
        key, inner, minx, miny, w, h = load_tool(label, kind, slug)
        loaded.append((key, inner, minx, miny, w, h, label))
        print(f"fetched {label} ({kind}:{slug})")

    for theme, out in (("dark", "assets/tech-stack-dark.svg"), ("light", "assets/tech-stack-light.svg")):
        svg = render(theme, loaded)
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{out}: {len(loaded)} icons, {len(svg)} bytes")


if __name__ == "__main__":
    main()
