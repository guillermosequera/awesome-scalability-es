#!/usr/bin/env python3
"""Extrae el texto de cada enlace del indice y lo deja en ficheros de texto plano.

Este script NO usa ningun modelo de IA ni consume tokens: es scraping puro.
El resumen se genera despues, por separado, con el modelo que quieras.

Dos pasadas:
  1. HTTP plano (httpx + trafilatura). Rapido, resuelve la mayoria.
  2. Navegador real (Playwright Chromium) para lo que la pasada 1 no logro.
     Hace falta: ~1/3 del corpus devuelve 403 a peticiones planas (Medium y cia).

Salida en --out-dir (por defecto `extracted/`, ignorada por git):
    <slug>.txt        texto limpio, UTF-8
    _manifest.json    que se extrajo, como, cuanto y que fallo

IMPORTANTE: esa carpeta queda fuera del control de versiones a proposito. Los
textos son de sus autores; sirven como insumo local, no para redistribuir.

Uso:
    python scripts/extract_text.py --limit 20          # prueba
    python scripts/extract_text.py                     # corpus completo
    python scripts/extract_text.py --bundle 12         # + lotes para pasar a un modelo
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import trafilatura

ROOT = Path(__file__).resolve().parent.parent

UA_HTTP = ("Mozilla/5.0 (compatible; awesome-scalability-es/1.0; "
           "+https://github.com/guillermosequera/awesome-scalability-es)")
UA_BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

MIN_CHARS = 800          # por debajo de esto el texto no sirve para resumir
HTTP_TIMEOUT = 20
BROWSER_TIMEOUT = 45_000
HTTP_CONCURRENCY = 8
HTTP_DOMAIN_DELAY = 1.5  # segundos entre peticiones al mismo dominio
BROWSER_DOMAIN_DELAY = 4.0
# Techo y reintentos deliberadamente bajos: medido 2026-10-21, cuando un dominio
# como Medium bloquea, no cede ni con 60 s de espera. Insistir solo gasta tiempo;
# la pasada 3 (Wayback) resuelve esos casos en segundos.
MAX_DOMAIN_DELAY = 20.0
BROWSER_RETRIES = 1
SKIP_KINDS = {"video", "pdf", "slides"}

BLOCK_ASSETS = "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,mp4,avi}"

WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_SNAPSHOTS = 4       # cuantos snapshots probar por URL
WAYBACK_DELAY = 2.0         # archive.org responde 429 con facilidad
WAYBACK_CDX_RETRIES = 3
WAYBACK_THROTTLE_WAIT = 20.0  # espera base cuando nos devuelve 429


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def domain(url: str) -> str:
    return urlsplit(url).netloc.lower()


def clean(html: str | None) -> str:
    if not html:
        return ""
    txt = trafilatura.extract(html, include_comments=False, include_tables=False,
                              favor_precision=True)
    return (txt or "").strip()


class DomainPacer:
    """Un turno por dominio: nunca dos peticiones seguidas sin respirar."""

    def __init__(self, delay: float):
        self.delay = delay
        self.last: dict[str, float] = {}
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def wait(self, url: str) -> None:
        d = domain(url)
        async with self.locks[d]:
            gap = time.monotonic() - self.last.get(d, 0.0)
            if gap < self.delay:
                await asyncio.sleep(self.delay - gap + random.uniform(0, 0.4))
            self.last[d] = time.monotonic()


class Store:
    """Persistencia incremental: cada texto se guarda en cuanto se obtiene.

    El corpus completo tarda horas. Si el guardado ocurriera solo al final, una
    interrupcion a mitad tiraria todo el trabajo a la basura. Aqui cada enlace
    resuelto se escribe en el acto y el manifiesto se vuelca cada FLUSH_EVERY
    registros, de modo que Ctrl+C cuesta como maximo unos pocos enlaces.
    """

    FLUSH_EVERY = 10

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.path = out_dir / "_manifest.json"
        self.records: dict[str, dict] = {}
        self.dirty = 0
        if self.path.exists():
            try:
                for m in json.loads(self.path.read_text(encoding="utf-8")):
                    self.records[m["slug"]] = m
            except (json.JSONDecodeError, KeyError):
                print("  ! manifiesto ilegible, se empieza uno nuevo",
                      file=sys.stderr)

    def chars_of(self, slug: str) -> int:
        return self.records.get(slug, {}).get("chars", 0)

    def save(self, rec: dict, src: dict | None = None) -> None:
        """Guarda un resultado si mejora lo que ya habia para ese enlace."""
        slug = rec["slug"]
        if rec["chars"] < self.chars_of(slug) and slug in self.records:
            return  # un intento anterior consiguio mas texto: se respeta
        src = src or {}
        status = classify(rec)
        if status == "ok":
            (self.out_dir / f"{slug}.txt").write_text(rec["text"], encoding="utf-8")
        self.records[slug] = {
            "slug": slug, "title": rec["title"], "url": rec["url"],
            "section": src.get("section", self.records.get(slug, {}).get("section", "")),
            "path": src.get("path", self.records.get(slug, {}).get("path", [])),
            "status": status, "method": rec["method"], "chars": rec["chars"],
            "http_status": rec["http_status"], "final_url": rec["final_url"],
            "archive_url": rec.get("archive_url"),
            "archive_timestamp": rec.get("archive_timestamp"),
            "error": rec["error"], "extracted_at": now(),
        }
        self.dirty += 1
        if self.dirty >= self.FLUSH_EVERY:
            self.flush()

    def flush(self) -> None:
        if not self.dirty:
            return
        data = sorted(self.records.values(), key=lambda m: m["slug"])
        # Escritura atomica: un Ctrl+C a medias no debe dejar JSON truncado.
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        tmp.replace(self.path)
        self.dirty = 0

    def solved(self) -> set[str]:
        return {s for s, m in self.records.items() if m["chars"] >= MIN_CHARS}


# --------------------------------------------------------------------------- #
# Pasada 1: HTTP plano
# --------------------------------------------------------------------------- #

async def fetch_http(client: httpx.AsyncClient, entry: dict, pacer: DomainPacer,
                     sem: asyncio.Semaphore) -> dict:
    async with sem:
        await pacer.wait(entry["url"])
        rec = {"slug": entry["slug"], "url": entry["url"], "title": entry["title"],
               "method": "http", "chars": 0, "http_status": None,
               "final_url": None, "error": None, "text": ""}
        try:
            r = await client.get(entry["url"])
            rec["http_status"] = r.status_code
            rec["final_url"] = str(r.url)
            if r.status_code == 200:
                rec["text"] = clean(r.text)
                rec["chars"] = len(rec["text"])
        except Exception as exc:
            rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
        return rec


async def pass_http(entries: list[dict], concurrency: int, store: Store) -> list[dict]:
    pacer = DomainPacer(HTTP_DOMAIN_DELAY)
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency * 2)
    headers = {"User-Agent": UA_HTTP, "Accept-Language": "en-US,en;q=0.9"}
    by_slug = {e["slug"]: e for e in entries}
    out: list[dict] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True,
                                 headers=headers, limits=limits) as client:
        tasks = [fetch_http(client, e, pacer, sem) for e in entries]
        done = 0
        for coro in asyncio.as_completed(tasks):
            rec = await coro
            store.save(rec, by_slug.get(rec["slug"]))
            out.append({**rec, "text": ""})  # el texto ya esta en disco
            done += 1
            if done % 25 == 0 or done == len(tasks):
                ok = sum(1 for r in out if r["chars"] >= MIN_CHARS)
                print(f"  http {done}/{len(tasks)}  utiles={ok}", flush=True)
    store.flush()
    return out


# --------------------------------------------------------------------------- #
# Pasada 2: navegador real
# --------------------------------------------------------------------------- #

def pass_browser(pending: list[dict], store: Store) -> list[dict]:
    """Segunda pasada con navegador real, con cola y enfriamiento por dominio.

    Clave aprendida midiendo: un 403 de Medium casi nunca es un bloqueo
    permanente, es rate-limit por golpear el dominio demasiado seguido. Asi que
    ante un fallo no se insiste en el sitio: se reencola al final (lo que deja
    pasar otros dominios por delante) y se triplica el tiempo de espera de ese
    dominio. Reintentar en caliente, como hacia la version anterior, solo
    confirma el bloqueo.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ! playwright no instalado: se omite la pasada de navegador",
              file=sys.stderr)
        return []

    out: list[dict] = []
    last: dict[str, float] = {}
    delay: dict[str, float] = {}
    tries: dict[str, int] = defaultdict(int)
    queue = deque(pending)
    total = len(pending)
    n = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA_BROWSER, locale="en-US",
                                  viewport={"width": 1280, "height": 900})
        # Imagenes y fuentes no aportan texto: fuera, es mucho mas rapido.
        ctx.route(BLOCK_ASSETS, lambda route: route.abort())

        while queue:
            entry = queue.popleft()
            url = entry["url"]
            d = domain(url)
            n += 1
            wait = delay.setdefault(d, BROWSER_DOMAIN_DELAY)

            gap = time.monotonic() - last.get(d, 0.0)
            if gap < wait:
                time.sleep(wait - gap + random.uniform(0, 0.6))
            last[d] = time.monotonic()

            rec = {"slug": entry["slug"], "url": url, "title": entry["title"],
                   "method": "browser", "chars": 0, "http_status": None,
                   "final_url": None, "error": None, "text": ""}
            page = ctx.new_page()
            try:
                resp = page.goto(url, wait_until="domcontentloaded",
                                 timeout=BROWSER_TIMEOUT)
                page.wait_for_timeout(2500)
                rec["http_status"] = resp.status if resp else None
                rec["final_url"] = page.url
                rec["text"] = clean(page.content())
                rec["chars"] = len(rec["text"])
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
            finally:
                page.close()

            if rec["chars"] >= MIN_CHARS:
                store.save(rec, entry)
                out.append({**rec, "text": ""})
                print(f"  nav {n}/{total} ok  {rec['chars']:>6}ch  {d}", flush=True)
                continue

            tries[entry["slug"]] += 1
            if tries[entry["slug"]] <= BROWSER_RETRIES:
                delay[d] = min(wait * 3, MAX_DOMAIN_DELAY)
                queue.append(entry)
                total += 1
                print(f"  nav {n}/{total} .. {rec['chars']:>6}ch  {d}  "
                      f"reencolado, espera {delay[d]:.0f}s", flush=True)
            else:
                store.save(rec, entry)
                out.append({**rec, "text": ""})
                print(f"  nav {n}/{total} XX {rec['chars']:>6}ch  {d}  agotado",
                      flush=True)

        browser.close()
    store.flush()
    return out


