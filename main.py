"""
MAS-Eval: Multi-Agent System for Candidate Evaluation Microservice

Main entry point for the application.
Run tests or start the FastAPI server.
"""

import asyncio
import sys

from src.config import get_settings, setup_logging
from src.api import create_app
from tests import test_evaluation_workflow


def main():
    """Main entry point."""
    # Setup logging
    settings = get_settings()
    setup_logging(settings)
    
    # Check if running tests or server
    if "--test" in sys.argv:
        # Run tests
        asyncio.run(test_evaluation_workflow())
    else:
        # Run server
        import uvicorn
        app = create_app()
        
        print("\n🚀 Launching FastAPI server...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info"
        )


if __name__ == "__main__":
    # Run test first, then launch server
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting test execution before launching server...")
        asyncio.run(test_evaluation_workflow())
        
        # Launch FastAPI server after tests
        import uvicorn
        app = create_app()
        
        logger.info("\n🚀 Launching FastAPI server...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

