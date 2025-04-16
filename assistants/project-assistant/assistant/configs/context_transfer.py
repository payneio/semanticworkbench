"""
Context Transfer configuration for Project Assistant.

This module defines the Context Transfer configuration template, which focuses on
knowledge sharing and exploration without project management or progress tracking.
"""

from textwrap import dedent
from typing import Annotated

from pydantic import Field
from semantic_workbench_assistant.config import UISchema

from .base import (
    BaseAssistantConfigModel,
    BaseCoordinatorConfig,
    BaseTeamConfig,
    RequestConfig,
)


class ContextTransferCoordinatorConfig(BaseCoordinatorConfig):
    """
    Coordinator configuration specific to context transfer template.

    Configures the coordinator experience for knowledge sharing without
    progress tracking or project management overhead.
    """

    welcome_message: Annotated[
        str,
        Field(
            title="Context Transfer Coordinator Welcome Message",
            description="The message to display when a coordinator starts a new knowledge transfer project. {share_url} will be replaced with the actual URL.",
        ),
        UISchema(widget="textarea"),
    ] = """# Welcome to Context Transfer

Welcome! I'm here to help you capture and share complex information in a way that others can easily explore and understand. Think of me as your personal knowledge bridge - I'll help you:

- 📚 Organize your thoughts - whether from documents, code, research papers, or brainstorming sessions
- 🔄 Establish shared understanding - I'll ask questions to ensure we're aligned on what matters most
- 🔍 Make your knowledge interactive - so others can explore the "why" behind decisions, alternatives considered, and deeper context
- 🔗 Create shareable experiences - share this link with others for a self-service way to explore your knowledge:
[Explore Knowledge Space]({share_url})

Simply share your content or ideas, tell me who needs to understand them, and what aspects you want to highlight. We'll work together to create an interactive knowledge space that others can explore at their own pace.

What knowledge would you like to transfer today?"""

    prompt_for_files: Annotated[
        str,
        Field(
            title="File Upload Prompt",
            description="The message used to prompt context organizers to upload relevant files.",
        ),
        UISchema(widget="textarea"),
    ] = """To enrich the knowledge space with comprehensive information, consider sharing relevant materials:

**Valuable content to include:**
- Documentation or technical papers
- Code samples or repositories
- Diagrams, charts, or visual explanations
- Research findings or analysis
- Meeting notes or decision records
- FAQs or common questions

Simply drag and drop files into this conversation or click the attachment icon. I'll help extract and organize the key insights from these materials to create a rich, interactive knowledge space that others can explore."""


class ContextTransferTeamConfig(BaseTeamConfig):
    """
    Team configuration specific to context transfer template.

    Configures the team member experience for exploring knowledge
    without progress tracking or project management overhead.
    """

    welcome_message: Annotated[
        str,
        Field(
            title="Context Transfer Team Welcome Message",
            description="The message to display when a user joins as a Team member in context transfer mode.",
        ),
        UISchema(widget="textarea"),
    ] = """# Welcome to the Knowledge Space

You now have access to a curated knowledge collection that has been prepared specifically for you.

**What makes this Knowledge Space special:**
- It contains organized information from someone with expertise in this area
- You can explore complex topics through interactive conversation
- The AI assistant can explain concepts and answer your questions about the shared knowledge
- You can dig deeper into any aspect that interests you

**How to explore effectively:**
- Type `/knowledge-status` to see an overview of available information
- Ask specific questions about topics in the knowledge space
- Request clarification on anything that's unclear
- Create knowledge requests if you need information that isn't covered yet

This is your personal conversation for exploring the shared knowledge. Feel free to take your time and explore at your own pace."""

    status_command: Annotated[
        str,
        Field(
            title="Status Command",
            description="The command participants can use to check knowledge context (without the slash).",
        ),
    ] = "knowledge-status"


class ContextTransferConfigModel(BaseAssistantConfigModel):
    """
    Context Transfer configuration.

    This configuration enables knowledge sharing and exploration without
    project management overhead. It focuses on building a comprehensive
    knowledge space that others can explore interactively.
    """

    instruction_prompt: Annotated[
        str,
        Field(
            title="Instruction Prompt",
            description="The prompt used to instruct the behavior of the AI assistant.",
        ),
        UISchema(widget="textarea"),
    ] = dedent("""
        You are an AI context transfer assistant that helps users capture and share complex information in a way that others can easily explore and understand. You're designed to:

        1. Help users organize knowledge from documents, code, research, or brainstorming sessions
        2. Establish shared understanding through careful questioning
        3. Make knowledge interactive for recipients, so they can explore deeper context
        4. Create shareable experiences that give others a self-service way to explore your knowledge

        You should focus on helping users clarify their thoughts and structure information effectively. Ask questions to understand what aspects of their knowledge are most important to convey.
        """).strip()

    guardrails_prompt: Annotated[
        str,
        Field(
            title="Guardrails Prompt",
            description="The safety guardrails for the context transfer assistant.",
        ),
        UISchema(widget="textarea"),
    ] = dedent("""
        You are a helpful AI assistant focused on facilitating knowledge transfer and exploration. 
        
        Safety Guidelines:
        1. Prioritize user safety and wellbeing above all else
        2. Decline to engage with harmful, illegal, or unethical requests
        3. Be thoughtful, balanced, and nuanced in your responses
        4. Acknowledge limitations in your knowledge and suggest alternatives
        5. Protect user privacy and confidentiality
        6. Never generate misleading or made-up information
        
        Your purpose is to help organize and share knowledge effectively. Stay focused on this goal
        and decline respectfully if asked to perform tasks outside this scope.
        """).strip()

    request_config: Annotated[
        RequestConfig,
        Field(
            title="Request Configuration",
            description="Configuration for LLM request parameters, optimized for knowledge exploration.",
        ),
    ] = RequestConfig(
        openai_model="gpt-4o",
        max_tokens=128_000,
        response_tokens=16_384,
    )

    # Context transfer template specific settings
    track_progress: Annotated[
        bool,
        Field(
            title="Track Progress",
            description="Track project progress with goals, criteria completion, and overall project state.",
            validation_alias="track_progress",
        ),
    ] = False  # Key indicator for context transfer template

    proactive_guidance: Annotated[
        bool,
        Field(
            title="Proactive Guidance",
            description="Proactively guide context organizers through knowledge structuring.",
        ),
    ] = True

    coordinator_config: Annotated[
        BaseCoordinatorConfig,  # Use the base type for type compatibility
        Field(
            title="Context Transfer Coordinator Configuration",
            description="Configuration for coordinators in context transfer mode.",
        ),
    ] = ContextTransferCoordinatorConfig()

    team_config: Annotated[
        BaseTeamConfig,  # Use the base type for type compatibility
        Field(
            title="Context Transfer Team Configuration",
            description="Configuration for team members in context transfer mode.",
        ),
    ] = ContextTransferTeamConfig()
