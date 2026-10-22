#!/usr/bin/env python3
"""Convierte el README de awesome-scalability en un indice estructurado.

Salida: data/index.json con una entrada por enlace, mas data/parse_warnings.json
con lo que no se pudo interpretar. Determinista: misma entrada, mismo byte.

Uso:
    python scripts/parse_readme.py
    python scripts/parse_readme.py --readme README.es.md --out data/index.es.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = Path(__file__).resolve().parent / "taxonomy" / "sections.yml"

SECTION_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$")
# Un item es nivel 1 si no lleva sangria; nivel 2 si la lleva (tab o espacios).
ITEM_RE = re.compile(r"^(?P<indent>[\t ]*)\*\s+\[(?P<title>.+)\]\((?P<url>[^)\s]+)\)")

VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "atscaleconference.com")
SLIDE_HOSTS = ("slideshare.net", "speakerdeck.com", "slides.com")

MAX_SLUG = 80


def load_taxonomy() -> tuple[dict[str, str], set[str]]:
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    return data.get("sections", {}), set(data.get("skip", []))


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:MAX_SLUG].rstrip("-")


def link_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def detect_kind(url: str) -> str:
    low = url.lower()
    if low.endswith(".pdf"):
        return "pdf"
    if any(h in low for h in VIDEO_HOSTS):
        return "video"
    if any(h in low for h in SLIDE_HOSTS):
        return "slides"
    return "article"


def extract_author(title: str) -> str | None:
    """Saca autor o empresa del propio titulo. Nunca inventa: si no hay patron, None.

    Formas reales en el corpus:
        "EVCache: Distributed In-memory Caching at Netflix"      -> Netflix
        "Scaling Dropbox - Kevin Modzelewski, Back-end Engineer" -> Kevin Modzelewski
        "Distributed Systems in One Lesson - Tim Berglund, ... at Confluent" -> Confluent
    """
    if " at " in title:
        tail = title.rsplit(" at ", 1)[1].strip()
        if tail and len(tail) <= 60 and not tail.endswith((":", "-")):
            return tail
    if " - " in title:
        tail = title.rsplit(" - ", 1)[1].strip()
        # "Nombre, Cargo" -> nos queda el nombre
        name = tail.split(",")[0].strip()
        if name and len(name) <= 60:
            return name
    return None


def indent_depth(indent: str) -> int:
    """Profundidad de sangria. El upstream mezcla tabs y grupos de 4 espacios."""
    return indent.count("	") + indent.count(" ") // 4


def parse(readme: Path, sections_es: dict[str, str], skip: set[str]):
    """Recorre el README manteniendo una pila de ancestros.

    La jerarquia real llega a 4 niveles, p. ej.:
        NoSQL Databases > Columnar Databases > Cassandra > Cassandra at Instagram
    Por eso cada entrada guarda su `path` completo en vez de un unico campo
    de subcategoria: esa ruta alimenta las facetas del sitio.
    """
    lines = readme.read_text(encoding="utf-8").splitlines()
    entries: list[dict] = []
    warnings: list[dict] = []
    seen_slugs: dict[str, str] = {}

    section: str | None = None
    stack: list[tuple[int, str]] = []  # (profundidad, titulo) de los ancestros

    def next_item_depth(idx: int) -> int | None:
        """Profundidad del siguiente item, o None si la seccion se acaba antes."""
        for nxt in lines[idx + 1:]:
            if not nxt.strip():
                continue
            if SECTION_RE.match(nxt):
                return None
            m = ITEM_RE.match(nxt)
            return indent_depth(m.group("indent")) if m else None
        return None

    for i, raw in enumerate(lines):
        if (ms := SECTION_RE.match(raw)):
            section = ms.group("name").strip()
            stack = []
            continue

        mi = ITEM_RE.match(raw)
        if not mi or section is None or section in skip:
            continue

        title = mi.group("title").strip()
        # Hay URLs con espacio o tab final en el upstream.
        url = mi.group("url").strip().rstrip(",.")
        depth = indent_depth(mi.group("indent"))

        if not url.startswith(("http://", "https://")):
            warnings.append({"line": i + 1, "reason": "url_no_http", "url": url,
                             "title": title})
            continue

        while stack and stack[-1][0] >= depth:
            stack.pop()
        path = [t for _, t in stack]
        stack.append((depth, title))

        nd = next_item_depth(i)
        is_container = nd is not None and nd > depth

        slug = slugify(title) or f"link-{link_id(url)}"
        if slug in seen_slugs and seen_slugs[slug] != url:
            slug = f"{slug}-{link_id(url)[:6]}"
        seen_slugs[slug] = url

        author = extract_author(title)
        if author is None and not is_container:
            warnings.append({"line": i + 1, "reason": "autor_no_deducible",
                             "title": title})

        entries.append({
            "id": link_id(url),
            "slug": slug,
            "section": section,
            "section_es": sections_es.get(section, section),
            "path": path,
            "subcategory": path[0] if path else None,
            "topic": path[-1] if path else None,
            "title": title,
            "author": author,
            "url": url,
            "kind": detect_kind(url),
            "depth": depth,
            "is_container": is_container,
            "line": i + 1,
        })

    return entries, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--out", default="data/index.json")
    ap.add_argument("--warnings-out", default="data/parse_warnings.json")
    args = ap.parse_args()

    readme = (ROOT / args.readme) if not Path(args.readme).is_absolute() else Path(args.readme)
    if not readme.exists():
        print(f"error: no existe {readme}", file=sys.stderr)
        return 1

    sections_es, skip = load_taxonomy()
    entries, warnings = parse(readme, sections_es, skip)

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (ROOT / args.warnings_out).write_text(
        json.dumps(warnings, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    by_kind: dict[str, int] = {}
    for e in entries:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    sin_autor = sum(1 for w in warnings if w["reason"] == "autor_no_deducible")
    hojas = sum(1 for e in entries if not e["is_container"])
    max_depth = max((e["depth"] for e in entries), default=0)

    print(f"{len(entries)} enlaces -> {out.relative_to(ROOT)}")
    print(f"  hojas (articulos): {hojas}  |  contenedores (categorias): "
          f"{len(entries) - hojas}")
    print(f"  por tipo: {by_kind}")
    print(f"  secciones: {len({e['section'] for e in entries})}  |  "
          f"profundidad maxima: {max_depth + 1} niveles")
    print(f"  nodos de taxonomia distintos: "
          f"{len({t for e in entries for t in e['path']})}")
    print(f"  sin autor deducible: {sin_autor}  |  urls malformadas: "
          f"{len(warnings) - sin_autor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