# --------------------------------------------------------------------------- #
# Pasada 3: Wayback Machine
# --------------------------------------------------------------------------- #

def cdx_snapshots(c: httpx.Client, url: str) -> tuple[list, bool]:
    """Snapshots de una URL via CDX. Devuelve (filas, nos_frenaron).

    archive.org responde 429 cuando se le consulta en volumen. Tratar ese 429
    como 'no esta archivado' es el error que hizo fracasar la corrida del
    2026-10-22: 40 enlaces se dieron por irrecuperables sin estarlo. Aqui se
    reintenta con espera creciente y, si persiste, se informa del frenazo para
    que el enlace vuelva a intentarse en otra corrida.
    """
    for attempt in range(WAYBACK_CDX_RETRIES + 1):
        try:
            r = c.get(WAYBACK_CDX, params={
                "url": url, "output": "json", "filter": "statuscode:200",
                "fl": "timestamp", "limit": str(-WAYBACK_SNAPSHOTS)})
        except Exception:
            time.sleep(WAYBACK_DELAY * (attempt + 1))
            continue
        if r.status_code == 200:
            try:
                return r.json()[1:], False
            except json.JSONDecodeError:
                return [], False
        if r.status_code in (429, 503):
            if attempt < WAYBACK_CDX_RETRIES:
                time.sleep(WAYBACK_THROTTLE_WAIT * (attempt + 1))
                continue
            return [], True
        return [], False
    return [], True


