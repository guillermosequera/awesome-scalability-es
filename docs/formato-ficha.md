# Formato de ficha

Este documento define qué espera el sitio de cada artículo resumido. El resumen lo genera
quien quiera, con el modelo que quiera (Claude, Gemini, Grok, uno local…): mientras la
salida respete este esquema, encaja.

## De dónde salen los textos

`scripts/extract_text.py` deja el texto limpio de cada artículo en `extracted/<slug>.txt`
y, con `--bundle N`, agrupa los útiles en `extracted/bundles/bundle-NNN.txt`. Cada lote
contiene N artículos con esta forma:

```
<articulo slug="operate-kubernetes-reliably-at-stripe">
titulo: Operate Kubernetes Reliably at Stripe
url: https://stripe.com/blog/operating-kubernetes
seccion: Scalability / Microservices and Orchestration
texto:
...el texto completo del articulo...
</articulo>
```

El `slug` es la clave: es lo que amarra la ficha con la entrada de `data/index.json`.

## Esquema de salida

Un fichero por artículo en `data/articles/<slug>.json`:

```json
{
  "slug": "operate-kubernetes-reliably-at-stripe",
  "schema_version": 1,
  "summary_es": "Stripe explica cómo construyó un planificador...",
  "summary_en": "Stripe describes how it built a scheduler...",
  "key_takeaways_es": [
    "Definir SLOs concretos antes de discutir fiabilidad.",
    "Montar el clúster a mano permite integrarlo con la infraestructura existente."
  ],
  "key_takeaways_en": [
    "Set concrete SLOs before discussing reliability.",
    "Building the cluster by hand allows deeper integration."
  ],
  "tags": {
    "patterns": ["orchestration"],
    "technologies": ["Kubernetes", "Chronos", "Puppet"],
    "company": "Stripe",
    "year": 2016
  },
  "model": "claude-haiku-5-5",
  "generated_at": "2026-10-22T03:10:00Z",
  "source": "full_text",
  "needs_review": false
}
```

### Campos

| Campo | Tipo | Regla |
|---|---|---|
| `slug` | string | Idéntico al del lote y al de `data/index.json`. |
| `schema_version` | int | `1` por ahora. Sirve para reprocesar si el esquema cambia. |
| `summary_es` | string | **Máximo 150 palabras.** Redacción original. |
| `summary_en` | string | Ídem, en inglés. |
| `key_takeaways_es` | array | 3 a 5 bullets, concretos y técnicos. |
| `key_takeaways_en` | array | Ídem, en inglés. |
| `tags.patterns` | array | Solo del vocabulario controlado (abajo). |
| `tags.technologies` | array | Nombres propios citados en el texto. |
| `tags.company` | string \| null | Empresa del caso de estudio. `null` si no aplica. |
| `tags.year` | int \| null | Año de publicación si se deduce del texto. **`null` si no.** |
| `model` | string | Qué modelo lo generó. Para poder auditar la calidad por lotes. |
| `generated_at` | string | ISO 8601 UTC. |
| `source` | string | `full_text` o `metadata_only` (vídeos, PDF y slides). |
| `needs_review` | bool | `true` si el resultado es dudoso. |

### Vocabulario controlado de `patterns`

Cerrado a propósito: si cada modelo inventa sus etiquetas, los filtros del sitio se
vuelven inútiles.

```
caching        sharding       rate-limiting   replication
load-balancing consensus      cdn             message-queue
observability  microservices  orchestration   database
storage        networking     security        testing
```

## Dos reglas que no son negociables

**1. Redacción original.** El resumen se publica en un repo público: no puede reproducir
frases del artículo. Criterio operativo: **ninguna secuencia de 8 o más palabras
consecutivas** del resumen debe aparecer literal en el texto fuente. Si tu proceso no lo
comprueba, marca `needs_review: true` y se valida después.

**2. No inventar.** Si el año, la empresa o un dato no están en el texto, el campo va a
`null`. Un `null` honesto es útil; un dato inventado contamina el índice.

## Prompt de referencia

Validado el 2026-10-21 con `claude-haiku-5-5`, que devolvió JSON estricto y utilizable.
Sirve igual para cualquier otro modelo:

```
Eres un indexador tecnico. Para CADA bloque <articulo>, produce una ficha.

Reglas estrictas:
- summary_es y summary_en: maximo 150 palabras, REDACCION ORIGINAL. Parafrasea con
  tus propias palabras. Prohibido reutilizar cualquier secuencia de 8+ palabras
  consecutivas del texto fuente.
- key_takeaways_es / key_takeaways_en: 3 a 5 bullets, concretos y tecnicos.
- tags.patterns: solo de este vocabulario: caching, sharding, rate-limiting,
  replication, load-balancing, consensus, cdn, message-queue, observability,
  microservices, orchestration, database, storage, networking, security, testing.
- tags.technologies: nombres propios de tecnologias citadas.
- tags.company: la empresa del caso de estudio, o null.
- tags.year: año de publicacion si se deduce del texto, o null.
- No inventes datos que no esten en el texto.

Responde UNICAMENTE con un array JSON, sin markdown ni texto alrededor:
[{"slug": "...", "summary_es": "...", "summary_en": "...",
  "key_takeaways_es": ["..."], "key_takeaways_en": ["..."],
  "tags": {"patterns": ["..."], "technologies": ["..."], "company": "...", "year": 2017}}]
```

## Validación

`scripts/validate_articles.py` (pendiente) comprobará esquema, longitud de los resúmenes,
vocabulario de `patterns`, correspondencia de `slug` con el índice y ausencia de copia
literal. Las fichas que no pasen quedan fuera del sitio hasta corregirse.
