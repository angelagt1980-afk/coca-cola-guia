# COCA-COLA GUÍA

Asistente conversacional de trámites, políticas, beneficios y servicios corporativos para **The Coca-Cola Company**. Responde dudas de colaboradores, proveedores y usuarios a partir de un catálogo en texto plano que mantiene el equipo administrativo, con un consumo de tokens mínimo y acotado por usuario.

![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Gradio](https://img.shields.io/badge/Gradio-6.30-F40009)
![Deploy](https://img.shields.io/badge/deploy-Render-46E3B7)

## Contenido

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Inicio rápido](#inicio-rápido)
- [Configuración](#configuración)
- [Catálogo (corpus)](#catálogo-corpus)
- [Administración](#administración)
- [API HTTP](#api-http)
- [Pruebas y calidad](#pruebas-y-calidad)
- [Despliegue en Render](#despliegue-en-render)
- [Seguridad y privacidad](#seguridad-y-privacidad)
- [Limitaciones conocidas](#limitaciones-conocidas)

## Características

- **Catálogo como fuente de verdad.** Toda la información corporativa vive en `data/corpus.txt`. Agregar conocimiento (Recursos Humanos, Beneficios, Abastecimiento, Calidad, Sostenibilidad, TI) es agregar una ficha, no cambiar código.
- **Coste de tokens mínimo.** La IA es el último recurso: la mayoría de las consultas se resuelven con búsqueda local y no gastan tokens.
- **Sin datos inventados.** Horarios, teléfonos, extensiones, correos y ubicaciones se toman siempre de la ficha, nunca los redacta el modelo. Si un dato no está registrado, la aplicación lo indica.
- **Límites de uso.** Cupos por consulta, por usuario y por día, y un tope global, con degradación a respuesta directa en lugar de error.
- **Conversación fluida.** Respuestas al punto, preguntas de seguimiento y respuesta en streaming.
- **Mejora continua.** Los usuarios pueden informar cuando falta información; el administrador convierte esos informes en nuevas fichas.
- **Panel de administración** con editor del catálogo, importación de documentos asistida por IA y publicación en GitHub.
- **Interfaz corporativa profesional** con la identidad visual y paleta oficial de **Coca-Cola** (`#F40009` Rojo Spencerian, `#B80007` Carmesí, `#FFFFFF` Blanco Dynamic Ribbon y `#0D0D0F` Negro Carbón).

## Arquitectura

```
                      ┌──────────────────────────── FastAPI ────────────────────────────┐
 Navegador ──► Gradio │  /           chat corporativo (interfaz Gradio)                  │
                      │  /admin      panel de administración (token)                     │
                      │  /api/*      API HTTP · /health · /docs                          │
                      └───────┬──────────────────────────────────────────────────────────┘
                              ▼
                       app/service.py  (pipeline de consulta)
                              │
   ┌──────────┬───────────────┼────────────────┬───────────────┐
   ▼          ▼               ▼                ▼               ▼
 safety    intent       índice BM25        quota / caché     llm.py
(derivar) (qué dato    (tags, sinónimos,  (cupos, límites)  (Anthropic u
           se pide)     prefijos)                            OpenAI-compatible)
                              ▲
                  data/corpus.txt ──► app.build_corpus ──► data/index.json
```

### Pipeline de consulta

Cada nivel se evalúa en orden; solo el último consume tokens de salida significativos.

| Nivel | Comportamiento | Tokens |
|---|---|---|
| 0 | Derivación de emergencias industriales y temas de salud ocupacional, legales/compliance o psicológicos; caché; aclaración cuando se pregunta un dato sin indicar el tema | 0 |
| 1 | **Respuesta al punto**: devuelve únicamente el dato pedido (horario, teléfono, ubicación…). **Seguimiento**: «¿y el teléfono?» reutiliza el último tema de la conversación. Ficha directa para consultas claras | 0 |
| 1b | **Reformulación**: si la búsqueda local no encuentra nada, el modelo propone 4 a 8 palabras clave y se busca de nuevo (una vez por pregunta, con caché; no cuenta como consulta del día) | ≈ 100 |
| 2 | Una llamada al modelo con un máximo de 3 fichas recortadas, en streaming | ≈ 860 máx. |

### Decisiones de diseño

- **Búsqueda léxica** (BM25 con campos ponderados: tags ×4, título ×3, puesto ×2, texto ×1), sinónimos editables y coincidencia por prefijo. No requiere embeddings ni base de datos y construir el índice cuesta 0 tokens.
- **Abstención con umbrales** (`MIN_SCORE`, `MIN_COVERAGE`): sin evidencia suficiente no se invoca al modelo.
- **Contenido como dato.** Las fichas se entregan al modelo delimitadas y se instruye ignorar órdenes embebidas. Correos y teléfonos nunca se envían al modelo.
- **Citas validadas.** El modelo cita el id de la ficha; las citas inexistentes se descartan y la respuesta se marca como no verificada si no cita ninguna.
- **Sin estado en servidor.** Sin cuentas ni base de datos; la conversación no se persiste.

## Estructura del repositorio

```
app/
  main.py          FastAPI: API, cabeceras de seguridad y montaje de Gradio
  ui.py            interfaz pública (diseño Coca-Cola, chat, streaming)
  admin.py         panel /admin y publicación del catálogo en GitHub
  admin_ai.py      importación de documentos y borradores con IA (uso del administrador)
  service.py       pipeline de consulta
  index.py         índice BM25, sinónimos y cobertura
  intent.py        detección local del dato solicitado
  corpus.py        parser y validación de corpus.txt
  llm.py           cliente HTTP del modelo (respuesta completa y streaming)
  quota.py         ritmo, cupos diarios y tope global
  safety.py        filtro de derivación
  build_corpus.py  CLI: validar e indexar
  importar.py      CLI: proponer fichas desde un documento
data/
  corpus.txt       catálogo de trámites, políticas y servicios de Coca-Cola
  sinonimos.txt    vocabulario corporativo y coloquial
  info_campus.md   datos del Corporativo Coca-Cola (panel de información)
  index.json       índice precalculado
tests/             pytest
render.yaml        servicio de Render (Blueprint)
```

## Inicio rápido

Requisitos: Python 3.12.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m app.build_corpus            # valida el catálogo y genera data/index.json
uvicorn app.main:app --reload         # http://localhost:8000
```

Con `LLM_PROVIDER=none` la aplicación funciona completa sin invocar al modelo (respuestas directas y al punto, sin reformulación ni redacción).

## Configuración

Todo se controla con variables de entorno. Las claves y tokens nunca deben subirse al repositorio.

| Variable | Descripción | Por defecto |
|---|---|---|
| `LLM_PROVIDER` | `anthropic`, `openai` (compatible) o `none` | `anthropic` |
| `MODEL_NAME` | Modelo a utilizar; verifica el identificador vigente con tu proveedor | `claude-haiku-5-5` |
| `LLM_API_KEY` | Clave del proveedor (secreta) | — |
| `LLM_BASE_URL` | URL base alternativa para proveedores compatibles | — |
| `ADMIN_TOKEN` | Token del panel y de `/api/admin/*` (secreto) | — |
| `ID_SALT` | Sal para el hash de identificadores anónimos (secreta) | `cambia-esto` |
| `TIMEZONE` | Zona horaria para el reinicio diario de cupos | `America/Hermosillo` |
| `MAX_QUERY_CHARS` | Longitud máxima de la pregunta | `300` |
| `TOP_K` | Fichas máximas enviadas al modelo | `3` |
| `MAX_CONTEXT_CHARS` | Presupuesto de contexto por consulta | `1800` |
| `MAX_OUTPUT_TOKENS` | Tokens máximos de salida | `250` |
| `USER_TOKENS_DAY` / `USER_QUERIES_DAY` | Cupo diario por usuario | `10000` / `15` |
| `REQ_PER_MIN` | Consultas por minuto por usuario | `8` |
| `IP_MULTIPLIER` | Holgura del cupo por IP (redes compartidas) | `5` |
| `GLOBAL_TOKENS_DAY` | Tope diario de todo el servicio | `300000` |
| `MIN_SCORE` / `MIN_COVERAGE` | Umbrales de relevancia | `1.2` / `0.34` |
| `DIRECT_ENABLED` | Permite responder con la ficha sin invocar al modelo | `true` |
| `STALE_DAYS` | Antigüedad a partir de la cual se avisa de vigencia | `365` |
| `CACHE_SIZE` / `CACHE_TTL_S` | Caché de respuestas | `500` / `86400` |
| `REPORTS_PER_DAY` | Informes de «sin respuesta» por usuario y día | `5` |
| `REPORT_WEBHOOK_URL` | Webhook opcional que recibe los informes | — |
| `IMPORT_MAX_CHUNKS` / `IMPORT_CHUNK_CHARS` | Límites de la importación asistida | `6` / `6000` |
| `GITHUB_TOKEN`, `GITHUB_REPO` | Publicación del catálogo desde el panel | — |
| `GITHUB_BRANCH`, `GITHUB_CORPUS_PATH` | Rama y ruta del catálogo | `main`, `data/corpus.txt` |
| `SHOW_ADMIN_LINK` | Muestra un enlace discreto «Administración» al pie del chat; `false` lo oculta (el panel sigue en `/admin`) | `true` |

> Los cupos viven en memoria y se reinician con el servicio. Configura además un tope de gasto en el panel del proveedor del modelo.

## Catálogo (corpus)

`data/corpus.txt` contiene una ficha por trámite, política o servicio corporativo. El formato es de texto plano, pensado para editarse a mano:

```
### recursos-humanos
TITULO: Recursos Humanos y Atención al Colaborador
PUESTO: Dirección de Capital Humano Coca-Cola
CATEGORIA: tramites
AUDIENCIA: colaborador
TAGS: contratacion, ingreso, gafete, constancia, recibo de nomina, baja
RESPONSABLE: Lic. Laura Pérez
CORREO: capital.humano@coca-cola.ejemplo.com
TELEFONO: 55 5262 6000 ext. 101
UBICACION: Planta baja del Edificio Corporativo, junto a Recepción Principal
HORARIO: Lunes a viernes, 9:00 a 15:00
WEB: https://www.coca-cola.com/mx/es
ACTUALIZADO: 2026-08-15
PREGUNTA: ¿Dónde entrego mis documentos de contratación?
--
Texto libre con frases cortas y literales: qué es, qué documentos llevar, pasos y políticas aplicables.
```

| Campo | Uso |
|---|---|
| `### id` | Identificador único (minúsculas y guiones) |
| `TITULO` | Obligatorio |
| `TAGS` | Palabras que los usuarios escribirían, con sinónimos coloquiales. Principal factor de recuperación |
| `PUESTO`, `RESPONSABLE`, `CORREO`, `TELEFONO`, `UBICACION`, `HORARIO`, `WEB` | Ficha de contacto y respuestas al punto |
| `ACTUALIZADO` | `AAAA-MM-DD`; habilita el aviso de vigencia |
| `PREGUNTA` | Pregunta modelo mostrada como ejemplo en el chat; los temas más consultados aparecen primero |
| `CATEGORIA`, `AUDIENCIA` | Clasificación (`colaborador`, `proveedor`, `cliente`, `todos`) |

## Administración

### Panel web

`/admin` (requiere `ADMIN_TOKEN`):

- **Resumen:** temas más consultados, informes de «sin respuesta», fichas desactualizadas y avisos de validación.
- **Corpus:** editor con validación y **Guardar y publicar**. El cambio se aplica de inmediato; con `GITHUB_TOKEN` y `GITHUB_REPO` se registra además un commit y Render redespliega.
- **Memoria:** estado de lo cargado frente al archivo del catálogo, caché e informes pendientes. Botones **Reindexar ahora** y **Vaciar caché**.
- **Importar con IA:** carga de PDF, HTML, TXT o MD (máx. 3 MB). Propone fichas para revisión; los correos, teléfonos y URLs ausentes del documento original se eliminan de la propuesta.
- **Borrador desde informes:** genera fichas con `[COMPLETAR]` a partir de las preguntas sin respuesta más frecuentes.
- **Configuración:** valores activos de solo lectura con recomendaciones. Los secretos nunca se muestran.

## API HTTP

Documentación interactiva en `/docs`.

| Método y ruta | Descripción | Acceso |
|---|---|---|
| `GET /health` | Estado del servicio | Público |
| `POST /api/consulta` | `{"texto": str, "perfil": "colaborador\|proveedor\|cliente\|todos"}` → respuesta con fichas y uso. Cabecera opcional `X-Client-Id` | Público, con límite de ritmo |
| `POST /api/feedback` | `{"util": bool}` | Público |
| `GET /api/admin/estado` | Estado del índice, métricas y cuotas | Token |
| `GET /api/admin/reportes` | Informes de «sin respuesta» y temas populares | Token |
| `POST /api/admin/reindex` | Recarga el catálogo | Token |

## Pruebas y calidad

```bash
python -m app.build_corpus --check
pytest -q --cov=app
```

## Despliegue en Render

1. Crea un **Web Service** conectado a tu repositorio en GitHub (o usa `render.yaml` desde **New > Blueprint**).
2. Configuración lista en `render.yaml`:
   - **Name:** `coca-cola-guia`
   - **Build Command:** `pip install -r requirements.txt && python -m app.build_corpus --check`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
3. Variables de entorno en Render: `PYTHON_VERSION=3.12.8`, `LLM_API_KEY`, `ADMIN_TOKEN` e `ID_SALT`; opcionalmente `GITHUB_TOKEN`, `GITHUB_REPO` y `REPORT_WEBHOOK_URL`.
4. Cada push a la rama `main` redespliega automáticamente.
