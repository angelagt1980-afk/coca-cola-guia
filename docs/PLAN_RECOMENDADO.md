# Plan recomendado (v2): COCA-COLA GUÍA — mínimo gasto de tokens y almacenamiento simple

## 1. Decisión central
El gasto de tokens **no debe estar en el build del corpus** ni en cada consulta si se puede evitar. Se diseña por niveles; solo el último usa IA:

| Nivel | Qué ocurre | Tokens |
|---|---|---|
| 0 | Emergencias/salud ocupacional/legal/psico → derivación fija a áreas de Coca-Cola; caché; abstención sin evidencia | 0 |
| 1 | Consulta clara (todos los términos hallados y un ganador nítido) → ficha + resumen del propio corpus | 0 |
| 2 | Consulta ambigua o compuesta → **1** llamada al LLM con ≤3 documentos recortados (~610 entrada + ≤250 salida) | ≈ 860 máx. |
| Build | `build_corpus` valida e indexa con BM25 (sin LLM ni embeddings) | 0 |
| Build opcional | `--sugerir-tags` solo para entradas sin tags, con caché por hash | ≈ 100 / entrada nueva |

## 2. Arquitectura mantenida y adaptada a The Coca-Cola Company
| Componente | Implementación en COCA-COLA GUÍA | Beneficio |
|---|---|---|
| Recuperación | BM25 con campos ponderados (tags×4, título×3, puesto×2), sinónimos corporativos y prefijos | Cero costo recurrente en el build y alta velocidad |
| Catálogo | `data/corpus.txt` con bloques `CLAVE: valor` de áreas de Coca-Cola (RR.HH., Beneficios, Abastecimiento, Calidad, TI, Sostenibilidad) | Edición a mano trivial desde `/admin` |
| Pipeline | Determinista con 1 llamada LLM como máximo y streaming | Consumo predecible y mínimo |
| Contactos | Ficha de contacto tomada del corpus, nunca redactada por el modelo | Cero alucinación de teléfonos/extensiones/correos |
| Cuotas | Cupos por usuario/día, por consulta y global, con degradación a ficha | Gasto acotado |
| Identidad visual | Paleta oficial Coca-Cola (`#F40009`, `#B80007`, `#FFFFFF`, `#0D0D0F`) | Diseño corporativo profesional y accesible (WCAG AA/AAA) |

## 3. Requisitos clave y verificación
| Requisito | Verificación |
|---|---|
| Sin evidencia → abstención, nunca inventar | `test_abstencion_sin_evidencia_solo_reformula`, `test_fuera_de_alcance_baja_relevancia` |
| Citas válidas; inventadas se descartan | `test_llm_cita_validada_y_tokens_contados`, `test_cita_inventada_se_descarta` |
| Tope de tokens por consulta/usuario/global | `tests/test_quota.py`, `test_limite_diario_degrada_a_ficha` |
| Contactos nunca van al LLM | assert en `test_llm_cita_validada_y_tokens_contados` |
| Emergencias/salud derivadas | `test_emergencia_deriva_sin_tokens`, `test_salud_deriva` |
| Admin protegido | `tests/test_api.py`, `tests/test_admin.py` |
| Nunca HTTP 500 al usuario | manejador en `main.consulta` |
