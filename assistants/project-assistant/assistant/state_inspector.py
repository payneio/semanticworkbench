"""
Project assistant inspector state provider.

This module provides the state inspector provider for the project assistant
to display project information in the workbench UI's inspector panel.
"""

import logging
from typing import Any, List

from semantic_workbench_assistant.assistant_app import (
    AssistantConversationInspectorStateDataModel,
    ConversationContext,
)

from .project_data import RequestStatus
from .project_manager import ProjectManager
from .project_storage import ConversationProjectManager, ProjectRole

logger = logging.getLogger(__name__)


class ProjectInspectorStateProvider:
    """
    Inspector state provider for project information.

    This provider displays project-specific information in the inspector panel
    including project state, brief, goals, and information requests based on the
    user's role (Coordinator or Team).

    The content displayed is adapted based on the template configuration:
    - Default: Shows brief, goals, criteria, and request status
    - Context Transfer: Focuses on knowledge context without goals or progress tracking
    """

    display_name = "Project Status"
    # Default description - will be updated based on template
    description = "Current project information including brief, goals, and request status."

    def __init__(self, config_provider) -> None:
        self.config_provider = config_provider
        self.is_context_transfer = False

    async def get(self, context: ConversationContext) -> AssistantConversationInspectorStateDataModel:
        """
        Get project information for display in the inspector panel.

        Returns different information based on the conversation's role (Coordinator or Team),
        and adapts presentation based on the active template (default or context_transfer).

        The inspector dynamically composes information from multiple data sources:
        - ProjectInfo for basic metadata and state
        - ProjectBrief for goals and context
        - Information requests for collaborative needs
        - Whiteboard for knowledge context
        """
        # First check conversation metadata for setup status
        conversation = await context.get_conversation()
        metadata = conversation.metadata or {}

        # Check if metadata has setup info
        setup_complete = metadata.get("setup_complete", False)
        assistant_mode = metadata.get("assistant_mode", "setup")

        # Determine template type using the centralized utility
        from .template_utils import is_context_transfer_template

        self.is_context_transfer = await is_context_transfer_template(context)

        # Update description and display name based on template
        if self.is_context_transfer:
            self.description = "Context transfer information including knowledge resources and shared content."
            self.display_name = "Knowledge Context"
        else:
            self.description = "Current project information including brief, goals, and request status."
            self.display_name = "Project Status"

        # For backwards compatibility, also set track_progress
        track_progress = not self.is_context_transfer

        # Double-check with project storage/manager state
        if not setup_complete:
            # Check if we have a project role in storage
            role = await ConversationProjectManager.get_conversation_role(context)
            if role:
                # If we have a role in storage, consider setup complete
                setup_complete = True
                assistant_mode = role.value

                # Update local metadata too
                metadata["setup_complete"] = True
                metadata["assistant_mode"] = role.value
                metadata["project_role"] = role.value

                # Send conversation state event to save the metadata - using None for state values
                try:
                    from semantic_workbench_api_model.workbench_model import AssistantStateEvent

                    await context.send_conversation_state_event(
                        AssistantStateEvent(state_id="setup_complete", event="updated", state=None)
                    )
                    await context.send_conversation_state_event(
                        AssistantStateEvent(state_id="assistant_mode", event="updated", state=None)
                    )
                    await context.send_conversation_state_event(
                        AssistantStateEvent(state_id="project_role", event="updated", state=None)
                    )
                    logger.info(f"Updated metadata based on project role detection: {role.value}")
                except Exception as e:
                    logger.exception(f"Failed to update metadata: {e}")

        # If setup isn't complete, show setup instructions
        if not setup_complete and assistant_mode == "setup":
            setup_markdown = """# Project Assistant Setup

**Role Selection Required**

Before you can access project features, please specify your role:

- Use `/start` to create a new project as Coordinator
- Use `/join <project_id>` to join an existing project as Team member

Type `/help` for more information on available commands.

⚠️ **Note:** Setup is required before you can access any project features.
"""
            return AssistantConversationInspectorStateDataModel(data={"content": setup_markdown})

        # Continue with normal inspector display for already set up conversations
        # Determine the conversation's role and project
        project_id = await ConversationProjectManager.get_associated_project_id(context)
        if not project_id:
            return AssistantConversationInspectorStateDataModel(
                data={"content": "No active project. Start a conversation to create one."}
            )

        role = await ConversationProjectManager.get_conversation_role(context)
        if not role:
            return AssistantConversationInspectorStateDataModel(
                data={"content": "Role not assigned. Please restart the conversation."}
            )

        # Get project information
        brief = await ProjectManager.get_project_brief(context)
        project_info = await ProjectManager.get_project_info(context)

        # Generate nicely formatted markdown for the state panel
        if role == ProjectRole.COORDINATOR:
            # Format for Coordinator role
            markdown = await self._format_coordinator_markdown(
                project_id, role, brief, project_info, context, track_progress
            )
        else:
            # Format for Team role
            markdown = await self._format_team_markdown(project_id, role, brief, project_info, context, track_progress)

        return AssistantConversationInspectorStateDataModel(data={"content": markdown})

    async def _format_coordinator_markdown(
        self,
        project_id: str,
        role: ProjectRole,
        brief: Any,
        project_info: Any,
        context: ConversationContext,
        track_progress: bool,
    ) -> str:
        """Format project information as markdown for Coordinator role"""
        project_name = brief.project_name if brief else "Unnamed Project"

        # Build the markdown content
        lines: List[str] = []
        lines.append(f"# {project_name}")
        lines.append("")

        # Determine stage based on project status
        stage_label = "Planning Stage"
        if project_info and project_info.state:
            if project_info.state.value == "planning":
                stage_label = "Planning Stage"
            elif project_info.state.value == "ready_for_working":
                stage_label = "Ready for Working"
            elif project_info.state.value == "in_progress":
                stage_label = "Working Stage"
            elif project_info.state.value == "completed":
                stage_label = "Completed Stage"
            elif project_info.state.value == "aborted":
                stage_label = "Aborted Stage"

        lines.append("**Role:** Coordinator")
        lines.append(f"**Status:** {stage_label}")

        # Add status message if available
        if project_info and project_info.status_message:
            lines.append(f"**Status Message:** {project_info.status_message}")

        lines.append("")

        # Add project description and additional context if available
        if brief and brief.project_description:
            if self.is_context_transfer:
                lines.append("## Knowledge Context")
            else:
                lines.append("## Description")

            lines.append(brief.project_description)
            lines.append("")

            # In context transfer mode, show additional context in a dedicated section
            if self.is_context_transfer and brief.additional_context:
                lines.append("## Additional Context")
                lines.append(brief.additional_context)
                lines.append("")

        # Add goals section if available and progress tracking is enabled
        if track_progress and brief and brief.goals:
            lines.append("## Goals")
            for goal in brief.goals:
                criteria_complete = sum(1 for c in goal.success_criteria if c.completed)
                criteria_total = len(goal.success_criteria)
                lines.append(f"### {goal.name}")
                lines.append(goal.description)
                lines.append(f"**Progress:** {criteria_complete}/{criteria_total} criteria complete")

                if goal.success_criteria:
                    lines.append("")
                    lines.append("#### Success Criteria:")
                    for criterion in goal.success_criteria:
                        status_emoji = "✅" if criterion.completed else "⬜"
                        lines.append(f"- {status_emoji} {criterion.description}")
                lines.append("")

        # Add information requests section with template-specific formatting
        requests = await ProjectManager.get_information_requests(context)
        # Filter out resolved requests
        requests = [req for req in requests if req.status != RequestStatus.RESOLVED]

        # Determine section title based on template
        if self.is_context_transfer:
            request_section_title = "## Knowledge Requests"
            no_requests_message = "No open knowledge requests."
        else:
            request_section_title = "## Information Requests"
            no_requests_message = "No open information requests."

        if requests:
            lines.append(request_section_title)
            lines.append(f"**Open requests:** {len(requests)}")
            lines.append("")

            for request in requests[:5]:  # Show only first 5 requests
                priority_emoji = "🔴"
                if hasattr(request.priority, "value"):
                    priority = request.priority.value
                else:
                    priority = request.priority

                if priority == "low":
                    priority_emoji = "🔹"
                elif priority == "medium":
                    priority_emoji = "🔶"
                elif priority == "high":
                    priority_emoji = "🔴"
                elif priority == "critical":
                    priority_emoji = "⚠️"

                lines.append(f"{priority_emoji} **{request.title}** ({request.status})")

                # In project assistant mode, show request ID for resolution
                # In context transfer mode, focus on description
                if self.is_context_transfer:
                    lines.append(f"  *{request.description}*")
                else:
                    lines.append(f"  **Request ID for resolution:** `{request.request_id}`")

                lines.append("")

            # For projects with many requests, add a note about viewing all
            if len(requests) > 5:
                lines.append(f"*...and {len(requests) - 5} more requests*")
                lines.append("")
        else:
            lines.append(request_section_title)
            lines.append(no_requests_message)
            lines.append("")

        # Display share URL as invitation information
        if self.is_context_transfer:
            lines.append("## Share Knowledge Context")
        else:
            lines.append("## Project Invitation")

        lines.append("")

        # Get share URL from the project info
        share_url = None
        try:
            # Get project info which contains the share URL
            project_info = await ProjectManager.get_project_info(context, project_id)
            if project_info and project_info.share_url:
                share_url = project_info.share_url
                logger.info(f"Retrieved share URL from project info: {share_url}")
        except Exception as e:
            logger.warning(f"Error retrieving share URL from project info: {e}")

        # Fallback to metadata if needed
        if not share_url:
            conversation = await context.get_conversation()
            metadata = conversation.metadata or {}
            share_url = metadata.get("team_conversation_share_url")
            if share_url:
                logger.info(f"Retrieved share URL from metadata: {share_url}")

        if share_url:
            # Display the share URL as a properly formatted link
            lines.append("### Team Conversation Invitation Link")
            lines.append("**Share this link with your team members:**")
            lines.append(f"[Join Team Conversation]({share_url})")
            lines.append("")
            lines.append("The link never expires and can be used by multiple team members.")
        else:
            # Display that share URL is not available yet
            lines.append("### Team Conversation Share Link")
            lines.append("🔄 **Creating team conversation...**")
            lines.append("")
            lines.append("A shareable link for inviting team members will appear here soon.")
            lines.append("This link will appear after the project setup is complete.")

        lines.append("")

        return "\n".join(lines)

    async def _format_team_markdown(
        self,
        project_id: str,
        role: ProjectRole,
        brief: Any,
        project_info: Any,
        context: ConversationContext,
        track_progress: bool,
    ) -> str:
        """Format project information as markdown for Team role"""
        project_name = brief.project_name if brief else "Unnamed Project"

        # Build the markdown content
        lines: List[str] = []
        lines.append(f"# {project_name}")
        lines.append("")

        # Determine stage based on project status
        stage_label = "Working Stage"
        if project_info and project_info.state:
            if project_info.state.value == "planning":
                stage_label = "Planning Stage"
            elif project_info.state.value == "ready_for_working":
                stage_label = "Working Stage"
            elif project_info.state.value == "in_progress":
                stage_label = "Working Stage"
            elif project_info.state.value == "completed":
                stage_label = "Completed Stage"
            elif project_info.state.value == "aborted":
                stage_label = "Aborted Stage"

        lines.append(f"**Role:** Team ({stage_label})")
        lines.append(f"**Status:** {stage_label}")

        # Add status message if available
        if project_info and project_info.status_message:
            lines.append(f"**Status Message:** {project_info.status_message}")

        lines.append("")

        # Add project description and additional context if available
        if brief and brief.project_description:
            if self.is_context_transfer:
                lines.append("## Knowledge Context")
            else:
                lines.append("## Project Brief")

            lines.append(brief.project_description)
            lines.append("")

            # In context transfer mode, show additional context in a dedicated section
            if self.is_context_transfer and brief.additional_context:
                lines.append("## Additional Context")
                lines.append(brief.additional_context)
                lines.append("")

        # Add goals section with checkable criteria if progress tracking is enabled
        if track_progress and brief and brief.goals:
            lines.append("## Objectives")
            for goal in brief.goals:
                criteria_complete = sum(1 for c in goal.success_criteria if c.completed)
                criteria_total = len(goal.success_criteria)
                lines.append(f"### {goal.name}")
                lines.append(goal.description)
                lines.append(f"**Progress:** {criteria_complete}/{criteria_total} criteria complete")

                if goal.success_criteria:
                    lines.append("")
                    lines.append("#### Success Criteria:")
                    for criterion in goal.success_criteria:
                        status_emoji = "✅" if criterion.completed else "⬜"
                        completion_info = ""
                        if criterion.completed and hasattr(criterion, "completed_at") and criterion.completed_at:
                            completion_info = f" (completed on {criterion.completed_at.strftime('%Y-%m-%d')})"
                        lines.append(f"- {status_emoji} {criterion.description}{completion_info}")
                lines.append("")

        # Add my information requests section with template-specific formatting
        requests = await ProjectManager.get_information_requests(context)
        my_requests = [r for r in requests if r.conversation_id == str(context.id)]

        # Determine section titles based on template
        if self.is_context_transfer:
            request_section_title = "## My Knowledge Requests"
            no_requests_message = "You haven't created any knowledge requests yet."
            other_requests_title = "Knowledge Questions"
        else:
            request_section_title = "## My Information Requests"
            no_requests_message = "You haven't created any information requests yet."
            other_requests_title = "Information Requests"

        if my_requests:
            lines.append(request_section_title)
            pending = [r for r in my_requests if r.status != "resolved"]
            resolved = [r for r in my_requests if r.status == "resolved"]

            if pending:
                lines.append("### Pending Requests:")
                for request in pending[:3]:  # Show only first 3 pending requests
                    priority_emoji = "🔶"  # default medium
                    if hasattr(request.priority, "value"):
                        priority = request.priority.value
                    else:
                        priority = request.priority

                    if priority == "low":
                        priority_emoji = "🔹"
                    elif priority == "medium":
                        priority_emoji = "🔶"
                    elif priority == "high":
                        priority_emoji = "🔴"
                    elif priority == "critical":
                        priority_emoji = "⚠️"

                    lines.append(f"{priority_emoji} **{request.title}** ({request.status})")

                    # Show request description in context transfer mode for more clarity
                    if self.is_context_transfer:
                        lines.append(f"  *{request.description}*")

                    lines.append("")

                # Note for additional pending requests
                if len(pending) > 3:
                    lines.append(f"*...and {len(pending) - 3} more pending requests*")
                    lines.append("")

            if resolved:
                lines.append("### Resolved Requests:")
                for request in resolved[:3]:  # Show only first 3 resolved requests
                    lines.append(f"✅ **{request.title}**")
                    if hasattr(request, "resolution") and request.resolution:
                        lines.append(f"  *Resolution:* {request.resolution}")
                    lines.append("")

                # Note for additional resolved requests
                if len(resolved) > 3:
                    lines.append(f"*...and {len(resolved) - 3} more resolved requests*")
                    lines.append("")

            # Add tip for team members about creating requests
            template_tip = (
                "Use the **Knowledge Request** tool to ask questions about content"
                if self.is_context_transfer
                else "Use the **Information Request** tool when you need more details from the coordinator"
            )
            lines.append(f"*Tip: {template_tip}*")
            lines.append("")
        else:
            lines.append(f"## {other_requests_title}")
            lines.append(no_requests_message)

        return "\n".join(lines)
