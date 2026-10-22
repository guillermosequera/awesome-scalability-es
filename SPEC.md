# SPEC — awesome-scalability-es (Fase 1)

**Estado:** borrador pendiente de aprobación
**Fecha:** 2026-10-20
**Upstream:** [binhnguyennus/awesome-scalability](https://github.com/binhnguyennus/awesome-scalability) · licencia MIT
**Cuenta GitHub destino:** `guillermosequera`

---

## 1. Contexto y objetivo

`awesome-scalability` es una lista curada de lectura sobre sistemas distribuidos a gran
escala: un único `README.md` con **923 enlaces** organizados en **12 secciones** de nivel
`##`. No existe traducción al español en ningún fork.

El objetivo de la Fase 1 es producir, sobre un fork propio, **cuatro artefactos
encadenados**:

1. una traducción mantenible del README (`README.es.md`),
2. un índice estructurado y verificado de los enlaces (`data/`),
3. resúmenes bilingües originales generados con la API de Claude (`data/articles/`),
4. un sitio estático navegable y buscable (`site/`), más la automatización que lo
   mantiene al día (`.github/workflows/sync.yml`).

Y, al cerrar la fase, un PR mínimo al repo original que solo añada el enlace a la
traducción.

### Fuera de alcance (Fase 1)

- Traducir los títulos de los artículos (son nombres propios de publicaciones).
- Alojar, copiar o versionar el texto completo de los artículos.
- Traducir `CONTRIBUTING.md` u otros ficheros del upstream.
- Buscador con backend, cuentas de usuario o comentarios.

---

## 2. Estructura real del README upstream (verificada)

Descargado y analizado el 2026-10-20 (`master`, 976 líneas, 124 KB):

| Elemento | Formato | Nº |
|---|---|---|
| Cabeceras de sección | `## Nombre` | 12 |
| Bloques de intro | `#### Nombre` + cita `>` | 5 |
| Índice de contenidos | `- [Nombre](#ancla)` | 11 |
| Ítems de primer nivel (subcategoría **con URL propia**) | `* [Texto](url)` | 210 |
| Entradas anidadas | `\t* [Título - Autor/Empresa](url)` | 673 |
| Entradas anidadas con sangría de 4 espacios (no tab) | `    * [...](url)` | ~24 |
| **Total de enlaces** | | **923** |

Secciones: `Content`, `Principle`, `Scalability`, `Availability`, `Stability`,
`Performance`, `Intelligence`, `Architecture`, `Interview`, `Organization`, `Talk`,
`A Piece of Cake`.

**Hallazgos que el parser y la traducción deben respetar:**

- Dos formas de entrada conviven: en `Principle` y `Talk` los ítems `* [...]` son
  artículos sueltos sin subcategoría; en `Scalability`…`Organization` los ítems
  `* [...]` son **subcategorías que además enlazan a un artículo de referencia** y
  llevan hijos indentados. El parser debe tratar el ítem de primer nivel como
  subcategoría **y** como enlace indexable.
- La sangría no es homogénea (tabs y 4 espacios). Normalizar por nivel, no por carácter.
- Hay URLs con espacio/tab final (p. ej. la entrada de Kubernetes at Quora). Limpiar.
- El índice upstream apunta a `#book`, un ancla **que no existe** (la sección se llama
  `A Piece of Cake`). En `README.es.md` el índice no reproducirá anclas muertas.
- `A Piece of Cake` es una nota personal del autor con un enlace de donación: se
  mantiene traducida y con el enlace intacto.
- El logo es una ruta relativa (`/logo.png`): válida en el fork, se conserva.

---

## 3. Requisitos

### R1 — Fork y rama

- **R1.1** Fork de `binhnguyennus/awesome-scalability` en la cuenta `guillermosequera`
  vía `gh repo fork`, conservando el historial y la licencia.
- **R1.2** Rama de trabajo `es` creada desde el `master` del fork. `master` queda limpio
  y sincronizable con upstream; todo el trabajo propio vive en `es`.
- **R1.3** Remotos: `origin` → fork, `upstream` → repo original.
- **R1.4** El `LICENSE` del upstream no se modifica. Los ficheros nuevos quedan cubiertos
  por la misma licencia MIT, y se añade una nota de atribución en `README.es.md` y en
  `REPORT.md`.

**Escenario:** `git remote -v` muestra ambos remotos; `git log --oneline -1 master`
coincide con el `HEAD` del upstream en el momento del fork.

### R2 — `README.es.md`

- **R2.1 Se traduce:** la frase de presentación, los 5 bloques `#### …` con sus citas,
  la nota de comunidad, el índice de contenidos, los títulos de las 12 secciones y los
  textos de las 210 subcategorías.
- **R2.2 NO se traduce:** el texto de los 673+ enlaces a artículos. Se conservan
  carácter a carácter, incluido el patrón ` - Autor, Empresa`.
- **R2.3** Las URLs son idénticas a las del upstream. Cero reescrituras.
- **R2.4 Anclas:** el índice usa anclas generadas en español por GitHub
  (`## Escalabilidad` → `#escalabilidad`). Todas las referencias cruzadas dentro de las
  citas (`[escalabilidad](#scalability)` → `#escalabilidad`) se reapuntan. Ninguna ancla
  del documento queda sin destino.
- **R2.5 Selector de idioma** en la primera línea, bajo el logo:
  `🇬🇧 [English](README.md) · 🇪🇸 **Español**`. Y el recíproco se añade a `README.md`
  **solo en la rama `es`** (el PR al upstream es independiente, ver R7).
- **R2.6 Crédito:** bloque visible al inicio indicando que es una traducción de la obra
  de Binh Nguyen, con enlace al repo original y mención de la licencia MIT.
- **R2.7 Glosario de consistencia** en `docs/glosario.md`: términos técnicos y su
  traducción acordada (o su decisión de dejarlos en inglés: *sharding*, *caching*,
  *rate limiting*, *load balancer*…). El traductor y la GitHub Action lo usan como
  referencia.

**Escenarios:**
- Un script de verificación compara el conjunto de URLs de `README.md` y `README.es.md`:
  deben ser idénticos en número y contenido → 923 == 923.
- Toda ancla `#...` interna de `README.es.md` resuelve a un encabezado existente.

### R3 — `scripts/parse_readme.py`

- **R3.1** Entrada: ruta a un README (por defecto `README.md`). Salida:
  `data/index.json`.
- **R3.2** Esquema por enlace:

```json
{
  "id": "sha1-12-de-la-url",
  "slug": "evcache-distributed-in-memory-caching-at-netflix",
  "section": "Scalability",
  "section_es": "Escalabilidad",
  "subcategory": "Distributed Caching",
  "subcategory_es": "Caching distribuido",
  "title": "EVCache: Distributed In-memory Caching at Netflix",
  "author": "Netflix",
  "url": "https://...",
  "kind": "article | video | pdf | slides",
  "level": 1,
  "line": 128
}
```

- **R3.3** `author` se extrae heurísticamente del propio título: sufijos ` at <X>`,
  ` - <Nombre>, <Cargo> at <X>`. Si no hay patrón reconocible, `author: null` (nunca
  inventado) y se registra en `data/parse_warnings.json`.
- **R3.4** `kind` se deduce del dominio y la extensión: `youtube|vimeo|…` → `video`,
  `.pdf` → `pdf`, `slideshare|speakerdeck` → `slides`, resto → `article`.
- **R3.5** `slug` único y estable; ante colisión se sufija con los primeros 6 caracteres
  del `id`.
- **R3.6** El parser es **idempotente** y determinista: misma entrada → mismo JSON byte
  a byte (claves ordenadas, `ensure_ascii=False`).
- **R3.7** Salida secundaria `data/index.es.json` con la misma estructura leída desde
  `README.es.md`, para validar que ambas versiones no se desincronizan.

**Escenario:** `python scripts/parse_readme.py` sobre el README real produce
`data/index.json` con 923 entradas y 0 warnings de URL malformada.

### R4 — `scripts/check_links.py`

- **R4.1** Comprobación asíncrona con `httpx.AsyncClient` (HTTP/2, `follow_redirects`),
  `timeout=15s`, 3 reintentos con backoff exponencial + jitter sobre errores de red,
  `429`, `5xx`.
- **R4.2** Educación con los sitios: concurrencia global 16 y **máximo 2 peticiones
  simultáneas por dominio**, con pausa mínima de 1 s entre peticiones al mismo dominio;
  se respeta `Retry-After`. User-Agent identificable con URL del proyecto.
- **R4.3** Estrategia por petición: `HEAD` primero; si devuelve `405/403/501` o falla,
  reintento con `GET` en streaming leyendo solo los primeros bytes.
- **R4.4** Estados: `ok` (2xx final sin cambio de URL), `redirect` (2xx final tras
  redirección; se guarda `final_url`), `dead` (4xx/5xx definitivo, DNS, TLS o timeout
  tras reintentos).
- **R4.5** Para cada `dead`, consulta a `https://archive.org/wayback/available?url=…`
  y, si hay snapshot, se guarda en `archive_url` (+ `archive_timestamp`). Si no hay,
  `archive_url: null`.
- **R4.6** Salida `data/links_status.json` con `checked_at`, y resumen agregado en
  `data/links_summary.json`. **Reanudable:** las entradas ya comprobadas en las últimas
  N horas (`--max-age`, por defecto 168) se saltan salvo `--force`.
- **R4.7** Flags: `--dry-run N`, `--only-dead`, `--concurrency`, `--max-age`, `--force`.
- **R4.8** Un enlace caído **nunca se borra** del índice ni del README: se marca. La
  decisión de retirarlo es humana.

**Escenarios:**
- Un dominio que responde `429` con `Retry-After: 2` provoca espera y reintento, no un
  `dead`.
- Un enlace muerto con snapshot en Wayback acaba con `status: "dead"` y `archive_url`
  poblado.
- Interrumpir el script y relanzarlo no repite el trabajo ya hecho.

### R5 — `scripts/extract_text.py` (sin IA)

**Decisión del 2026-10-21:** la generación de resúmenes **sale de la Fase 1**. Este
script solo scrapea y guarda texto plano; el resumen lo genera el usuario después, por
separado, con el modelo que elija (Haiku, Gemini, Grok…). Consecuencia: la Fase 1 **no
consume ni un token de IA en ningún punto**.

- **R5.1 Pipeline de tres pasadas**, cada una sobre lo que falló en la anterior. Las tres
  están medidas contra el corpus real, no supuestas:

  | Pasada | Medio | Para qué sirve | Medido |
  |---|---|---|---|
  | 1 | `httpx` + `trafilatura` | el grueso del corpus | 16/25 útiles |
  | 2 | Playwright Chromium | sitios que exigen JS o rechazan peticiones planas | +3/9 |
  | 3 | Wayback Machine (CDX API) | dominios que bloquean en firme | 5/6 |

- **R5.2 Pasada 1 — HTTP plano.** Concurrencia 8, un turno por dominio con 1,5 s de
  separación, `follow_redirects`, timeout 20 s, UA identificable con la URL del proyecto.
- **R5.3 Pasada 2 — navegador real.** Chromium headless, imágenes y fuentes abortadas por
  ruta (mucho más rápido), espera de 2,5 s tras `domcontentloaded`, 4 s entre peticiones al
  mismo dominio. Ante fallo **no se insiste en caliente**: se reencola al final y se
  triplica el enfriamiento de ese dominio, con techo de 20 s y un solo reintento.
- **R5.4 Pasada 3 — Wayback.** Vía **CDX API** (`web.archive.org/cdx/search/cdx`), no vía
  `/wayback/available`, que responde 429 con facilidad. Se prueban hasta 4 snapshots **de
  más antiguo a más nuevo**: el más reciente a menudo es la propia página de bloqueo
  archivada, mientras que los viejos son anteriores a los muros de pago. Se guardan
  `archive_url` y `archive_timestamp`, con lo que esta pasada cubre además el requisito
  R4.5.
- **R5.5 Salida** en `extracted/` (**en `.gitignore`**, ver R5.9):
  - `<slug>.txt` — texto limpio, UTF-8, sin cabeceras ni adornos.
  - `_manifest.json` — por enlace: `status`, `method`, `chars`, `http_status`,
    `final_url`, `archive_url`, `archive_timestamp`, `error`, `extracted_at`.
- **R5.6 Estados:** `ok` (≥ 800 caracteres), `blocked` (401/403/429), `dead` (404/410),
  `poor` (200 pero sin contenido útil, p. ej. una portada), `error`, `skipped`.
- **R5.7 Vídeos, PDF y slides se omiten** por defecto (`kind` en `{video, pdf, slides}`):
  no hay texto HTML que extraer. Quedan en el manifiesto con `status: "skipped"` y su
  motivo. `--include-binaries` los intenta igualmente.
- **R5.8 Reanudable:** salta los `<slug>.txt` que ya existen con tamaño suficiente, y el
  manifiesto se fusiona en vez de sobrescribirse. `--force` reextrae. Flags: `--limit`,
  `--only <subcadena>`, `--concurrency`, `--no-browser`, `--no-wayback`, `--urls <fichero>`
  (para trabajar sobre una lista arbitraria sin pasar por el índice).
- **R5.9 Copyright.** Los textos extraídos son de sus autores: sirven como insumo local y
  **no se versionan ni se publican**. `extracted/` va en `.gitignore`. El repo publica
  índice, estados, enlaces y resúmenes originales; nunca el texto fuente.
- **R5.10 Entrega para el resumen.** `--bundle N` agrupa los textos útiles en
  `extracted/bundles/bundle-NNN.txt`, cada artículo envuelto en `<articulo slug=…>` con
  título, URL y ruta de taxonomía. Son ficheros de texto plano listos para pasárselos a
  cualquier modelo, por API propia, por web o por CLI. El esquema de ficha que se espera de
  vuelta (`summary_es`, `summary_en`, `key_takeaways_*`, `tags`) queda documentado en
  `docs/formato-ficha.md` para que las fichas encajen en el sitio sea quien sea el que las
  genere.
- **R5.11 Rendimiento esperado** (extrapolado de lo medido): pasada 1 ≈ 3 min para 861
  artículos; pasada 2 ≈ 10 s por enlace sobre el ~35 % que falla; pasada 3 ≈ 5 s por
  enlace. Total estimado **1,5 a 2,5 horas** para el corpus completo, una sola vez, con
  reanudación si se interrumpe.
- **R5.12 Encoding.** UTF-8 explícito en toda la E/S. No se imprime el texto extraído por
  stdout: la consola de Windows es cp1252 y corrompe los acentos.

**Escenarios:**
- `python scripts/extract_text.py --limit 25` deja 19 `.txt` y un manifiesto que explica
  los 6 que no (verificado 2026-10-21).
- Interrumpir y relanzar no repite lo ya extraído.
- `git status` no muestra nunca ficheros de `extracted/`.
- `grep -rn "anthropic\|openai\|ANTHROPIC_API_KEY" scripts/` no devuelve nada.

### R6 — `site/`

- **R6.1** Sitio estático con **Astro** en `site/`, en modo totalmente estático
  (`output: 'static'`, sin adaptador de servidor). Consume `data/index.json` +
  `data/articles/*.json` compactados en un único `site/src/data/search-index.json`
  generado por `scripts/build_site_data.py`. El build (`astro build`) produce
  `site/dist/`, que **no se commitea**: lo publica la Action de Pages (R6.6).
- **R6.2** Búsqueda en cliente por texto libre y **filtros combinables** por: patrón,
  empresa, tecnología, sección e idioma del resumen. Filtro adicional por estado del
  enlace (vivo / recuperado de archivo).
- **R6.3** Cada resultado muestra título original (sin traducir), subcategoría en
  español, resumen en el idioma activo, bullets, tags, enlace al original y, si aplica,
  enlace al snapshot de archivo.
- **R6.4** Accesible (navegación por teclado, contraste AA), responsive desde 360 px,
  y funcional sin JS para la vista de índice básica.
- **R6.5** Sin dependencias de CDN de terceros en runtime: todo el JS y las fuentes se
  sirven desde el propio despliegue. Dependencias de Astro fijadas con `package-lock.json`
  y versiones exactas.
- **R6.6** Despliegue con `.github/workflows/pages.yml` (`actions/configure-pages`,
  `upload-pages-artifact`, `deploy-pages`) disparado al tocar `site/` o `data/` en la
  rama `es`. `site.base` configurado para la ruta de Pages del fork.

**Escenario:** `npm run dev` en `site/` permite filtrar por `caching` + `Netflix` y
obtener resultados en < 100 ms; `npm run build` genera `dist/` sin errores.

### R7 — `.github/workflows/sync.yml`

- **R7.1** Disparadores: `schedule` semanal (lunes 06:00 UTC) y `workflow_dispatch`.
- **R7.2** Pasos: sincronizar `master` con `upstream/master` → parsear el README nuevo →
  **diff contra `data/index.json`** → si no hay enlaces nuevos, terminar sin hacer nada.
- **R7.3** Si hay enlaces nuevos: comprobarlos (`check_links.py --only-new`), regenerar
  `search-index.json`, verificar que `astro build` sigue pasando y **abrir un PR
  automático** contra la rama `es` con un cuerpo que lista los enlaces nuevos, los que han
  muerto desde la última pasada, y **la lista de slugs pendientes de resumir**. El
  despliegue a Pages lo hace `pages.yml` al mergear, no esta Action.
- **R7.4 La Action no genera resúmenes.** Consecuencia directa de la regla de cero
  créditos: GitHub Actions no tiene acceso a la sesión de Claude Code del usuario, y usar
  una API key está descartado. El runner ejecuta solo los pasos deterministas (parse,
  check, build). `summarize.py` se corre **en local**, cuando el usuario quiera, sobre los
  pendientes que el PR enumera. El sitio tolera fichas sin resumen: se muestran con título,
  sección y tags deterministas.
- **R7.5** Nunca hace push directo a `es`. **No hay ningún secreto de API en el repo.**
  Permisos mínimos (`contents: write`, `pull-requests: write`).
- **R7.6** Tope `--max-new` (por defecto 50) en los pasos deterministas, para que un cambio
  masivo en upstream no dispare una verificación de miles de URLs en el runner.

### R8 — Tests

- **R8.1** `pytest` con fixtures de un README mínimo que reproduzca los casos reales:
  sangría con tabs y con espacios, ítem de primer nivel con hijos, ítem suelto, URL con
  espacio final, título sin autor reconocible.
- **R8.2** `check_links.py` se testea con transporte simulado de `httpx`
  (`MockTransport`): 200, 301→200, 404, 429 con `Retry-After`, timeout, y respuesta de
  Wayback con y sin snapshot. **Cero red real en los tests.**
- **R8.3** `summarize.py` se testea con un cliente de Claude falso: se verifica el
  esquema de salida, el salto de ya-procesados, el modo `metadata_only` y el detector
  de copia literal.
- **R8.4** Test de integridad `README.md` ↔ `README.es.md` (conjunto de URLs idéntico,
  anclas resueltas).

### R9 — `REPORT.md`

Generado por `scripts/report.py` a partir de `data/`, con: total de enlaces, vivos,
redirigidos, caídos, caídos **recuperados** vía Wayback y no recuperables; tabla de
artículos por patrón, por empresa y por sección; cobertura de resúmenes; coste real
consumido en la API; y una lista explícita de los enlaces muertos sin archivo, como
candidatos a PR en el upstream.

### R10 — PR al repositorio original

- **R10.1** Rama dedicada `add-spanish-translation-link` desde un `master` limpio y
  sincronizado, con **un único commit** que toca **solo `README.md`**: ni scripts, ni
  `data/`, ni `site/`, ni `README.es.md`.
- **R10.2** El cambio es una línea en la cabecera, con el formato habitual de las
  *awesome lists*:
  `🇪🇸 [Spanish translation](https://github.com/guillermosequera/awesome-scalability-es/blob/es/README.es.md)`
- **R10.3** Cuerpo del PR: breve, en inglés, explicando que la traducción se mantiene en
  un fork, que respeta la licencia MIT y la atribución, y que no se han traducido los
  títulos de los artículos.
- **R10.4 Se abre solo con tu confirmación explícita.** Es una acción pública sobre un
  repo de tercero; no se envía sin tu OK en ese momento.

---

## 4. Estructura de ficheros resultante (rama `es`)

```
README.md                  (upstream + línea de selector de idioma)
README.es.md               (nuevo)
LICENSE                    (intacto)
SPEC.md  PLAN.md  REPORT.md
docs/glosario.md
scripts/
  parse_readme.py  check_links.py  extract_text.py
  build_site_data.py  report.py
  taxonomy/sections.yml  taxonomy/patterns.yml
  tests/  conftest.py  test_*.py  fixtures/
data/
  index.json  index.es.json
  links_status.json  links_summary.json
  parse_warnings.json
  articles/<slug>.json          (fichas; las genera el usuario aparte)
extracted/                      NO VERSIONADO (.gitignore)
  <slug>.txt  _manifest.json  bundles/bundle-NNN.txt
docs/glosario.md  docs/formato-ficha.md
site/
  package.json  package-lock.json  astro.config.mjs
  src/pages/index.astro  src/components/  src/data/search-index.json
  public/
.github/workflows/sync.yml  .github/workflows/pages.yml
pyproject.toml  .gitignore
```

`.gitignore` excluye `.cache/`, `.venv/`, `__pycache__/`, `site/node_modules/`,
`site/dist/`, `site/.astro/` y cualquier volcado de texto extraído.

---

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Copiar texto con copyright en los resúmenes | Extracción solo en memoria (R5.1) + detector de n-gramas literales (R5.3) + `.gitignore` |
| Gasto inesperado de créditos de API | Imposible por diseño: ningún script invoca modelo alguno. Test que falla si aparece una importación de SDK (R5 escenarios) |
| Dominios que bloquean el scraping (Medium es el 23 % del corpus) | Pipeline de 3 pasadas. Medido: 10/10 en el conjunto de Medium gracias a Wayback (R5.1) |
| Textos con copyright acabando en el repo público | `extracted/` en `.gitignore` desde el primer commit; el repo nunca publica texto fuente (R5.9) |
| Enlaces que se caen con el tiempo | `check_links.py` semanal + Wayback en `archive_url`; nunca se borra, se marca |
| Bloqueo o rate-limit al verificar 923 URLs | 2 peticiones/dominio, 1 s de separación, `Retry-After`, backoff (R4.2) |
| Desincronización README ↔ README.es | `index.es.json` + test de integridad (R3.7, R8.4) |
| Traducción inconsistente entre pasadas | `docs/glosario.md` como referencia obligatoria |
| El autor upstream rechaza el PR | El PR es mínimo (una línea, un fichero) y la traducción es útil igualmente en el fork |
| Rutas largas / OneDrive en Windows | `git config core.longpaths true`; `data/articles/` con slugs acotados a 80 caracteres |

---

## 6. Decisiones tomadas (2026-10-20)

1. **Fork (R1.1):** `awesome-scalability-es`, **público**. Público es además requisito
   para GitHub Pages sin plan de pago.
2. **Sitio (R6.1):** **Astro** en modo estático, con despliegue vía Action de Pages.
3. **PR upstream (R10.2):** una línea que apunta al `README.es.md` **del fork**.
4. **Generación de resúmenes: fuera de la Fase 1.** `extract_text.py` solo scrapea y
   deja texto plano en `extracted/`, mas lotes listos con `--bundle N`. El resumen lo
   genera el usuario por su cuenta, con el modelo que prefiera. La Fase 1 **no consume
   ningún token de IA**.

### Nota de facturación

**Coste de IA de la Fase 1: cero.** Ningún script invoca modelo alguno. El único coste es
tiempo de red: 1,5 a 2,5 horas de scraping, una sola vez (R5.11).

El resumen posterior queda en manos del usuario y fuera de este alcance. Como referencia,
si lo hiciera con la API de Anthropic sobre los textos ya extraídos (~8 K tokens de entrada
y ~0,7 K de salida por artículo), serían ≈1 USD con `claude-haiku-5-5`, ≈21 con
`claude-sonnet-5-5` y ≈41 con `claude-opus-5-5`, a la mitad con la Batches API. Pero la
elección de modelo y de proveedor es suya, y `docs/formato-ficha.md` documenta el esquema
de salida para que cualquiera de ellos encaje en el sitio.

## 7. Criterios de aceptación de la Fase 1

- [ ] Fork creado, rama `es`, remotos `origin` y `upstream` configurados.
- [ ] `README.es.md` con 923 URLs idénticas al original, títulos de artículos sin
      traducir, todas las anclas resueltas, selector de idioma, crédito y licencia.
- [ ] `data/index.json` con 923 entradas y 0 warnings de URL malformada.
- [ ] `data/links_status.json` con los 923 clasificados y `archive_url` en los `dead`
      recuperables.
- [ ] `extracted/` con el texto de los artículos recuperables y un `_manifest.json` que
      explique cada fallo; nada de ello versionado.
- [ ] `extracted/bundles/` con los lotes listos para que el usuario genere las fichas.
- [ ] Cero tokens de IA consumidos: `grep -rn "anthropic\|openai" scripts/` sin resultados.
- [ ] `site/` (Astro) compila sin errores, filtra por patrón, empresa, tecnología e
      idioma, y `pages.yml` lo despliega en GitHub Pages.
- [ ] `sync.yml` ejecutado a mano (`workflow_dispatch`) abre un PR o termina
      correctamente sin cambios.
- [ ] `pytest` en verde.
- [ ] `REPORT.md` con las estadísticas pedidas.
- [ ] PR al upstream preparado, de un solo fichero y una sola línea, pendiente de tu OK.
