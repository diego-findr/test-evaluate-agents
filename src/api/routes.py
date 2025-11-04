"""
FastAPI routes and application setup
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..models import EvaluationRequest, EvaluationResult
from ..services import EvaluationService
from ..exceptions import InvalidInputDataError, AgentExecutionError, GraphExecutionError
from .dependencies import get_container


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    settings = get_settings()
    container = get_container()
    await container.initialize(settings)
    logger.info("FastAPI application startup complete")
    
    yield
    
    # Shutdown
    await container.cleanup()
    logger.info("FastAPI application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="MAS-Eval: Multi-Agent Candidate Evaluation System",
        description="AI-powered candidate evaluation microservice using LangGraph",
        version="1.0.0",
        lifespan=lifespan
    )
    
    
    def get_evaluation_service() -> EvaluationService:
        """Dependency injection for EvaluationService."""
        container = get_container()
        if container.evaluation_service is None:
            raise HTTPException(
                status_code=503,
                detail="Evaluation service not initialized"
            )
        return container.evaluation_service
    
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "mas-eval",
            "version": "1.0.0"
        }
    
    
    @app.post("/evaluate", response_model=EvaluationResult)
    async def evaluate_candidate(
        request: EvaluationRequest,
        service: EvaluationService = Depends(get_evaluation_service)
    ) -> EvaluationResult:
        """
        Main evaluation endpoint.
        
        Receives offer and candidate data, executes the multi-agent workflow,
        and returns the evaluation result with compatibility score and decision.
        """
        try:
            result = await service.evaluate(request)
            return result
            
        except InvalidInputDataError as e:
            logger.error(f"Invalid input data: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
            
        except (AgentExecutionError, GraphExecutionError) as e:
            logger.error(f"Evaluation error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler for unhandled errors."""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error occurred"}
        )
    
    return app

