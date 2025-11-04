"""
Dependency injection container for the application
"""

import logging
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from ..config import Settings
from ..agents import AgentFactory
from ..graph import GraphBuilder
from ..services import EvaluationService


logger = logging.getLogger(__name__)


class DependencyContainer:
    """Container for managing application dependencies."""
    
    def __init__(self):
        self.settings: Optional[Settings] = None
        self.llm: Optional[ChatOpenAI] = None
        self.agent_factory: Optional[AgentFactory] = None
        self.graph: Optional[Any] = None
        self.evaluation_service: Optional[EvaluationService] = None
    
    async def initialize(self, settings: Settings):
        """Initialize all dependencies."""
        logger.info("Initializing application dependencies...")
        
        self.settings = settings
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key
        )
        logger.info(f"LLM initialized: {settings.openai_model}")
        
        # Initialize agent factory
        self.agent_factory = AgentFactory(self.llm)
        
        # Build graph
        graph_builder = GraphBuilder(self.agent_factory)
        self.graph = graph_builder.build_graph()
        
        # Initialize evaluation service
        self.evaluation_service = EvaluationService(self.graph)
        
        logger.info("All dependencies initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up application resources...")
        # Add cleanup logic if needed


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container

