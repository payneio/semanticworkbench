"""
Template utilities for the Project Assistant.

This module provides utilities for working with assistant templates,
including detection of the active template and template-specific behavior.
"""

import logging

from semantic_workbench_assistant.assistant_app import ConversationContext


logger = logging.getLogger(__name__)


async def is_context_transfer_template(context: ConversationContext) -> bool:
    """
    Determines if the conversation is using the context transfer template.

    This is the centralized place to check whether the current template
    is the context transfer template, which helps ensure consistent behavior
    across the codebase.

    Args:
        context: The conversation context

    Returns:
        True if using context transfer template, False if using default template
    """
    from .chat import assistant_config

    try:
        # Get the configuration for this assistant
        config = await assistant_config.get(context.assistant)

        # Check if it's a context transfer configuration
        # The key indicator is track_progress=False which is only in context transfer
        is_context_transfer = not getattr(config, "track_progress", True)

        # Get additional context from metadata if available
        conversation = await context.get_conversation()
        if conversation and conversation.metadata:
            metadata = conversation.metadata

            # If metadata contains template info, use that
            if "template_id" in metadata:
                # Direct template ID is the most authoritative
                is_context_transfer = metadata["template_id"] == "context_transfer"
            elif "track_progress" in metadata:
                # Explicit track_progress setting overrides default
                is_context_transfer = not metadata["track_progress"]

        logger.debug(f"Template detection: is_context_transfer={is_context_transfer}")
        return is_context_transfer

    except Exception as e:
        # If there's an error detecting the template, assume default
        logger.warning(f"Error detecting template type: {e}")
        return False


async def get_template_name(context: ConversationContext) -> str:
    """
    Gets a human-readable name for the active template.

    Args:
        context: The conversation context

    Returns:
        "Context Transfer" for context transfer template, "Project Assistant" for default
    """
    is_context_transfer = await is_context_transfer_template(context)
    return "Context Transfer" if is_context_transfer else "Project Assistant"


async def get_template_id(context: ConversationContext) -> str:
    """
    Gets the internal template ID for the active template.

    Args:
        context: The conversation context

    Returns:
        "context_transfer" for context transfer template, "default" for default
    """
    is_context_transfer = await is_context_transfer_template(context)
    return "context_transfer" if is_context_transfer else "default"
