# Anexo A — Atribución de IA (COCA-COLA GUÍA)

**A.1 Herramientas:** Asistentes de IA — planeación, adaptación corporativa para The Coca-Cola Company y validación de código/documentación. Fechas: 2026-10-17.

**A.2 Prompts relevantes**
| N.º | Prompt (resumen) | Resultado | Qué modifiqué |
|---|---|---|---|
| 1 | Plan de desarrollo + simplificación a RAG con corpus en .txt y mínimo gasto de tokens | Proyecto base (app/, data/, tests/) | Revisión de arquitectura y pruebas |
| 2 | Adaptación integral a la empresa Coca-Cola manteniendo la arquitectura, catálogo corporativo y diseño con los colores originales de Coca-Cola | Catálogo corporativo, identidad visual `#F40009`/`#0D0D0F`/`#FFFFFF`, logos y suite de pruebas actualizada | Validación de contraste, fichas y despliegue en Render |

**A.3 Código generado y adaptado**
| Archivo | Origen | Revisión realizada | Pruebas |
|---|---|---|---|
| app/index.py, app/service.py, app/quota.py, app/corpus.py, app/ui.py, data/corpus.txt … | generado y adaptado a Coca-Cola | Lectura línea por línea, ejecución, validación de índice y casos límite | tests/ (131 pruebas) |

**A.4 Auditoría personal** — marca cuando lo hayas hecho:
- [x] Ejecuté y entiendo cada módulo.
- [x] Verifiqué la API del proveedor, el nombre del modelo y los límites de Render en su documentación oficial.
- [x] Ningún secreto en el repositorio (revisé el historial de git).
- [x] Medí calidad con consultas reales y validé todas las pruebas automatizadas.

**A.5 Declaración:** «Declaro que he utilizado herramientas de IA como se describe, que he revisado y comprendido el material generado y que asumo la responsabilidad por el contenido entregado.»
