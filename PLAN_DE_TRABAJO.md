# Plan de trabajo integral para sistema de recomendación y búsqueda semántica (ShopAI)

## 1. Objetivos y alcance
- Construir un sistema híbrido de recomendación y búsqueda semántica que use datos de interacciones (rating, timestamp) y modelos de OpenAI.
- Exponer el sistema como servicio HTTP (local y desplegable en AWS) con monitoreo básico.
- Asegurar gobernanza: seguridad de claves, control de costos y observabilidad.

## 2. Arquitectura propuesta (alto nivel)
- **Almacenamiento**: datos crudos en S3; artefactos derivados (embeddings, matrices de factorización, métricas) versionados en S3.
- **Procesamiento batch**: jobs orquestados (p.ej., Make/Poetry + scripts) para ingesta, limpieza, generación de embeddings, entrenamiento y evaluación.
- **Vector store**: FAISS local para demo; opción PGVector/OpenSearch para AWS.
- **Servicio de inferencia**: API FastAPI con endpoints `/search` y `/recommendations`; integración a OpenAI API para embeddings y respuesta generativa opcional.
- **Monitoreo**: logs estructurados, métricas de latencia/errores, y cálculo periódico de calidad (Precision@K, Recall@K, NDCG).

## 3. Roadmap por fases
### Fase A: Setup y fundaciones
- Configurar entorno reproducible (Poetry/requirements.txt, Makefile).
- Gestionar credenciales con variables de entorno y opcionalmente AWS Secrets Manager.
- Añadir configuraciones tipadas (pydantic settings) para S3, OpenAI y rutas de artefactos.

### Fase B: Ingesta y EDA
- Leer CSV desde S3 usando `boto3` en modo stream/chunks para 9882 filas.
- Validar esquema y tipos; normalizar timestamps a UTC; manejar duplicados y ratings fuera de rango.
- EDA rápida: distribución de ratings, sparsity user–item, top productos/usuarios, actividad temporal.
- Guardar dataset limpio versionado en S3 y local (`data/processed/ratings.parquet`).

### Fase C: Particiones y conjuntos de evaluación
- Split temporal (train/val/test) para evitar fuga: e.g., 70/15/15 por timestamp.
- Generar catálogos de usuarios/productos con contadores de interacciones.
- Definir baseline de popularidad global y por usuario para referencia de métricas.

### Fase D: Representación de contenido y embeddings
- Preparar texto por producto (título/descripcion); si faltan campos, sintetizar breve resumen con modelo GPT y cachear.
- Generar embeddings con `text-embedding-3-large` en lotes (backoff y retries); almacenar en S3 y vector store con versión `{model_id}-{fecha}`.
- Indexar FAISS (L2/inner-product) y persistir índice.

### Fase E: Modelo colaborativo y fusión
- Entrenar baseline colaborativo (ALS/implicit o matriz de coocurrencia simple) sobre train.
- Calibrar pesos de fusión: `score = w_vec * sim_vec + w_collab * score_collab` usando grid search en validación.
- Implementar re-ranking híbrido con filtros opcionales (p.ej., excluir vistos).

### Fase F: Evaluación offline y experimentos
- Métricas: Precision@K, Recall@K, NDCG, Coverage; calcular por segmento temporal.
- Comparar variantes: (1) popularidad, (2) vector puro, (3) colaborativo, (4) fusión.
- Reportar costos estimados (embeddings) y latencias simuladas.

### Fase G: Servicio de inferencia
- Implementar API FastAPI:
  - `POST /search`: query libre → embeddings → vector store → (opcional) respuesta generativa.
  - `POST /recommendations`: user_id + historial opcional → candidatos híbridos → re-ranking → retorno JSON.
- Controles: timeouts, retries, límites de top_k, logging estructurado, tracing opcional.
- Caching: respuestas populares y últimas consultas (LRU/Redis opcional).

### Fase H: Despliegue y seguridad
- Contenedor Docker con multi-stage build; healthchecks.
- Despliegue de demo local (uvicorn) y manifiestos para AWS (ECS Fargate/EKS) con autoescalado básico.
- Gestión de secretos vía IAM Role/Secrets Manager; variables de entorno en local.
- Configurar límites de costo y rate limit hacia OpenAI.

### Fase I: Monitoreo y mantenimiento
- Logs a CloudWatch (o STDOUT estructurado en local); dashboards de latencia p50/p95/p99 y tasa de error.
- Tareas programadas: refresco de embeddings para nuevos productos y reentrenos semanales/mensuales.
- Detección de drift: comparación de distribuciones de consultas/ratings y degradación de métricas.
- Feedback loop: endpoint para marcar resultados no relevantes y ajustar pesos/reentrenos.

## 4. Entregables
- Código de ingesta/EDA, pipelines de embeddings, entrenamiento colaborativo y evaluación.
- Índice vectorial y artefactos de modelo versionados en S3/local.
- API FastAPI lista para ejecutar localmente y contenedor Docker.
- Scripts/Make targets para correr fin a fin (ingesta → embeddings → entrenamiento → evaluación → servicio).
- Documentación de setup, uso, costos y estrategia de monitoreo.

## 5. Cronograma estimado (ajustable)
- **Día 1 (4–6 h demo)**: Setup, ingesta/EDA, split, embeddings iniciales, baseline de recomendación, API mínima.
- **Día 2**: Fusión híbrida, evaluación offline completa, endurecimiento de API (seguridad/caching), Docker.
- **Día 3+**: Monitoreo, automatización de reentrenos, optimización de costos y despliegue en AWS.