def pass_wayback(pending: list[dict], store: Store) -> list[dict]:
    """Ultimo recurso: el texto archivado en la Wayback Machine.

    Resuelve justo lo que el navegador no puede: dominios que bloquean de forma
    persistente (Medium tras disparar su limite, codeascraft, netflixtechblog).
    Medido 2026-10-21: 5 de 6 casos irrecuperables por las otras dos vias.

    Dos detalles aprendidos midiendo:
      - El endpoint /wayback/available responde 429 con facilidad. La CDX API no.
      - El snapshot MAS RECIENTE puede ser la propia pagina de bloqueo archivada.
        Por eso se prueban varios, de mas antiguo a mas nuevo: los snapshots
        viejos son anteriores a los muros de pago.
    """
    out: list[dict] = []
    headers = {"User-Agent": UA_HTTP}
    with httpx.Client(timeout=40, follow_redirects=True, headers=headers) as c:
        for n, entry in enumerate(pending, 1):
            url = entry["url"]
            rec = {"slug": entry["slug"], "url": url, "title": entry["title"],
                   "method": "wayback", "chars": 0, "http_status": None,
                   "final_url": None, "error": None, "text": "",
                   "archive_url": None, "archive_timestamp": None}
            try:
                rows, throttled = cdx_snapshots(c, url)
                if throttled:
                    # Distinguir "no esta archivado" de "archive.org nos frena"
                    # importa: lo primero es definitivo, lo segundo se reintenta.
                    rec["error"] = "wayback 429: reintentar mas tarde"
                elif not rows:
                    rec["error"] = "sin snapshot en Wayback"
                else:
                    # De mas antiguo a mas nuevo.
                    for (ts,) in rows:
                        snap = f"https://web.archive.org/web/{ts}id_/{url}"
                        try:
                            s = c.get(snap)
                            txt = clean(s.text)
                        except Exception:
                            continue
                        if len(txt) > rec["chars"]:
                            rec.update(text=txt, chars=len(txt), archive_url=snap,
                                       archive_timestamp=ts, http_status=s.status_code,
                                       final_url=snap)
                        if rec["chars"] >= MIN_CHARS:
                            break
                        time.sleep(WAYBACK_DELAY)
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"[:200]

            store.save(rec, entry)
            out.append({**rec, "text": ""})
            mark = "ok" if rec["chars"] >= MIN_CHARS else "XX"
            snap_info = rec["archive_timestamp"][:8] if rec["archive_timestamp"] else "-"
            print(f"  arch {n}/{len(pending)} {mark} {rec['chars']:>6}ch  "
                  f"snap={snap_info}  {domain(url)}", flush=True)
            time.sleep(WAYBACK_DELAY)
    store.flush()
    return out


