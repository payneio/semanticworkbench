"""
Role utilities for the Project Assistant.

This module provides utilities for working with conversation roles,
including detection, persistence, and template-specific role management.
"""

from typing import Optional, Tuple

from semantic_workbench_assistant.assistant_app import ConversationContext

from .logging import logger
from .project_storage import ConversationProjectManager, ProjectRole
from .template_utils import is_context_transfer_template


async def get_conversation_role(context: ConversationContext) -> Optional[ProjectRole]:
    """
    Gets the role of the current conversation with improved detection and caching.

    This function centralizes role detection logic, combining information from:
    1. File-based storage (handled by ConversationProjectManager)
    2. Conversation metadata (which may be more up-to-date)
    3. Any cached role information for performance

    It ensures that the role is consistent across different data sources and
    persists any corrections to file storage if needed.

    Args:
        context: The conversation context

    Returns:
        The detected ProjectRole (COORDINATOR or TEAM), or None if not in a project
    """
    # First, try to get role from conversation metadata (fastest and usually up-to-date)
    try:
        conversation = await context.get_conversation()
        metadata = conversation.metadata if conversation else {}

        metadata_role = metadata.get("project_role")
        if metadata_role in ["coordinator", "team"]:
            role_from_metadata = ProjectRole(metadata_role)
            logger.debug(f"Role from metadata: {role_from_metadata}")
        else:
            role_from_metadata = None
            logger.debug("No valid role found in metadata")
    except Exception as e:
        logger.warning(f"Error getting role from metadata: {e}")
        role_from_metadata = None

    # Next, get role from file storage (more persistent, but might be out of sync)
    try:
        role_from_storage = await ConversationProjectManager.get_conversation_role(context)
        logger.debug(f"Role from storage: {role_from_storage}")
    except Exception as e:
        logger.warning(f"Error getting role from storage: {e}")
        role_from_storage = None

    # If both sources agree, we're done
    if role_from_metadata and role_from_storage and role_from_metadata == role_from_storage:
        logger.debug(f"Role consistent across sources: {role_from_metadata}")
        return role_from_metadata

    # If only one source has a role, verify it's valid and update the other source
    if role_from_metadata and not role_from_storage:
        # Verify the metadata role by checking if we have a project association
        project_id = await ConversationProjectManager.get_associated_project_id(context)
        if project_id:
            # Metadata role is valid, update storage to match
            logger.info(f"Updating storage with role from metadata: {role_from_metadata}")
            await ConversationProjectManager.set_conversation_role(context, project_id, role_from_metadata)
            return role_from_metadata
        else:
            logger.warning("Metadata contains role but no project association found")
            return None

    if role_from_storage and not role_from_metadata:
        # Storage role appears valid, update metadata to match
        project_id = await ConversationProjectManager.get_associated_project_id(context)
        try:
            conversation = await context.get_conversation()
            if project_id and conversation and conversation.metadata:
                logger.info(f"Updating metadata with role from storage: {role_from_storage}")
                conversation.metadata["project_role"] = role_from_storage.value
                # We don't need to explicitly save metadata - it's updated in the conversation object
                return role_from_storage
        except Exception as e:
            logger.warning(f"Error updating metadata with role from storage: {e}")

    # If sources disagree, we have a conflict to resolve
    if role_from_metadata and role_from_storage and role_from_metadata != role_from_storage:
        logger.warning(f"Role conflict: metadata={role_from_metadata}, storage={role_from_storage}")
        # Prefer storage as the source of truth
        project_id = await ConversationProjectManager.get_associated_project_id(context)
        try:
            conversation = await context.get_conversation()
            if project_id and conversation and conversation.metadata:
                logger.info(f"Resolving conflict by updating metadata to match storage: {role_from_storage}")
                conversation.metadata["project_role"] = role_from_storage.value
                return role_from_storage
        except Exception as e:
            logger.warning(f"Error resolving role conflict: {e}")

    # If we get here, we couldn't determine a role
    return None


async def get_role_info(context: ConversationContext) -> Tuple[Optional[ProjectRole], bool]:
    """
    Gets both the conversation role and template type in one call.

    This is a convenience function that combines role detection with template detection,
    for code that needs both pieces of information.

    Args:
        context: The conversation context

    Returns:
        Tuple of (role, is_context_transfer) where:
        - role: The ProjectRole (COORDINATOR, TEAM) or None if not in a project
        - is_context_transfer: True if using the context transfer template, False if using default
    """
    role = await get_conversation_role(context)
    is_context_transfer = await is_context_transfer_template(context)

    return role, is_context_transfer


async def is_authorized_for_action(context: ConversationContext, required_role: Optional[ProjectRole] = None) -> bool:
    """
    Checks if the current conversation is authorized for a specific role-based action.

    This function centralizes authorization logic, making it easier to enforce
    consistent access control across the codebase.

    Args:
        context: The conversation context
        required_role: The role required for authorization (None means any project role is ok)

    Returns:
        True if authorized, False otherwise
    """
    # Get the current role
    current_role = await get_conversation_role(context)

    # If we're not in a project, always unauthorized
    if not current_role:
        return False

    # If no specific role required, any project role is sufficient
    if required_role is None:
        return True

    # Otherwise, check if current role matches required role
    return current_role == required_role


async def is_coordinator(context: ConversationContext) -> bool:
    """
    Checks if the current conversation has the Coordinator role.

    This is a convenience function for the common case of checking
    for Coordinator permissions.

    Args:
        context: The conversation context

    Returns:
        True if Coordinator, False otherwise
    """
    role = await get_conversation_role(context)
    return role == ProjectRole.COORDINATOR


async def is_team_member(context: ConversationContext) -> bool:
    """
    Checks if the current conversation has the Team role.

    This is a convenience function for the common case of checking
    for Team permissions.

    Args:
        context: The conversation context

    Returns:
        True if Team member, False otherwise
    """
    role = await get_conversation_role(context)
    return role == ProjectRole.TEAM
