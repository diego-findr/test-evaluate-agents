"""API module"""

from .dependencies import DependencyContainer, get_container
from .routes import create_app

__all__ = ["DependencyContainer", "get_container", "create_app"]