# --------------------------------------------------------------------------- #
# Clasificacion y salida
# --------------------------------------------------------------------------- #

def classify(rec: dict) -> str:
    if rec["chars"] >= MIN_CHARS:
        return "ok"
    if rec["http_status"] in (401, 403, 429):
        return "blocked"
    if rec["http_status"] in (404, 410):
        return "dead"
    if rec["error"]:
        return "error"
    return "poor"


def write_bundles(out_dir: Path, records: list[dict], size: int) -> int:
    """Agrupa los textos en lotes listos para pasarselos a cualquier modelo."""
    bdir = out_dir / "bundles"
    bdir.mkdir(parents=True, exist_ok=True)
    for f in bdir.glob("bundle-*.txt"):
        f.unlink()

    usable = [r for r in records if r["status"] == "ok"]
    count = 0
    for i in range(0, len(usable), size):
        count += 1
        parts = []
        for r in usable[i:i + size]:
            body = (out_dir / f"{r['slug']}.txt").read_text(encoding="utf-8")
            ruta = " > ".join(r.get("path") or [])
            parts.append(
                f'<articulo slug="{r["slug"]}">\n'
                f'titulo: {r["title"]}\n'
                f'url: {r["url"]}\n'
                f'seccion: {r.get("section", "")} / {ruta}\n'
                f'texto:\n{body}\n'
                f'</articulo>'
            )
        (bdir / f"bundle-{count:03d}.txt").write_text("\n\n".join(parts),
                                                      encoding="utf-8")
    return count


