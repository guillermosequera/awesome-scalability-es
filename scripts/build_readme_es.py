#!/usr/bin/env python3
"""Genera README.es.md a partir de README.md y los ficheros de traducción.

Por qué generar en vez de editar a mano: el upstream añade enlaces cada pocas
semanas. Un README.es.md editado a mano se desincroniza en la primera
actualización y hay que rehacerlo entero. Generándolo, la traducción vive en
`scripts/taxonomy/*.yml` y el documento se regenera en segundos, también desde
la Action semanal.

Qué se traduce: la presentación, los bloques `####` con sus citas, el índice,
los 10 títulos de sección y los 55 nodos de taxonomía.
Qué NO se traduce: los 864 títulos de artículo, que son nombres de
publicaciones, y ninguna URL.

En modo estricto (por defecto) aborta si encuentra prosa sin traducir: es
preferible fallar a publicar un README medio en inglés sin darse cuenta.

Uso:
    python scripts/build_readme_es.py
    python scripts/build_readme_es.py --check     # no escribe, solo verifica
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TAX = Path(__file__).resolve().parent / "taxonomy"

SECTION_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$")
H4_RE = re.compile(r"^####\s+(?P<name>.+?)\s*$")
ITEM_RE = re.compile(r"^(?P<indent>[\t ]*)\*\s+\[(?P<title>.+)\]\((?P<url>[^)\s]+)\)(?P<tail>.*)$")
TOC_RE = re.compile(r"^-\s+\[(?P<name>.+)\]\(#(?P<anchor>[^)]+)\)\s*$")
LOGO_RE = re.compile(r"^\[!\[Logo\]")


def anchor(text: str) -> str:
    """Ancla que GitHub genera para un encabezado.

    Minúsculas, espacios por guiones, se descarta la puntuación. Las tildes y
    las eñes SE CONSERVAN: '## Organización' -> '#organización'.
    """
    text = text.strip().lower()
    out = []
    for ch in text:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch in " \t":
            out.append("-")
        elif unicodedata.combining(ch):
            out.append(ch)
    return "".join(out)


def load() -> tuple[dict, dict, dict, list[str]]:
    sec = yaml.safe_load((TAX / "sections.yml").read_text(encoding="utf-8"))
    nod = yaml.safe_load((TAX / "nodos_es.yml").read_text(encoding="utf-8"))
    pro = yaml.safe_load((TAX / "prosa_es.yml").read_text(encoding="utf-8"))
    return sec["sections"], nod["nodes"], pro, sec.get("skip", [])


def normalize(s: str) -> str:
    """Para comparar prosa sin que un espacio de más rompa la correspondencia."""
    return re.sub(r"\s+", " ", s).strip()


def build(readme: Path, sections: dict, nodes: dict, prosa: dict,
          skip: list[str]) -> tuple[list[str], list[str]]:
    lines = readme.read_text(encoding="utf-8").splitlines()
    blocks = {normalize(k): v.strip() for k, v in prosa["blocks"].items()}
    headers = prosa["headers"]

    out: list[str] = []
    problems: list[str] = []
    in_toc = False
    logo_done = False

    for i, raw in enumerate(lines, 1):
        # Logo: se conserva y debajo va el selector de idioma y el crédito.
        if not logo_done and LOGO_RE.match(raw):
            out.append(raw)
            out.append("")
            out.append(prosa["header"].strip())
            logo_done = True
            continue

        if (m := SECTION_RE.match(raw)):
            name = m.group("name").strip()
            if name == "Content":
                # El índice se regenera entero: el del upstream apunta a #book,
                # un ancla que no existe, y no se reproduce.
                out.append("## Contenido")
                out.append("")
                for en, es in sections.items():
                    out.append(f"- [{es}](#{anchor(es)})")
                in_toc = True
                continue
            in_toc = False
            if name not in sections:
                problems.append(f"L{i}: sección sin traducir: {name!r}")
                out.append(raw)
            else:
                out.append(f"## {sections[name]}")
            continue

        if in_toc and (TOC_RE.match(raw) or not raw.strip()):
            continue  # ya emitido arriba
        in_toc = False

        if (m := H4_RE.match(raw)):
            name = m.group("name").strip()
            if name not in headers:
                problems.append(f"L{i}: encabezado sin traducir: {name!r}")
                out.append(raw)
            else:
                out.append(f"#### {headers[name]}")
            continue

        if (m := ITEM_RE.match(raw)):
            title = m.group("title").strip()
            # Solo los nodos de taxonomía se traducen. Los títulos de artículo
            # se copian tal cual, con su URL y su espaciado original.
            if title in nodes:
                out.append(f"{m.group('indent')}* [{nodes[title]}]"
                           f"({m.group('url')}){m.group('tail')}")
            else:
                out.append(raw)
            continue

        if not raw.strip():
            out.append(raw)
            continue

        key = normalize(raw)
        if key in blocks:
            out.append(blocks[key])
        else:
            problems.append(f"L{i}: prosa sin traducir: {raw[:70]!r}")
            out.append(raw)

    return out, problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--out", default="README.es.md")
    ap.add_argument("--check", action="store_true",
                    help="verificar sin escribir")
    ap.add_argument("--allow-untranslated", action="store_true",
                    help="generar aunque quede prosa en inglés (no recomendado)")
    ap.add_argument("--patch-en", action="store_true",
                    help="insertar el selector de idioma en README.md (solo rama es)")
    args = ap.parse_args()

    readme = ROOT / args.readme
    if not readme.exists():
        print(f"error: no existe {readme}", file=sys.stderr)
        return 1

    sections, nodes, prosa, skip = load()
    out, problems = build(readme, sections, nodes, prosa, skip)

    if problems:
        print(f"{len(problems)} fragmentos sin traducir:", file=sys.stderr)
        for p in problems[:20]:
            print(f"  {p}", file=sys.stderr)
        if not args.allow_untranslated:
            print("\nAborta sin escribir. Añade las traducciones que falten a "
                  "scripts/taxonomy/ o usa --allow-untranslated.", file=sys.stderr)
            return 1

    # Paridad de URLs: la garantía de que no se perdió ni se inventó un enlace.
    # Se descuentan las del bloque de crédito, que son añadidas a propósito.
    url_re = re.compile(r"\]\((https?://[^)\s]+)\)")
    src_urls = url_re.findall(readme.read_text(encoding="utf-8"))
    out_text = "\n".join(out) + "\n"
    new_urls = url_re.findall(out_text)
    for u in url_re.findall(prosa["header"]):
        if u in new_urls:
            new_urls.remove(u)
    if src_urls != new_urls:
        print(f"error: las URLs no coinciden ({len(src_urls)} originales, "
              f"{len(new_urls)} generadas)", file=sys.stderr)
        falta = set(src_urls) - set(new_urls)
        sobra = set(new_urls) - set(src_urls)
        for u in list(falta)[:5]:
            print(f"  falta: {u}", file=sys.stderr)
        for u in list(sobra)[:5]:
            print(f"  sobra: {u}", file=sys.stderr)
        return 1

    # Anclas: toda referencia interna debe resolver a un encabezado real.
    heads = {anchor(m.group(1)) for m in re.finditer(r"^#{2,4}\s+(.+?)\s*$",
                                                     out_text, re.M)}
    refs = set(re.findall(r"\]\(#([^)]+)\)", out_text))
    rotas = refs - heads
    if rotas:
        print(f"error: {len(rotas)} anclas sin destino: {sorted(rotas)}",
              file=sys.stderr)
        return 1

    if args.check:
        print(f"ok: {len(src_urls)} URLs, {len(refs)} anclas internas, todas resuelven")
        return 0

    if args.patch_en:
        en_lines = readme.read_text(encoding="utf-8").splitlines()
        sel = prosa["header_en"].strip()
        if sel not in "\n".join(en_lines):
            for n, l in enumerate(en_lines):
                if LOGO_RE.match(l):
                    en_lines[n + 1:n + 1] = ["", sel]
                    break
            readme.write_text("\n".join(en_lines) + "\n", encoding="utf-8")
            print(f"{args.readme}: selector de idioma insertado")
        else:
            print(f"{args.readme}: ya tenía el selector")

    (ROOT / args.out).write_text(out_text, encoding="utf-8")
    print(f"{args.out}: {len(out)} líneas, {len(src_urls)} URLs intactas, "
          f"{len(refs)} anclas resueltas")
    print(f"  secciones traducidas: {len(sections)}")
    print(f"  nodos de taxonomía traducidos: "
          f"{sum(1 for l in out for t in nodes.values() if f'[{t}](' in l)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
