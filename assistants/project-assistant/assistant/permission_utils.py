"""
Permission utilities for the Project Assistant.

This module provides utilities for validating permissions based on
both user roles and the active template type. It integrates template
detection with role-based permissions to provide a comprehensive
permission system.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from semantic_workbench_assistant.assistant_app import ConversationContext

from .logging import logger
from .project_storage import ProjectRole
from .role_utils import get_conversation_role
from .template_utils import is_context_transfer_template


class PermissionScope(str, Enum):
    """Enum defining permission scopes for actions in the Project Assistant."""

    # Project Management
    PROJECT_CREATE = "project.create"
    PROJECT_MODIFY = "project.modify"
    PROJECT_VIEW = "project.view"
    PROJECT_DELETE = "project.delete"

    # Brief Management
    BRIEF_CREATE = "brief.create"
    BRIEF_MODIFY = "brief.modify"
    BRIEF_VIEW = "brief.view"

    # Goal Management
    GOAL_CREATE = "goal.create"
    GOAL_MODIFY = "goal.modify"
    GOAL_VIEW = "goal.view"
    GOAL_COMPLETE = "goal.complete"

    # Request Management
    REQUEST_CREATE = "request.create"
    REQUEST_MODIFY = "request.modify"
    REQUEST_VIEW = "request.view"
    REQUEST_RESOLVE = "request.resolve"

    # Status Management
    STATUS_UPDATE = "status.update"
    STATUS_VIEW = "status.view"

    # Whiteboard Management
    WHITEBOARD_MODIFY = "whiteboard.modify"
    WHITEBOARD_VIEW = "whiteboard.view"

    # Team Management
    TEAM_INVITE = "team.invite"
    TEAM_VIEW = "team.view"

    # File Management
    FILE_UPLOAD = "file.upload"
    FILE_VIEW = "file.view"
    FILE_SYNC = "file.sync"


# Define role-based permissions for the default template
DEFAULT_COORDINATOR_PERMISSIONS: Set[PermissionScope] = {
    # Project Management
    PermissionScope.PROJECT_CREATE,
    PermissionScope.PROJECT_MODIFY,
    PermissionScope.PROJECT_VIEW,
    # Brief Management
    PermissionScope.BRIEF_CREATE,
    PermissionScope.BRIEF_MODIFY,
    PermissionScope.BRIEF_VIEW,
    # Goal Management
    PermissionScope.GOAL_CREATE,
    PermissionScope.GOAL_MODIFY,
    PermissionScope.GOAL_VIEW,
    # Request Management
    PermissionScope.REQUEST_VIEW,
    PermissionScope.REQUEST_RESOLVE,
    # Status Management
    PermissionScope.STATUS_UPDATE,
    PermissionScope.STATUS_VIEW,
    # Whiteboard Management
    PermissionScope.WHITEBOARD_MODIFY,
    PermissionScope.WHITEBOARD_VIEW,
    # Team Management
    PermissionScope.TEAM_INVITE,
    PermissionScope.TEAM_VIEW,
    # File Management
    PermissionScope.FILE_UPLOAD,
    PermissionScope.FILE_VIEW,
}

DEFAULT_TEAM_PERMISSIONS: Set[PermissionScope] = {
    # Project Management
    PermissionScope.PROJECT_VIEW,
    # Brief Management
    PermissionScope.BRIEF_VIEW,
    # Goal Management
    PermissionScope.GOAL_VIEW,
    PermissionScope.GOAL_COMPLETE,
    # Request Management
    PermissionScope.REQUEST_CREATE,
    PermissionScope.REQUEST_MODIFY,
    PermissionScope.REQUEST_VIEW,
    # Status Management
    PermissionScope.STATUS_UPDATE,
    PermissionScope.STATUS_VIEW,
    # Whiteboard Management
    PermissionScope.WHITEBOARD_VIEW,
    # Team Management
    PermissionScope.TEAM_VIEW,
    # File Management
    PermissionScope.FILE_UPLOAD,
    PermissionScope.FILE_VIEW,
    PermissionScope.FILE_SYNC,
}

# Define role-based permissions for the context transfer template
CONTEXT_TRANSFER_COORDINATOR_PERMISSIONS: Set[PermissionScope] = {
    # Project Management
    PermissionScope.PROJECT_CREATE,
    PermissionScope.PROJECT_MODIFY,
    PermissionScope.PROJECT_VIEW,
    # Brief Management - limited in context transfer
    PermissionScope.BRIEF_CREATE,
    PermissionScope.BRIEF_VIEW,
    # Request Management - renamed as knowledge requests
    PermissionScope.REQUEST_VIEW,
    PermissionScope.REQUEST_RESOLVE,
    # Whiteboard Management - primary focus in context transfer
    PermissionScope.WHITEBOARD_MODIFY,
    PermissionScope.WHITEBOARD_VIEW,
    # Team Management
    PermissionScope.TEAM_INVITE,
    PermissionScope.TEAM_VIEW,
    # File Management
    PermissionScope.FILE_UPLOAD,
    PermissionScope.FILE_VIEW,
}

CONTEXT_TRANSFER_TEAM_PERMISSIONS: Set[PermissionScope] = {
    # Project Management
    PermissionScope.PROJECT_VIEW,
    # Brief Management
    PermissionScope.BRIEF_VIEW,
    # Request Management - renamed as knowledge requests
    PermissionScope.REQUEST_CREATE,
    PermissionScope.REQUEST_VIEW,
    # Whiteboard Management - primary focus in context transfer
    PermissionScope.WHITEBOARD_VIEW,
    # Team Management
    PermissionScope.TEAM_VIEW,
    # File Management
    PermissionScope.FILE_VIEW,
    PermissionScope.FILE_SYNC,
}


async def get_permissions(context: ConversationContext) -> Set[PermissionScope]:
    """
    Gets the permissions for the current conversation based on role and template.

    This function:
    1. Detects the conversation's role using role_utils
    2. Detects if the conversation is using the context transfer template
    3. Returns the appropriate permission set based on role and template

    Args:
        context: The conversation context

    Returns:
        A set of PermissionScope values representing the allowed actions
    """
    # Detect role and template
    role = await get_conversation_role(context)
    is_context_transfer = await is_context_transfer_template(context)

    # If no role detected, return empty permission set
    if not role:
        logger.warning("No role detected, returning empty permission set")
        return set()

    # Select permission set based on role and template
    if role == ProjectRole.COORDINATOR:
        if is_context_transfer:
            return CONTEXT_TRANSFER_COORDINATOR_PERMISSIONS
        else:
            return DEFAULT_COORDINATOR_PERMISSIONS
    elif role == ProjectRole.TEAM:
        if is_context_transfer:
            return CONTEXT_TRANSFER_TEAM_PERMISSIONS
        else:
            return DEFAULT_TEAM_PERMISSIONS

    # Should never reach here, but just in case
    logger.error(f"Unknown role {role}, returning empty permission set")
    return set()


async def has_permission(context: ConversationContext, permission: PermissionScope) -> bool:
    """
    Checks if the current conversation has a specific permission.

    Args:
        context: The conversation context
        permission: The permission to check

    Returns:
        True if the conversation has the permission, False otherwise
    """
    permissions = await get_permissions(context)
    return permission in permissions


async def validate_permissions(
    context: ConversationContext, required_permissions: List[PermissionScope]
) -> Tuple[bool, Optional[PermissionScope]]:
    """
    Validates that the current conversation has all the required permissions.

    Args:
        context: The conversation context
        required_permissions: List of permissions to check

    Returns:
        Tuple of (has_all_permissions, first_missing_permission)
    """
    permissions = await get_permissions(context)

    for permission in required_permissions:
        if permission not in permissions:
            return False, permission

    return True, None


async def get_missing_permission_message(context: ConversationContext, permission: PermissionScope) -> str:
    """
    Gets a user-friendly message explaining why a permission is not available.

    This is used to provide helpful feedback when a user tries to perform
    an action they don't have permission for.

    Args:
        context: The conversation context
        permission: The missing permission

    Returns:
        A user-friendly message explaining the permission issue
    """
    role = await get_conversation_role(context)
    is_context_transfer = await is_context_transfer_template(context)

    # Create a mapping of permissions to explanations
    permission_messages: Dict[PermissionScope, str] = {
        # Project Management
        PermissionScope.PROJECT_CREATE: "Only coordinators can create projects.",
        PermissionScope.PROJECT_MODIFY: "Only coordinators can modify project settings.",
        # Brief Management
        PermissionScope.BRIEF_CREATE: "Only coordinators can create project briefs.",
        PermissionScope.BRIEF_MODIFY: "Only coordinators can modify project briefs.",
        # Goal Management
        PermissionScope.GOAL_CREATE: "Only coordinators can create project goals.",
        PermissionScope.GOAL_MODIFY: "Only coordinators can modify project goals.",
        PermissionScope.GOAL_COMPLETE: "Only team members can mark goals as completed.",
        # Request Management
        PermissionScope.REQUEST_CREATE: "Only team members can create information requests.",
        PermissionScope.REQUEST_MODIFY: "Only the creator can modify information requests.",
        PermissionScope.REQUEST_RESOLVE: "Only coordinators can resolve information requests.",
        # Status Management
        PermissionScope.STATUS_UPDATE: "Only team members can update project status.",
        # Whiteboard Management
        PermissionScope.WHITEBOARD_MODIFY: "Only coordinators can modify the whiteboard.",
        # Team Management
        PermissionScope.TEAM_INVITE: "Only coordinators can invite team members.",
    }

    # Add template-specific context if needed
    if is_context_transfer:
        # Customize messages for context transfer template
        context_transfer_messages = {
            PermissionScope.GOAL_CREATE: "Goal creation is not available in Context Transfer mode.",
            PermissionScope.GOAL_MODIFY: "Goal modification is not available in Context Transfer mode.",
            PermissionScope.GOAL_COMPLETE: "Goal completion is not available in Context Transfer mode.",
            PermissionScope.STATUS_UPDATE: "Status updates are not available in Context Transfer mode.",
        }

        # Update the messages with context transfer versions
        permission_messages.update(context_transfer_messages)

    # Get the message for this permission
    message = permission_messages.get(
        permission, f"You don't have permission to perform this action (missing: {permission.value})."
    )

    # Add role context
    role_name = "coordinator" if role == ProjectRole.COORDINATOR else "team member"
    template_name = "Context Transfer" if is_context_transfer else "Project Assistant"

    return f"{message} You are currently in {role_name} role using the {template_name} template."


# Command-specific permission requirements
COMMAND_PERMISSIONS: Dict[str, List[PermissionScope]] = {
    # Project Management
    "create-brief": [PermissionScope.BRIEF_CREATE],
    "update-brief": [PermissionScope.BRIEF_MODIFY],
    # Goal Management
    "add-goal": [PermissionScope.GOAL_CREATE],
    "mark-criterion-completed": [PermissionScope.GOAL_COMPLETE],
    # Request Management
    "request-info": [PermissionScope.REQUEST_CREATE],
    "resolve-request": [PermissionScope.REQUEST_RESOLVE],
    # Status Management
    "update-status": [PermissionScope.STATUS_UPDATE],
    # Team Management
    "invite": [PermissionScope.TEAM_INVITE],
    # File Management
    "sync-files": [PermissionScope.FILE_SYNC],
}


async def check_command_permission(context: ConversationContext, command_name: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if the current conversation has permission to run a specific command.

    Args:
        context: The conversation context
        command_name: The command to check permission for

    Returns:
        Tuple of (has_permission, error_message)
    """
    # Strip any prefix slash
    if command_name.startswith("/"):
        command_name = command_name[1:]

    # Get required permissions for this command
    required_permissions = COMMAND_PERMISSIONS.get(command_name, [])

    # If no permissions defined, assume allowed
    if not required_permissions:
        return True, None

    # Check each permission
    has_all, missing = await validate_permissions(context, required_permissions)

    if not has_all and missing:
        error_message = await get_missing_permission_message(context, missing)
        return False, error_message

    return True, None
