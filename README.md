# CampusGuía (versión simple, bajo costo de tokens)

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
1. Abre `data/corpus.txt`, copia `data/plantilla_entrada.txt` al final y llena los campos.
2. `python -m app.build_corpus` → valida (avisa de tags faltantes, fechas, correos, entradas largas u obsoletas).
3. `git commit` y `git push` → Render redespliega solo. Para ver cambios sin redesplegar (solo si el archivo ya está en el servidor):
   `curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" https://TU-APP.onrender.com/api/admin/reindex`
4. `GET /api/admin/brechas` muestra las preguntas sin respuesta (anónimas) = qué entradas faltan.
5. Opcional: `python -m app.build_corpus --sugerir-tags` pide al LLM tags **solo para entradas sin TAGS** (~100 tokens c/u, con caché por hash); escribe `data/tags_sugeridos.txt` y **nunca modifica tu corpus**.

### Formato de una entrada
```
### servicios-escolares                  <- id único (minúsculas y guiones)
TITULO: Servicios Escolares
PUESTO: Coordinación de Servicios Escolares
CATEGORIA: tramites
AUDIENCIA: estudiante                    <- estudiante | profesor | todos (puedes combinar con comas)
TAGS: inscripcion, credencial, kardex    <- lo que la gente escribiría; incluye sinónimos coloquiales
RESPONSABLE: Mtra. Laura Pérez
CORREO: servicios.escolares@ejemplo.edu.mx
TELEFONO: 662 000 0001 ext. 101
UBICACION: Planta baja, junto a la cafetería
HORARIO: Lunes a viernes, 9:00 a 15:00
ACTUALIZADO: 2026-08-15
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

## Interfaz (Gradio) y marca
- Código en `app/ui.py`: tema, CSS y chat; se monta en `/` dentro de FastAPI (`app/main.py`), de modo que **siguen existiendo** `/health`, `/api/*` y `/docs`.
- Logo en `app/static/logo.png` y favicon en `app/static/favicon.png`. Para cambiarlos, reemplaza los archivos.
- Paleta (constantes al inicio de `ui.py`): azul de marca `#234488` para texto, botones y burbuja del usuario; naranjas `#FF5100`/`#FF7D00` solo como acento (barra del encabezado y borde de la respuesta), porque el naranja sobre blanco no cumple el contraste 4.5:1 de WCAG AA.
- La interfaz fuerza los colores de marca también en modo oscuro del navegador.

## Despliegue en Render
`render.yaml` incluido. Variables secretas en el panel: `LLM_API_KEY`, `ADMIN_TOKEN`, `ID_SALT`. Healthcheck: `/health`.

## Seguridad y privacidad
Sin cuentas ni base de datos; no se guardan preguntas (solo, opcional, las no respondidas: truncadas, sin IP). IPs e ids se usan con hash salado en memoria. Documentos al modelo como datos delimitados; correos y teléfonos **nunca** se envían al modelo. Todo el contenido del corpus se muestra escapado como texto en el chat (sin HTML ni formato inyectado); la API lleva cabeceras de seguridad. Admin con token y bloqueo tras 5 intentos fallidos.

## Limitaciones conocidas
Búsqueda léxica (BM25 + tags + sinónimos + prefijos), no semántica: la calidad depende de buenos TAGS y sinónimos. Plan gratuito de Render: arranque en frío, 512 MB de RAM (Gradio consume más que una página estática: vigila la memoria en los registros) y sin disco persistente. Verifica el nombre de modelo y los límites vigentes del proveedor antes de desplegar. Este código fue generado con asistencia de IA: ver `ANEXO_ATRIBUCION_IA.md`.
