# PLAN — awesome-scalability-es (Fase 1)

Plan de implementación de [SPEC.md](SPEC.md). **Pendiente de tu OK.**
Cada etapa termina en un commit verificable. Las etapas 2–7 son secuenciales en
dependencias de datos pero el código de 3, 4 y 5 se puede escribir en paralelo.

---

## Etapa 0 — Preparación del repo (≈10 min)

| # | Tarea | Verificación |
|---|---|---|
| 0.1 | `gh repo fork binhnguyennus/awesome-scalability --fork-name awesome-scalability-es --clone=false` (público) | el repo aparece en tu cuenta |
| 0.2 | El directorio **ya no está vacío** (`SPEC.md`, `PLAN.md`), así que `git clone` fallaría: en su lugar `git init` + `git remote add origin` + `git fetch origin` + `git checkout -B master origin/master` | `git log -1` == HEAD de upstream, y `SPEC.md`/`PLAN.md` siguen presentes sin commitear |
| 0.3 | `git remote add upstream …` y `git config core.longpaths true` | `git remote -v` muestra los dos |
| 0.4 | `git switch -c es` | rama activa `es` |
| 0.5 | `pyproject.toml` (httpx[http2], trafilatura, anthropic, pyyaml, pytest, pytest-asyncio, respx), `.gitignore`, venv | `pytest --version` dentro del venv |
| 0.5b | Scaffold de Astro en `site/` (`npm create astro`, modo estático, versiones fijadas) | `npm run build` en verde con una página vacía |
| 0.6 | Commit `chore: bootstrap SDD (spec, plan, tooling)` con `SPEC.md` + `PLAN.md` + tooling | — |

**Acción irreversible:** 0.1 crea un repo **público** en tu cuenta, como decidiste.

---

## Etapa 1 — `scripts/parse_readme.py` + tests (R3, R8.1)

| # | Tarea |
|---|---|
| 1.1 | Fixtures en `scripts/tests/fixtures/`: README mínimo con tabs, 4 espacios, ítem con hijos, ítem suelto, URL con espacio final, título sin autor |
| 1.2 | Parser por máquina de estados sobre líneas: `## ` → sección; `* [` → nivel 1; sangría → nivel 2. Normaliza sangría, limpia URLs, deduce `kind`, extrae `author`, genera `slug`/`id` |
| 1.3 | Tabla de traducción de secciones y subcategorías en `scripts/taxonomy/sections.yml` (fuente única para parser, README.es y sitio) |
| 1.4 | Volcado determinista a `data/index.json`; warnings a `data/parse_warnings.json` |
| 1.5 | Tests: 12 secciones, 923 enlaces, idempotencia byte a byte, casos raros |

**Puerta de calidad:** `python scripts/parse_readme.py` → 923 entradas, 0 warnings de URL
malformada. Si el recuento no cuadra, se investiga antes de seguir.

---

## Etapa 2 — `README.es.md` + glosario (R2)

| # | Tarea |
|---|---|
| 2.1 | `docs/glosario.md`: decisiones de traducción (qué se traduce, qué se queda en inglés) |
| 2.2 | Traducir intro, 5 bloques `####` con sus citas, nota de comunidad, 12 secciones y 210 subcategorías. Los 673+ títulos de artículo se copian intactos |
| 2.3 | Índice con anclas españolas; reapuntar las referencias cruzadas de las citas; sin anclas muertas (el `#book` del upstream no se reproduce) |
| 2.4 | Selector `🇬🇧/🇪🇸` arriba en ambos README (solo en la rama `es`), bloque de crédito a Binh Nguyen y nota de licencia MIT |
| 2.5 | `scripts/tests/test_readme_parity.py`: conjunto de URLs idéntico y anclas resueltas |

**Puerta de calidad:** paridad 923 == 923 y `pytest` en verde. Esta etapa es la única con
traducción manual masiva; la reviso sección a sección antes de commitear.

---

## Etapa 3 — `scripts/check_links.py` + tests (R4, R8.2)

| # | Tarea |
|---|---|
| 3.1 | Cliente `httpx` asíncrono: HTTP/2, `follow_redirects`, timeout 15 s, UA identificable |
| 3.2 | Limitador por dominio (semáforo de 2 + 1 s de separación) sobre un cap global de 16; respeto de `Retry-After` |
| 3.3 | Reintentos (3, backoff exponencial + jitter) para red, 429 y 5xx; `HEAD` → fallback `GET` en streaming |
| 3.4 | Clasificación `ok` / `redirect` / `dead` con `final_url` |
| 3.5 | Consulta a Wayback para los `dead` → `archive_url` + `archive_timestamp` |
| 3.6 | Persistencia reanudable (`--max-age`, `--force`) y flags `--dry-run N`, `--only-dead`, `--only-new`, `--concurrency` |
| 3.7 | Tests con `MockTransport`: 200, 301→200, 404, 429 con `Retry-After`, timeout, Wayback con y sin snapshot. Cero red real |

**Puerta de calidad:** `--dry-run 10` sobre URLs reales se comporta; tests en verde.
Después, pasada completa de las 923 (≈15–25 min de reloj).

---

## Etapa 4 — `scripts/extract_text.py` (sin IA) · **YA IMPLEMENTADO Y VALIDADO**

Hecho el 2026-10-21. Pipeline de tres pasadas, cada una medida contra el corpus real:

