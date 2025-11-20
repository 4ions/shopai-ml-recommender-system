from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger
from src.api.middleware.logging import LoggingMiddleware
from src.api.middleware.metrics import MetricsMiddleware
from src.api.routes import search, recommendations, health, feedback, reports

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting application", environment=settings.environment)

    try:
        from src.api.download_artifacts import download_artifacts_from_s3
        download_artifacts_from_s3()
    except Exception as e:
        logger.warning("Failed to download artifacts from S3, using local", error=str(e))

    try:
        from src.models.collaborative import CollaborativeFilter
        from src.models.hybrid import HybridRecommender
        from src.services.vector_store import FAISSVectorStore
        from src.services.recommendation import RecommendationService
        from src.services.search import SearchService
        from src.data.catalog import UserCatalog, ProductCatalog

        logger.info("Loading models and services")

        import glob
        import os
        
        collaborative_model_path = "data/artifacts/collaborative_model.pkl"
        if not os.path.exists(collaborative_model_path):
            raise FileNotFoundError(f"Collaborative model not found: {collaborative_model_path}")
        collaborative_model = CollaborativeFilter.load(collaborative_model_path)
        
        index_files = glob.glob("data/artifacts/faiss_index_*.pkl")
        if not index_files:
            raise FileNotFoundError("No FAISS index found")
        latest_index = max(index_files)
        vector_store = FAISSVectorStore.load(latest_index)
        
        # Verify vector store is not empty, regenerate if needed
        try:
            total_vectors = vector_store.index.ntotal if hasattr(vector_store.index, 'ntotal') else len(vector_store.product_ids)
        except (AttributeError, TypeError):
            total_vectors = len(vector_store.product_ids) if vector_store.product_ids else 0
        
        if total_vectors == 0 or len(vector_store.product_ids) == 0:
            logger.warning("Vector store is empty, attempting to regenerate from embeddings")
            try:
                # Try to regenerate from embeddings
                embeddings_files = glob.glob("data/artifacts/embeddings_*.npy")
                if embeddings_files:
                    latest_embeddings = max(embeddings_files)
                    logger.info("Regenerating index from embeddings", file=latest_embeddings)
                    from scripts.regenerate_faiss_index import main as regenerate_main
                    regenerate_main()
                    # Reload
                    index_files = glob.glob("data/artifacts/faiss_index_*.pkl")
                    if index_files:
                        latest_index = max(index_files)
                        vector_store = FAISSVectorStore.load(latest_index)
                        logger.info("Vector store regenerated successfully")
                else:
                    logger.error("No embeddings found to regenerate index")
            except Exception as e:
                logger.error("Failed to regenerate vector store", error=str(e))
                raise
        
        user_catalog_path = "data/artifacts/user_catalog.json"
        if not os.path.exists(user_catalog_path):
            raise FileNotFoundError(f"User catalog not found: {user_catalog_path}")
        user_catalog = UserCatalog.load(user_catalog_path)
        
        product_catalog_path = "data/artifacts/product_catalog.json"
        if not os.path.exists(product_catalog_path):
            raise FileNotFoundError(f"Product catalog not found: {product_catalog_path}")
        product_catalog = ProductCatalog.load(product_catalog_path)

        hybrid_recommender = HybridRecommender(
            collaborative_model=collaborative_model,
            vector_store=vector_store,
            alpha=0.5,
        )

        recommendation_service = RecommendationService(
            hybrid_recommender=hybrid_recommender,
            user_catalog=user_catalog,
            product_catalog=product_catalog,
        )

        search_service = SearchService(
            vector_store=vector_store,
            product_catalog=product_catalog,
        )

        app.state.hybrid_recommender = hybrid_recommender
        app.state.recommendation_service = recommendation_service
        app.state.search_service = search_service
        app.state.user_catalog = user_catalog
        app.state.product_catalog = product_catalog
        app.state.vector_store = vector_store

        logger.info("Models and services loaded successfully")

    except FileNotFoundError as e:
        logger.warning("Models not found, API will run in degraded mode", error=str(e))
    except Exception as e:
        logger.error("Error loading models", error=str(e))
        raise

    yield

    logger.info("Shutting down application")


app = FastAPI(
    title="ShopAI ML Recommender System",
    description="Hybrid recommendation and semantic search system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(search.router)
app.include_router(recommendations.router)
app.include_router(health.router)
app.include_router(feedback.router)
app.include_router(reports.router)


@app.get("/")
async def root():
    return {
        "message": "ShopAI ML Recommender System API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/metrics")
async def metrics():
    from src.infrastructure.metrics import get_metrics, get_metrics_content_type
    from fastapi import Response

    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )

