"""
Base configuration classes for Project Assistant.

This module defines the base configuration classes that are shared between
all configuration templates (default and context transfer).
"""

from typing import Annotated

import openai_client
from assistant_extensions.attachments import AttachmentsConfigModel
from content_safety.evaluators import CombinedContentSafetyEvaluatorConfig
from pydantic import BaseModel, ConfigDict, Field
from semantic_workbench_assistant.config import UISchema


class RequestConfig(BaseModel):
    """
    Configuration for LLM request parameters.

    This class configures the parameters used when making requests to the
    language model, including token limits and model selection.
    """

    model_config = ConfigDict(
        title="Response Generation",
        json_schema_extra={
            "required": ["max_tokens", "response_tokens", "openai_model"],
        },
    )

    max_tokens: Annotated[
        int,
        Field(
            title="Max Tokens",
            description=(
                "The maximum number of tokens to use for both the prompt and response. Current max supported by OpenAI"
                " is 128k tokens, but varies by model (https://platform.openai.com/docs/models)"
            ),
        ),
    ] = 50_000

    response_tokens: Annotated[
        int,
        Field(
            title="Response Tokens",
            description=(
                "The number of tokens to use for the response, will reduce the number of tokens available for the"
                " prompt. Current max supported by OpenAI is 4096 tokens (https://platform.openai.com/docs/models)"
            ),
        ),
    ] = 4_048

    openai_model: Annotated[
        str,
        Field(title="OpenAI Model", description="The OpenAI model to use for generating responses."),
    ] = "gpt-4o"


class BaseTeamConfig(BaseModel):
    """
    Base configuration for team members.

    This class defines parameters that control the behavior and UI
    for team member conversations in any template.
    """

    model_config = ConfigDict(
        title="Team Member Configuration",
        json_schema_extra={
            "required": ["welcome_message", "status_command"],
        },
    )

    welcome_message: Annotated[
        str,
        Field(
            title="Team Welcome Message",
            description="The message to display when a user joins a project as a Team member. Shown after successfully joining a project.",
        ),
        UISchema(widget="textarea"),
    ] = """# Welcome to Your Team Workspace

You've joined this project as a team member. This is your personal workspace for collaborating on the project.

**What you can do here:**
- View the project brief, goals, and current status
- Ask questions and get assistance from the AI assistant
- Create information requests when you need input from the project coordinator
- Update project progress and mark success criteria as completed
- Access files and resources shared by the coordinator

To get started, try the following:
- Type `/project-status` to view the current project status
- Send a message to get assistance from the AI
- Upload files to share them with other team members

Your contributions will help drive the project forward and achieve its goals."""

    status_command: Annotated[
        str,
        Field(
            title="Status Command",
            description="The command project participants can use to check project status (without the slash).",
        ),
    ] = "project-status"


class BaseCoordinatorConfig(BaseModel):
    """
    Base configuration for project coordinators.

    This class defines parameters that control the behavior and UI
    for coordinator conversations in any template.
    """

    model_config = ConfigDict(
        title="Coordinator Configuration",
        json_schema_extra={
            "required": ["welcome_message", "prompt_for_files"],
        },
    )

    welcome_message: Annotated[
        str,
        Field(
            title="Coordinator Welcome Message",
            description="The message to display when a coordinator starts a new project. {share_url} will be replaced with the actual URL.",
        ),
        UISchema(widget="textarea"),
    ] = """# Welcome to the Project Assistant

This is your coordinator workspace where you'll define, structure, and monitor your project.

**To invite team members to your project, copy and share this link with them:**
[Join Team Workspace]({share_url})

**As the coordinator, you can:**
- Create and refine your project brief with clear goals and success criteria
- Share files and resources with your team
- Respond to information requests from team members
- Monitor overall project progress
- Keep track of all project participants

**Getting started:**
1. Define your project brief with a clear description and purpose
2. Add specific goals and measurable success criteria
3. Upload any relevant files your team will need
4. Invite team members using the link above
5. Mark the project as "ready for working" when initial setup is complete

I'll guide you through each step of the process. Let's begin by creating a project brief with your goals and key details."""

    prompt_for_files: Annotated[
        str,
        Field(
            title="File Upload Prompt",
            description="The message used to prompt project coordinators to upload relevant files.",
        ),
        UISchema(widget="textarea"),
    ] = """To help your team succeed, consider uploading relevant project materials:

**Useful files to share:**
- Project requirements or specifications
- Reference documents or research
- Design assets or mockups
- Existing code or data samples
- Templates or examples

Simply drag and drop files into this conversation or click the attachment icon. These files will be available to all team members and will help provide valuable context for your project."""

    list_participants_command: Annotated[
        str,
        Field(
            title="List Participants Command",
            description="The command project coordinators can use to list all participants (without the slash).",
        ),
    ] = "list-participants"


class BaseAssistantConfigModel(BaseModel):
    """
    Base configuration for all assistant templates.

    This class defines the core configuration parameters that are common
    across all assistant templates. It serves as the foundation for
    template-specific configurations.

    Every required field from AssistantConfigModel needs to be defined here
    to ensure type compatibility with the BaseModelAssistantConfig.
    """

    # Core settings
    enable_debug_output: Annotated[
        bool,
        Field(
            title="Include Debug Output",
            description="Include debug output on conversation messages.",
        ),
    ] = False

    # Prompt configuration
    instruction_prompt: Annotated[
        str,
        Field(
            title="Instruction Prompt",
            description="The prompt used to instruct the behavior of the AI assistant.",
        ),
        UISchema(widget="textarea"),
    ] = ""

    guardrails_prompt: Annotated[
        str,
        Field(
            title="Guardrails Prompt",
            description="The prompt used to inform the AI assistant about the guardrails to follow.",
        ),
        UISchema(widget="textarea"),
    ] = ""

    # Service configuration
    service_config: openai_client.ServiceConfig

    request_config: Annotated[
        RequestConfig,
        Field(
            title="Request Configuration",
            description="Configuration for LLM request parameters.",
        ),
    ] = RequestConfig()

    content_safety_config: Annotated[
        CombinedContentSafetyEvaluatorConfig,
        Field(
            title="Content Safety Configuration",
            description="Configuration for content safety evaluation.",
        ),
    ] = CombinedContentSafetyEvaluatorConfig()

    attachments_config: Annotated[
        AttachmentsConfigModel,
        Field(
            title="Attachments Configuration",
            description="Configuration for handling file attachments in messages.",
        ),
    ] = AttachmentsConfigModel()

    # Project features
    auto_sync_files: Annotated[
        bool,
        Field(
            title="Auto-sync Files",
            description="Automatically synchronize files between linked conversations.",
        ),
    ] = True

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
            description="Proactively guide users through context building.",
        ),
    ] = True

    # Role-specific configurations
    coordinator_config: Annotated[
        BaseCoordinatorConfig,
        Field(
            title="Coordinator Configuration",
            description="Configuration for coordinator role.",
        ),
    ] = BaseCoordinatorConfig()

    team_config: Annotated[
        BaseTeamConfig,
        Field(
            title="Team Configuration",
            description="Configuration for team member role.",
        ),
    ] = BaseTeamConfig()