| # | Tarea | Estado |
|---|---|---|
| 4.1 | Pasada 1: `httpx` async + `trafilatura`, concurrencia 8, 1,5 s por dominio | hecho — 16/25 en muestra |
| 4.2 | Pasada 2: Playwright Chromium, assets abortados, reencolado con enfriamiento | hecho — +3/9 |
| 4.3 | Pasada 3: Wayback vía CDX API, 4 snapshots de viejo a nuevo | hecho — **10/10 en Medium** |
| 4.4 | Manifiesto con `status`/`method`/`chars`/`archive_url`/`error` | hecho |
| 4.5 | Reanudación, `--limit`, `--only`, `--force`, `--no-browser`, `--no-wayback`, `--urls` | hecho |
| 4.6 | `--bundle N` → lotes de texto listos para cualquier modelo | hecho |
| 4.7 | `extracted/` en `.gitignore` desde el primer commit | hecho |
| 4.8 | `docs/formato-ficha.md`: esquema de ficha esperado, para que las fichas encajen en el sitio venga el resumen de donde venga | pendiente |
| 4.9 | Tests: fixtures HTML locales, clasificación de estados, reanudación, selección de snapshot. Cero red real | pendiente |
| 4.10 | Pasada completa sobre los 861 artículos (1,5–2,5 h, reanudable) | pendiente |

**El resumen queda fuera de la Fase 1.** Lo genera el usuario con el modelo que elija a
partir de `extracted/bundles/`.

## Etapa 5 — Datos del sitio y `site/` (R6)

| # | Tarea |
|---|---|
| 5.1 | `scripts/build_site_data.py`: fusiona `index.json` + `links_status.json` + `articles/*.json` en `site/src/data/search-index.json` compacto, con facetas precalculadas |
| 5.2 | Componentes Astro: cabecera con selector de idioma, buscador, panel de facetas, tarjeta de resultado. Página estática con el índice completo renderizado en build |
| 5.3 | Isla de cliente para la búsqueda: índice invertido ligero, filtros combinables (patrón, empresa, tecnología, sección, idioma, estado), estado en la URL para compartir búsquedas |
| 5.4 | Accesibilidad (teclado, contraste AA, `prefers-color-scheme`), responsive 360 px; el índice renderizado en build sigue siendo navegable sin JS |
| 5.5 | `.github/workflows/pages.yml`: build de Astro y despliegue a Pages desde la rama `es`; `site.base` ajustado a la ruta del fork |

**Puerta de calidad:** `npm run build` sin errores y filtrar `caching` + `Netflix`
responde en < 100 ms sobre el dataset real; sin dependencias de CDN en runtime.

---

## Etapa 6 — `.github/workflows/sync.yml` (R7)

| # | Tarea |
|---|---|
| 6.1 | Job semanal + `workflow_dispatch`; permisos mínimos; `ANTHROPIC_API_KEY` desde secrets |
| 6.2 | Sync de `master` con upstream → parse → diff contra `data/index.json` → salida temprana si no hay novedades |
| 6.3 | Con novedades: `check_links --only-new`, `build_site_data`, `astro build` como verificación, `report`. Sin resumen y sin scraping masivo en el runner |
| 6.4 | PR automático contra `es` con enlaces nuevos, recién caídos y **slugs pendientes de extraer y resumir en local**. Nunca push directo |
| 6.5 | Ejecución manual de prueba |

---

## Etapa 7 — `REPORT.md` y cierre (R9)

| # | Tarea |
|---|---|
| 7.1 | `scripts/report.py` → `REPORT.md`: vivos / redirigidos / caídos / recuperados / no recuperables, artículos por patrón, empresa y sección, cobertura de resúmenes, coste real, lista de muertos sin archivo |
| 7.2 | Repaso de los criterios de aceptación de la SPEC, uno a uno |
| 7.3 | `pytest` completo + verificación de que no hay texto fuente en el repo |

---

## Etapa 8 — PR al repositorio original (R10) · **requiere tu OK en el momento**

| # | Tarea |
|---|---|
| 8.1 | `git switch master && git fetch upstream && git merge --ff-only upstream/master` |
| 8.2 | Rama `add-spanish-translation-link`, un commit, **solo `README.md`**, una línea con el enlace a la traducción en tu fork |
| 8.3 | Verificar el diff: `git diff upstream/master --stat` debe mostrar exactamente `README.md | 1 +` |
| 8.4 | Preparar título y cuerpo del PR en inglés y **enseñártelos**. Lo abro solo cuando digas que sí |

---

## Resumen de dependencias

```
0 ──► [1 hecho] ──► 2 ───────────────┐
         │                            ├──► 7 ──► 8
         └──► 3 ──► [4 hecho] ──► 5 ──► 6 ──┘
```
Las etapas 1 y 4 se implementaron antes que la 0 porque validarlas contra el corpus real
era lo que decidía el diseño. Se commitean en cuanto exista el repo.

## Decisiones ya tomadas

Fork `awesome-scalability-es` público · sitio en **Astro** estático · PR upstream con una
línea al `README.es.md` del fork · **cero IA en la Fase 1**: `extract_text.py` solo scrapea
y entrega texto plano en lotes; el resumen lo genera el usuario aparte con el modelo que
quiera.

## Lo que necesito de ti

- **Ahora:** el OK para arrancar la etapa 0 (es donde se crea el repo público). Las etapas
  1 y 4 ya están implementadas y validadas contra el corpus real; esperan commit.
- **Antes de la etapa 4.10:** luz verde para la pasada completa de scraping (1,5–2,5 h de
  red, sin coste).
- **En la etapa 8:** el OK para abrir el PR en el repo de Binh Nguyen.

Ninguna etapa consume tokens de IA. Dependencias: Python 3.13 (ok), `playwright` con
Chromium (instalado, 118 MB), Node para Astro.
