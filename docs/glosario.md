# Glosario y criterios de traducción

Las traducciones concretas viven en `scripts/taxonomy/` (`sections.yml`,
`nodos_es.yml`, `prosa_es.yml`). Este documento explica **por qué** cada cosa se
traduce o no, para que futuras aportaciones sean coherentes con lo ya hecho.

## Qué no se traduce

**Los títulos de los artículos.** Son nombres de publicaciones: *"EVCache: Distributed
In-memory Caching at Netflix"* es el nombre de ese artículo, igual que no se traduce el
título de un libro al citarlo. Verificado automáticamente: los 864 coinciden byte a byte
con el README en inglés.

**Las URLs.** Ni una reescritura. El generador aborta si el conjunto de URLs de la versión
española no es idéntico al del original.

**Los nombres propios de tecnologías.** Cassandra, HBase, Kafka, Redshift, Druid, Presto,
el stack ELK y Airflow conservan su nombre; solo se traduce la descripción que los
acompaña: *"Kafka - Message Broker"* → *"Kafka — broker de mensajes"*.

## Términos que se dejan en inglés

Son los que cualquiera que trabaje en el oficio usa en inglés a diario. Traducirlos
dificulta la lectura en vez de facilitarla:

| Se queda | Por qué no se traduce |
|---|---|
| *caching* | "Almacenamiento en caché" es correcto pero nadie lo dice. |
| *sharding* | Se acompaña de "(particionado)" la primera vez. |
| *rate limiting* | Se acompaña de "(limitación de tasa)". |
| *streaming* | Sin equivalente breve que se use. |
| *big data*, *deep learning* | Nombres de campo establecidos. |
| *failover* | Se acompaña de "(conmutación por error)". |
| *circuit breaker* | Se acompaña de "(cortacircuitos)". |
| *timeout* | Se acompaña de "(tiempo de espera)". |
| *pub-sub* | Nombre del patrón. |
| *broker*, *stack*, *framework* | Uso corriente en el oficio. |

El criterio: **término en inglés + aclaración entre paréntesis la primera vez**. Así el
lector que no conoce el término aprende el equivalente, y el que sí lo conoce no tropieza.

## Términos que sí se traducen

| Inglés | Español |
|---|---|
| Load Balancing | Balanceo de carga |
| Replication | Replicación |
| Autoscaling | Autoescalado |
| Distributed Locking | Bloqueo distribuido |
| Key-Value Databases | Bases de datos clave-valor |
| Columnar Databases | Bases de datos columnares |
| Time Series Databases | Bases de datos de series temporales |
| Object Storage | Almacenamiento de objetos |
| In-memory Storage | Almacenamiento en memoria |
| Code Review | Revisión de código |
| Monitoring and Alerting | Monitorización y alertas |
| Machine Learning | Aprendizaje automático |
| Garbage Collection | Recolector de basura |
| OS | SO |

## Anclas internas

Los títulos de sección traducidos cambian las anclas que genera GitHub:
`## Escalabilidad` → `#escalabilidad`. Todas las referencias internas se reapuntan, y el
generador falla si alguna queda sin destino.

Las tildes y las eñes se conservan en las anclas: `## Organización` → `#organización`.
GitHub lo soporta.

Un detalle heredado: el índice del README original apunta a `#book`, un ancla que **no
existe** (la sección se llama *A Piece of Cake*). En la versión española el índice se
regenera desde la lista de secciones, así que ese enlace roto no se reproduce.

## Cómo añadir o corregir una traducción

1. Edita el YAML correspondiente en `scripts/taxonomy/`.
2. Regenera: `python scripts/build_readme_es.py --patch-en`.
3. El script verifica solo la paridad de URLs y las anclas. Si algo falla, aborta sin
   escribir.

No edites `README.es.md` a mano: se regenera y perderías el cambio.
