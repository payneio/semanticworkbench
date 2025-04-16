"""
Configuration models for the Project Assistant.

This package contains all configuration models for different templates:
- Base classes that are shared by all templates
- Default project assistant template with full project management
- Context transfer template for knowledge sharing without progress tracking
"""

from .base import (
    BaseAssistantConfigModel,
    BaseCoordinatorConfig,
    BaseTeamConfig,
    RequestConfig,
)
from .context_transfer import (
    ContextTransferConfigModel,
    ContextTransferCoordinatorConfig,
    ContextTransferTeamConfig,
)
from .default import AssistantConfigModel, CoordinatorConfig, TeamConfig

__all__ = [
    # Base configuration classes
    "BaseAssistantConfigModel",
    "BaseCoordinatorConfig",
    "BaseTeamConfig",
    "RequestConfig",
    # Default template classes
    "AssistantConfigModel",
    "CoordinatorConfig",
    "TeamConfig",
    # Context transfer template classes
    "ContextTransferConfigModel",
    "ContextTransferCoordinatorConfig",
    "ContextTransferTeamConfig",
]