def load_entries(args) -> list[dict]:
    if args.urls:
        raw = Path(args.urls).read_text(encoding="utf-8").splitlines()
        urls = [u.strip() for u in raw if u.strip() and not u.startswith("#")]
        return [{"slug": f"url-{i:04d}", "url": u, "title": u, "kind": "article",
                 "section": "", "path": []} for i, u in enumerate(urls, 1)]

    idx = ROOT / args.index
    if not idx.exists():
        raise SystemExit(f"error: falta {idx}. Corre antes scripts/parse_readme.py")
    return json.loads(idx.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", default="data/index.json")
    ap.add_argument("--urls", help="fichero con una URL por linea (en vez del indice)")
    ap.add_argument("--out-dir", default="extracted")
    ap.add_argument("--limit", type=int, help="procesar solo los N primeros")
    ap.add_argument("--only", help="filtrar por subcadena de la URL (p. ej. medium.com)")
    ap.add_argument("--concurrency", type=int, default=HTTP_CONCURRENCY)
    ap.add_argument("--no-browser", action="store_true",
                    help="omitir la pasada 2 (navegador)")
    ap.add_argument("--no-wayback", action="store_true",
                    help="omitir la pasada 3 (Wayback Machine)")
    ap.add_argument("--force", action="store_true", help="reextraer lo ya guardado")
    ap.add_argument("--bundle", type=int, metavar="N",
                    help="agrupar los textos en lotes de N articulos")
    ap.add_argument("--include-binaries", action="store_true",
                    help="intentar tambien video/pdf/slides (por defecto se omiten)")
    args = ap.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    store = Store(out_dir)
    entries = load_entries(args)

    skipped: list[dict] = []
    if not args.include_binaries:
        keep = []
        for e in entries:
            if e.get("kind") in SKIP_KINDS:
                skipped.append({
                    "slug": e["slug"], "title": e["title"], "url": e["url"],
                    "section": e.get("section", ""), "path": e.get("path", []),
                    "status": "skipped", "method": None, "chars": 0,
                    "http_status": None, "final_url": None,
                    "error": f"tipo {e['kind']}: sin texto que extraer",
                    "extracted_at": now(),
                })
            else:
                keep.append(e)
        entries = keep

    if args.only:
        entries = [e for e in entries if args.only in e["url"]]

    if not args.force:
        before = len(entries)
        entries = [e for e in entries
                   if not (out_dir / f"{e['slug']}.txt").exists()
                   or (out_dir / f"{e['slug']}.txt").stat().st_size < MIN_CHARS]
        if before - len(entries):
            print(f"reanudando: {before - len(entries)} ya extraidos, se omiten")

    # `is not None`: `--limit 0` es legitimo (no extraer nada, solo rearmar lotes).
    if args.limit is not None:
        entries = entries[:args.limit]

    for sk in skipped:
        if sk["slug"] not in store.records:
            store.records[sk["slug"]] = sk
            store.dirty += 1

    if not entries:
        print("nada que extraer")
        store.flush()
        # Aun sin trabajo nuevo, --bundle debe poder rearmar los lotes.
        if args.bundle and store.records:
            existing = sorted(store.records.values(), key=lambda m: m["slug"])
            n = write_bundles(out_dir, existing, args.bundle)
            print(f"{n} lotes regenerados en {out_dir.name}/bundles/")
        return 0

    by_slug = {e["slug"]: e for e in entries}
    t0 = time.monotonic()
    try:
        print(f"\n== pasada 1: HTTP plano sobre {len(entries)} enlaces ==")
        asyncio.run(pass_http(entries, args.concurrency, store))
        solved = store.solved()
        pending = [e for e in entries if e["slug"] not in solved]

        if pending and not args.no_browser:
            print(f"\n== pasada 2: navegador sobre {len(pending)} que fallaron ==")
            pass_browser(pending, store)
            solved = store.solved()
            pending = [e for e in pending if e["slug"] not in solved]

        if pending and not args.no_wayback:
            print(f"\n== pasada 3: Wayback sobre {len(pending)} que siguen sin texto ==")
            pass_wayback(pending, store)
    except KeyboardInterrupt:
        store.flush()
        print("\n! interrumpido. Lo extraido hasta ahora queda guardado: relanza "
              "el mismo comando para continuar donde iba.", file=sys.stderr)
        return 130
    finally:
        store.flush()

    manifest = sorted(store.records.values(), key=lambda m: m["slug"])

    if args.bundle:
        n = write_bundles(out_dir, manifest, args.bundle)
        print(f"\n{n} lotes en {out_dir.name}/bundles/ (de {args.bundle} articulos)")

    tally: dict[str, int] = defaultdict(int)
    for m in manifest:
        tally[m["status"]] += 1
    chars = sum(m["chars"] for m in manifest)
    print(f"\n== resultado ({time.monotonic() - t0:.0f}s) ==")
    for k in ("ok", "blocked", "dead", "poor", "error", "skipped"):
        if tally[k]:
            print(f"  {k:<8} {tally[k]:>4}")
    print(f"  {chars / 1_000_000:.2f}M caracteres en {out_dir.name}/")
    print(f"  manifiesto: {store.path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
