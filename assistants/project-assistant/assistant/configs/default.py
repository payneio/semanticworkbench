"""
Default configuration for Project Assistant.

This module defines the default configuration for the Project Assistant,
which includes full project management capabilities with goals, progress tracking,
and team collaboration features.
"""

from typing import Annotated

from pydantic import Field
from semantic_workbench_assistant.config import UISchema

from ..utils import load_text_include
from .base import (
    BaseAssistantConfigModel,
    BaseCoordinatorConfig,
    BaseTeamConfig,
    RequestConfig,
)


class CoordinatorConfig(BaseCoordinatorConfig):
    """
    Default coordinator configuration.

    Extends the base coordinator configuration with default project assistant specific
    settings and messages.
    """

    pass  # Uses all defaults from BaseCoordinatorConfig


class TeamConfig(BaseTeamConfig):
    """
    Default team member configuration.

    Extends the base team configuration with default project assistant specific
    settings and messages.
    """

    pass  # Uses all defaults from BaseTeamConfig


class AssistantConfigModel(BaseAssistantConfigModel):
    """
    Default Project Assistant configuration.

    This configuration enables full project management features including
    progress tracking, goal setting, and project lifecycle management.
    """

    instruction_prompt: Annotated[
        str,
        Field(
            title="Instruction Prompt",
            description="The prompt used to instruct the behavior of the AI assistant.",
        ),
        UISchema(widget="textarea"),
    ] = (
        "You are an AI project assistant that helps teams collaborate. You can facilitate file sharing between "
        "different conversations, allowing users to collaborate without being in the same conversation. "
        "Users can invite others with the /invite command, and you'll help synchronize files between conversations. "
        "In addition to text, you can also produce markdown, code snippets, and other types of content."
    )

    guardrails_prompt: Annotated[
        str,
        Field(
            title="Guardrails Prompt",
            description=(
                "The prompt used to inform the AI assistant about the guardrails to follow. Default value based upon"
                " recommendations from: [Microsoft OpenAI Service: System message templates]"
                "(https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/system-message"
                "#define-additional-safety-and-behavioral-guardrails)"
            ),
        ),
        UISchema(widget="textarea", enable_markdown_in_description=True),
    ] = load_text_include("guardrails_prompt.txt")

    request_config: Annotated[
        RequestConfig,
        Field(
            title="Request Configuration",
            description="Configuration for LLM request parameters.",
        ),
    ] = RequestConfig()

    # Default template specific settings
    track_progress: Annotated[
        bool,
        Field(
            title="Track Progress",
            description="Track project progress with goals, criteria completion, and overall project state.",
        ),
    ] = True

    proactive_guidance: Annotated[
        bool,
        Field(
            title="Proactive Guidance",
            description="Proactively guide project coordinators through context building.",
        ),
    ] = True

    coordinator_config: Annotated[
        BaseCoordinatorConfig,  # Use base type for type compatibility
        Field(
            title="Coordinator Configuration",
            description="Configuration for project coordinators.",
        ),
    ] = CoordinatorConfig()

    team_config: Annotated[
        BaseTeamConfig,  # Use base type for type compatibility
        Field(
            title="Team Configuration",
            description="Configuration for project team members.",
        ),
    ] = TeamConfig()
