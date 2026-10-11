# GTU GUÍA (versión simple, bajo costo de tokens)

Chat (Gradio, con la marca del Grupo Tecnológico Universitario) de consulta sobre **trámites y servicios** del campus para estudiantes y profesores.
El usuario solo ve un chat. El administrador mantiene **un archivo de texto** (`data/corpus.txt`).

```
data/corpus.txt ──► python -m app.build_corpus ──► data/index.json   (0 tokens)
                                                        │
 usuario ─► chat ─► filtro seguridad ─► caché ─► búsqueda local ─┬─► ficha directa      (0 tokens)
                                                                 └─► 1 llamada LLM corta (~860 tokens máx.)
```

## Inicio rápido
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # edita LLM_API_KEY, ADMIN_TOKEN, ID_SALT (o LLM_PROVIDER=none)
python -m app.build_corpus      # valida y genera data/index.json
set -a; source .env; set +a     # (o exporta las variables como prefieras)
uvicorn app.main:app --reload   # http://localhost:8000   (Swagger en /docs)
pytest -q --cov=app
```
Con `LLM_PROVIDER=none` todo funciona **sin gastar un solo token** (respuestas directas con ficha).

## Cómo actualizar la información (administrador)
**Opción A — Panel web `/admin` (recomendada).** Entra a `https://TU-APP.onrender.com/admin` con tu `ADMIN_TOKEN`.
- *Resumen*: temas más consultados, informes de «sin respuesta», fichas desactualizadas y avisos.
- *Corpus*: edita el texto completo, **Validar** y **Guardar y publicar**. Se aplica al instante en el servidor y, si configuraste `GITHUB_TOKEN` + `GITHUB_REPO`, se hace commit en GitHub (Render redespliega solo). Sin GitHub el cambio se pierde al reiniciar el servicio.
- *Importar con IA*: sube un reglamento o convocatoria (PDF, HTML, TXT, MD; máx. 3 MB). La IA propone fichas; **tú revisas**. Los correos, teléfonos y webs que no aparezcan en el documento se eliminan de la propuesta. Gasta tokens una sola vez por documento (≈ 1,000–1,500 por fragmento de 6,000 caracteres; tope de `IMPORT_MAX_CHUNKS`).
- *Borrador desde informes*: convierte las preguntas sin respuesta más frecuentes en fichas con `[COMPLETAR]`. **No se pueden publicar mientras tengan `[COMPLETAR]`**.
- Crear el token de GitHub: Settings → Developer settings → Fine-grained tokens → solo este repositorio → permiso *Contents: Read and write*.

**Opción B — A mano.**
1. Abre `data/corpus.txt`, copia `data/plantilla_entrada.txt` al final y llena los campos.
2. `python -m app.build_corpus` valida (avisa de tags faltantes, fechas, correos, entradas largas u obsoletas).
3. `git commit` y `git push` → Render redespliega solo.
4. Por consola: `python -m app.importar reglamento.pdf --dry-run` (costo estimado, 0 tokens) y luego sin `--dry-run` para escribir `data/propuestas.txt`. `python -m app.build_corpus --sugerir-tags` sugiere tags solo para entradas sin TAGS.

API (con tu token): `GET /api/admin/reportes` y `POST /api/admin/reindex`.

### Formato de una entrada
```
### servicios-escolares                  <- id único (minúsculas y guiones)
TITULO: Servicios Escolares
PUESTO: Coordinación de Servicios Escolares
CATEGORIA: tramites
AUDIENCIA: estudiante                    <- estudiante | profesor | todos (la interfaz ya no pregunta el perfil)
TAGS: inscripcion, credencial, kardex    <- lo que la gente escribiría; incluye sinónimos coloquiales
RESPONSABLE: Mtra. Laura Pérez
CORREO: servicios.escolares@ejemplo.edu.mx
TELEFONO: 662 000 0001 ext. 101
UBICACION: Planta baja, junto a la cafetería
HORARIO: Lunes a viernes, 9:00 a 15:00
ACTUALIZADO: 2026-08-15
PREGUNTA: ¿Dónde entrego mis documentos de inscripción?   <- (opcional) ejemplo que verá el usuario
--                                       <- separa encabezado y texto
Texto libre, frases cortas, menos de 1,200 caracteres.
```
`data/sinonimos.txt`: un grupo por línea (`inscripcion, matricula, registro`) para vocabulario coloquial.

## Control de gasto (todo configurable por variable de entorno)
| Capa | Control | Por defecto |
|---|---|---|
| Consulta | caracteres de pregunta / documentos / contexto / salida | 300 / 3 / 1,800 / 250 tokens |
| Usuario | tokens y consultas con IA por día (id anónimo + IP) | 10,000 / 15 |
| Ritmo | consultas por minuto | 8 |
| Global | tokens por día de todo el servicio | 300,000 |
| Gratis | caché, derivaciones, abstenciones, respuestas directas | 0 tokens |
Al agotarse el cupo, el usuario **sigue recibiendo la ficha** (degradación, no error). **Configura también un tope de gasto en el panel del proveedor**: los contadores viven en memoria y se reinician al reiniciar el servicio.

## Cómo piensa la app (y cuánto cuesta cada nivel)
| Nivel | Qué ocurre | Tokens |
|---|---|---|
| 0 | Emergencias/salud/legal → derivación fija · caché · aclaración si preguntan un dato sin decir de qué | 0 |
| 1 | **Respuesta al punto**: «¿a qué hora abre la biblioteca?» devuelve solo el horario de la ficha · **seguimiento**: «¿y el teléfono?» usa el último tema de esa conversación · ficha directa para consultas claras | 0 |
| 1b | **Segunda oportunidad**: si la búsqueda local no halla nada, la IA propone 4–8 palabras clave y se busca de nuevo (una vez por pregunta, con caché; no cuenta como consulta del día) | ≈ 100 |
| 2 | Una llamada a la IA con ≤ 3 fichas recortadas, **en streaming** (el texto aparece mientras se escribe) | ≈ 860 máx. |
Los datos (horarios, teléfonos, correos, ubicación) siempre salen del corpus, nunca los escribe el modelo. Si un dato no está registrado, la app lo dice en vez de inventarlo.

## Interfaz (Gradio) y marca
Experiencia directa: abres la página, escribes, envías (flecha) y recibes respuesta. Cada visita es una conversación nueva; **no se guarda ningún historial**.
- Código en `app/ui.py` (tema, CSS, chat). Se monta en `/` dentro de FastAPI: siguen existiendo `/health`, `/api/*` y `/docs`.
- **Modo oscuro por defecto** con la paleta GTU (constantes al inicio de `ui.py`): fondo azul marino muy oscuro derivado de #06096F, burbuja del usuario en degradado #234488→#046DB4, acento naranja #FF5100/#FF7D00 (botón de envío, borde de las respuestas).
- Logo: `app/static/logo_dark.png` (variante con el texto en #F5F5F5 para fondo oscuro; el original `logo.png` se conserva) y favicon `favicon.png`.
- **Ejemplos de preguntas**: son las `PREGUNTA:` que escribes en el corpus; se muestran primero las de los temas más consultados desde el último reinicio. Nunca se muestra texto escrito por usuarios. Desaparecen al enviar la primera pregunta.
- **Informe de «sin respuesta»**: cuando no hay información aparece el botón «Informar que falta esta información». Envía solo la pregunta (con correos/teléfonos tachados), máximo `REPORTS_PER_DAY` por usuario y día. Se guarda en memoria, se escribe en los registros de Render (`REPORTE_SIN_RESPUESTA`) y, si defines `REPORT_WEBHOOK_URL`, se envía a ese webhook (Discord, Slack, Google Apps Script…). **En el plan gratuito la memoria se pierde al reiniciar**: usa el webhook o revisa los registros.
- **Información del campus**: el botón «i» del encabezado abre un panel oculto con dirección y contacto; el texto está en `data/info_campus.md` (edítalo a mano). La misma información está como entrada del corpus (`gtu-campus-hermosillo`) para que el chat también la responda.

## Despliegue en Render
`render.yaml` incluido. Variables secretas en el panel: `LLM_API_KEY`, `ADMIN_TOKEN`, `ID_SALT`. Healthcheck: `/health`.

## Seguridad y privacidad
Sin cuentas ni base de datos; no se guarda la conversación ni las preguntas. Solo se guarda la pregunta si el usuario pulsa «Informar» (truncada, con datos de contacto tachados y sin IP). IPs e ids se usan con hash salado en memoria. Documentos al modelo como datos delimitados; correos y teléfonos **nunca** se envían al modelo. Todo el contenido del corpus se muestra escapado como texto en el chat (sin HTML ni formato inyectado); la API lleva cabeceras de seguridad. Admin con token y bloqueo tras 5 intentos fallidos.

## Limitaciones conocidas
Búsqueda léxica (BM25 + tags + sinónimos + prefijos), no semántica: la calidad depende de buenos TAGS y sinónimos. Plan gratuito de Render: arranque en frío, 512 MB de RAM (Gradio consume más que una página estática: vigila la memoria en los registros) y sin disco persistente. Verifica el nombre de modelo y los límites vigentes del proveedor antes de desplegar. Este código fue generado con asistencia de IA: ver `ANEXO_ATRIBUCION_IA.md`.
