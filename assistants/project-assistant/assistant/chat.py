# Copyright (c) Microsoft. All rights reserved.

# Project Assistant implementation
#
# This assistant provides project coordination capabilities with Coordinator and Team member roles,
# supporting whiteboard sharing, file synchronization, and team collaboration.


import logging
import time
from typing import Any, Dict, Optional

# Import for template detection

import openai_client
from assistant_extensions.attachments import AttachmentsExtension
from content_safety.evaluators import CombinedContentSafetyEvaluator
from semantic_workbench_api_model import workbench_model
from semantic_workbench_api_model.workbench_model import (
    AssistantStateEvent,
    ConversationEvent,
    ConversationMessage,
    MessageType,
    NewConversationMessage,
    ParticipantRole,
    UpdateParticipant,
)
from semantic_workbench_assistant.assistant_app import (
    AssistantApp,
    AssistantCapability,
    AssistantTemplate,
    BaseModelAssistantConfig,
    ContentSafety,
    ContentSafetyEvaluator,
    ConversationContext,
)

from .config import BaseAssistantConfigModel, AssistantConfigModel, ContextTransferConfigModel
from .project_files import ProjectFileManager
from .project_manager import ProjectManager
from .project_storage import (
    ConversationProjectManager,
    ProjectNotifier,
    ProjectRole,
    ProjectStorage,
)
from .state_inspector import ProjectInspectorStateProvider

logger = logging.getLogger(__name__)

service_id = "project-assistant.made-exploration"
service_name = "Project Assistant"
service_description = "A mediator assistant that facilitates file sharing between conversations."

# Config.
assistant_config = BaseModelAssistantConfig[BaseAssistantConfigModel](
    AssistantConfigModel,
    additional_templates={
        "context_transfer": ContextTransferConfigModel,
    },
)


# Content safety.
async def content_evaluator_factory(
    context: ConversationContext,
) -> ContentSafetyEvaluator:
    config = await assistant_config.get(context.assistant)
    return CombinedContentSafetyEvaluator(config.content_safety_config)


content_safety = ContentSafety(content_evaluator_factory)

# Set up the app.
assistant = AssistantApp(
    assistant_service_id=service_id,
    assistant_service_name=service_name,
    assistant_service_description=service_description,
    config_provider=assistant_config.provider,
    content_interceptor=content_safety,
    capabilities={AssistantCapability.supports_conversation_files},
    inspector_state_providers={
        "project_status": ProjectInspectorStateProvider(assistant_config),
    },
    additional_templates=[
        AssistantTemplate(
            id="context_transfer",
            name="Context Transfer Assistant (experimental)",
            description="An assistant for capturing and sharing complex information for others to explore.",
        ),
    ],
)

attachments_extension = AttachmentsExtension(assistant)

app = assistant.fastapi_app()


async def trigger_whiteboard_update(context: ConversationContext, project_id: str) -> None:
    """
    Triggers a whiteboard update after a significant coordinator message.

    This function:
    1. Retrieves recent messages from the conversation
    2. Calls the auto_update_whiteboard function to update the whiteboard
    3. Does not send notifications to avoid notification spam

    Args:
        context: The conversation context
        project_id: The project ID
    """
    try:
        # Get the conversation
        conversation = await context.get_conversation()
        if not conversation:
            return

        # Get all messages from the conversation
        message_data = await context.get_messages()
        if not message_data or not hasattr(message_data, "__iter__"):
            return

        # Convert to a list we can work with
        message_list = list(message_data)
        if not message_list:
            return

        # Get the last 20 messages or all if fewer
        message_count = len(message_list)
        recent_message_list = message_list[-20:] if message_count > 20 else message_list

        # Call auto_update_whiteboard to update the whiteboard
        from .project_manager import ProjectManager

        await ProjectManager.auto_update_whiteboard(context, recent_message_list)

    except Exception as e:
        logger.exception(f"Error triggering whiteboard update: {e}")


@assistant.events.conversation.message.chat.on_created
async def on_message_created(
    context: ConversationContext, event: ConversationEvent, message: ConversationMessage
) -> None:
    """
    Handle user chat messages and provide appropriate project coordination responses.

    This manages project setup/detection, role enforcement, and updating the whiteboard
    for coordinator messages.
    """

    # update the participant status to indicate the assistant is thinking
    await context.update_participant_me(UpdateParticipant(status="thinking..."))
    try:
        # Get conversation to access metadata
        conversation = await context.get_conversation()
        metadata = conversation.metadata or {}

        # Check if setup is complete - check both local metadata and the state API
        setup_complete = metadata.get("setup_complete", False)

        # First check if project ID exists - if it does, setup should always be considered complete
        from .project_manager import ProjectManager

        project_id = await ProjectManager.get_project_id(context)
        if project_id:
            # If we have a project ID, we should never show the setup instructions
            setup_complete = True

            # If metadata doesn't reflect this, try to get actual role using the improved detection
            from .role_utils import get_conversation_role

            role = await get_conversation_role(context)
            if role:
                metadata["project_role"] = role.value
                metadata["assistant_mode"] = role.value
                metadata["setup_complete"] = True
                logger.info(f"Found project role using improved detection: {role.value}")

                # Update conversation metadata to fix this inconsistency
                await context.send_conversation_state_event(
                    AssistantStateEvent(state_id="setup_complete", event="updated", state=None)
                )
                await context.send_conversation_state_event(
                    AssistantStateEvent(state_id="project_role", event="updated", state=None)
                )
                await context.send_conversation_state_event(
                    AssistantStateEvent(state_id="assistant_mode", event="updated", state=None)
                )
            else:
                # Default to team if we can't determine
                metadata["project_role"] = "team"
                metadata["assistant_mode"] = "team"
                metadata["setup_complete"] = True
                logger.info("Could not determine role from storage, defaulting to team mode")
        # If no project ID, check storage as a fallback
        elif not setup_complete:
            try:
                from .role_utils import get_conversation_role

                # Check if we have a project role using improved detection
                role = await get_conversation_role(context)
                if role:
                    # If we have a role, consider setup complete
                    setup_complete = True
                    metadata["setup_complete"] = True
                    metadata["project_role"] = role.value
                    metadata["assistant_mode"] = role.value
                    logger.info(f"Found project role using improved detection: {role.value}")
            except Exception as e:
                logger.exception(f"Error getting role using improved detection: {e}")

        assistant_mode = metadata.get("assistant_mode", "setup")

        # If setup isn't complete, show setup required message (only if we truly have no project)
        if not setup_complete and assistant_mode == "setup" and not project_id:
            # Show setup required message for regular chat messages
            await context.send_messages(
                NewConversationMessage(
                    content=(
                        "**Setup Required**\n\n"
                        "You need to set up the assistant before proceeding. Please use one of these commands:\n\n"
                        "- `/start` - Create a new project as Coordinator\n"
                        "- `/join <code>` - Join an existing project as a Team member\n"
                        "- `/help` - Get help with available commands"
                    ),
                    message_type=MessageType.notice,
                )
            )
            return

        # Get the conversation's role (Coordinator or Team)
        role = metadata.get("project_role")

        # If role isn't set yet, detect it now
        if not role:
            role = await detect_assistant_role(context)
            metadata["project_role"] = role
            # Update conversation metadata through appropriate method
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="project_role", event="updated", state=None)
            )

        # If this is a Coordinator conversation, store the message for Team access
        if role == "coordinator" and message.message_type == MessageType.chat:
            try:
                # Get the project ID
                from .project_manager import ProjectManager
                from .role_utils import is_coordinator
                from .template_utils import is_context_transfer_template

                # Double-check with improved role detection to be sure
                is_coord = await is_coordinator(context)
                if not is_coord:
                    logger.warning("Metadata indicates coordinator role but improved detection says otherwise")
                    # Continue anyway as metadata might be setting the intended role

                project_id = await ProjectManager.get_project_id(context)

                if project_id:
                    # Get the sender's name
                    sender_name = "Coordinator"
                    if message.sender:
                        participants = await context.get_participants()
                        for participant in participants.participants:
                            if participant.id == message.sender.participant_id:
                                sender_name = participant.name
                                break

                    # Check if this is a context transfer template
                    is_context_transfer = await is_context_transfer_template(context)
                    if is_context_transfer:
                        sender_name = f"Knowledge Owner ({sender_name})"

                    # Check if the message contains significant content before storing
                    # This helps filter out routine messages and reduce noise in the coordinator message store
                    should_store = True

                    # Skip very short messages unless they contain important indicators
                    content_length = len(message.content.strip())
                    important_keywords = [
                        "decision",
                        "important",
                        "deadline",
                        "milestone",
                        "priority",
                        "agreed",
                        "conclusion",
                        "requirement",
                        "goal",
                        "complete",
                        "critical",
                        "update",
                        "change",
                    ]

                    # Check if message contains any important keywords
                    has_important_keyword = any(keyword in message.content.lower() for keyword in important_keywords)

                    # Only filter user messages, keep all assistant messages
                    is_user_message = message.sender and message.sender.participant_role == ParticipantRole.user

                    if is_user_message and content_length < 50 and not has_important_keyword:
                        # Short message without important keywords - skip storage
                        should_store = False
                        logger.info(f"Skipping short non-critical coordinator message: {message.id}")

                    # Store the message for Team access if it's worth sharing
                    if should_store:
                        from .project_storage import ProjectStorage

                        ProjectStorage.append_coordinator_message(
                            project_id=project_id,
                            message_id=str(message.id),
                            content=message.content,
                            sender_name=sender_name,
                            is_assistant=message.sender.participant_role == ParticipantRole.assistant,
                            timestamp=message.timestamp,
                        )
                        logger.info(f"Stored Coordinator message for Team access: {message.id}")

                        # For context transfer template, update the whiteboard more frequently
                        # This ensures knowledge is always accessible in the whiteboard
                        if is_context_transfer and is_user_message and (content_length > 100 or has_important_keyword):
                            await trigger_whiteboard_update(context, project_id)

            except Exception as e:
                # Don't fail message handling if storage fails
                logger.exception(f"Error storing Coordinator message for Team access: {e}")

        # Prepare custom system message based on role and template
        from .utils import load_text_include
        from .template_utils import is_context_transfer_template

        role_specific_prompt = ""

        # Check if this is a context transfer template
        is_context_transfer = await is_context_transfer_template(context)

        if role == "coordinator":
            if is_context_transfer:
                # Context Transfer Coordinator (Knowledge Owner) instructions
                role_specific_prompt = load_text_include("context_transfer_coordinator_prompt.txt")
            else:
                # Default Project Coordinator instructions
                role_specific_prompt = load_text_include("coordinator_prompt.txt")
        else:
            if is_context_transfer:
                # Context Transfer Team (Knowledge Recipient) instructions
                role_specific_prompt = load_text_include("context_transfer_team_prompt.txt")
            else:
                # Default Project Team instructions
                role_specific_prompt = load_text_include("team_prompt.txt")

        # Add role-specific and template-specific metadata to pass to the LLM
        if is_context_transfer:
            # Context Transfer template roles
            role_description = (
                "Knowledge Owner Mode (Context Transfer)"
                if role == "coordinator"
                else "Knowledge Recipient Mode (Context Transfer)"
            )
        else:
            # Default Project Assistant template roles
            role_description = (
                "Coordinator Mode (Planning Stage)" if role == "coordinator" else "Team Mode (Working Stage)"
            )

        role_metadata = {
            "project_role": role,
            "template_type": "context_transfer" if is_context_transfer else "default",
            "role_description": role_description,
            "debug": {"content_safety": event.data.get(content_safety.metadata_key, {})},
        }

        # respond to the message with role-specific context
        await respond_to_conversation(
            context,
            message=message,
            attachments_extension=attachments_extension,
            metadata=role_metadata,
            role_specific_prompt=role_specific_prompt,
        )
    finally:
        # update the participant status to indicate the assistant is done thinking
        await context.update_participant_me(UpdateParticipant(status=None))


@assistant.events.conversation.message.command.on_created
async def on_command_created(
    context: ConversationContext, event: ConversationEvent, message: ConversationMessage
) -> None:
    """
    Handle command messages using the centralized command processor.
    """
    # update the participant status to indicate the assistant is thinking
    await context.update_participant_me(UpdateParticipant(status="processing command..."))
    try:
        # Get the conversation's role (Coordinator or Team)
        conversation = await context.get_conversation()
        metadata = conversation.metadata or {}
        role = metadata.get("project_role")

        # If role isn't set yet, detect it now
        if not role:
            role = await detect_assistant_role(context)
            metadata["project_role"] = role
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="project_role", event="updated", state=None)
            )

        # Process the command using the command processor
        from .command_processor import process_command

        command_processed = await process_command(context, message)

        # If the command wasn't recognized or processed, respond normally
        if not command_processed:
            await respond_to_conversation(
                context,
                message=message,
                attachments_extension=attachments_extension,
                metadata={"debug": {"content_safety": event.data.get(content_safety.metadata_key, {})}},
            )
    finally:
        # update the participant status to indicate the assistant is done thinking
        await context.update_participant_me(UpdateParticipant(status=None))


@assistant.events.conversation.file.on_created
async def on_file_created(
    context: ConversationContext,
    event: workbench_model.ConversationEvent,
    file: workbench_model.File,
) -> None:
    """
    Handle when a file is created in the conversation.

    For Coordinator files:
    1. Store a copy in project storage
    2. Synchronize to all Team conversations

    For Team files:
    1. Use as-is without copying to project storage
    """
    try:
        # Log file creation event details
        logger.info(f"File created event: filename={file.filename}, size={file.file_size}, type={file.content_type}")
        logger.info(f"Full file object: {file}")

        # Get project ID
        project_id = await ProjectManager.get_project_id(context)
        if not project_id or not file.filename:
            logger.warning(
                f"No project ID found or missing filename: project_id={project_id}, filename={file.filename}"
            )
            return

        # Get the conversation's role
        role = await ConversationProjectManager.get_conversation_role(context)

        # If role couldn't be determined, skip processing
        if not role:
            logger.warning(f"Could not determine conversation role for file handling: {file.filename}")
            return

        logger.info(f"Processing file {file.filename} with role: {role.value}, project: {project_id}")

        # Use ProjectFileManager for file operations

        # Process based on role
        if role.value == "coordinator":
            # For Coordinator files:
            # 1. Store in project storage (marked as coordinator file)
            logger.info(f"Copying Coordinator file to project storage: {file.filename}")

            # Check project files directory
            from .project_files import ProjectFileManager

            files_dir = ProjectFileManager.get_project_files_dir(project_id)
            logger.info(f"Project files directory: {files_dir} (exists: {files_dir.exists()})")

            # Copy file to project storage
            success = await ProjectFileManager.copy_file_to_project_storage(
                context=context,
                project_id=project_id,
                file=file,
                is_coordinator_file=True,
            )

            if not success:
                logger.error(f"Failed to copy file to project storage: {file.filename}")
                return

            # Verify file was stored correctly
            file_path = ProjectFileManager.get_file_path(project_id, file.filename)
            if file_path.exists():
                logger.info(f"File successfully stored at: {file_path} (size: {file_path.stat().st_size} bytes)")
            else:
                logger.error(f"File not found at expected location: {file_path}")

            # Check file metadata was updated
            metadata = ProjectFileManager.read_file_metadata(project_id)
            if metadata and any(f.filename == file.filename for f in metadata.files):
                logger.info(f"File metadata updated successfully for {file.filename}")
            else:
                logger.error(f"File metadata not updated for {file.filename}")

            # 2. Synchronize to all Team conversations
            # Get all Team conversations
            team_conversations = await ProjectFileManager.get_team_conversations(context, project_id)

            if team_conversations:
                logger.info(f"Found {len(team_conversations)} team conversations to update")

                # Copy to each Team conversation
                for team_conv_id in team_conversations:
                    logger.info(f"Copying file to Team conversation {team_conv_id}: {file.filename}")
                    copy_success = await ProjectFileManager.copy_file_to_conversation(
                        context=context,
                        project_id=project_id,
                        filename=file.filename,
                        target_conversation_id=team_conv_id,
                    )
                    logger.info(f"Copy to Team conversation {team_conv_id}: {'Success' if copy_success else 'Failed'}")
            else:
                logger.info("No team conversations found to update files")

            # 3. Update all UIs but don't send notifications to reduce noise
            await ProjectNotifier.notify_project_update(
                context=context,
                project_id=project_id,
                update_type="file_created",
                message=f"Coordinator shared a file: {file.filename}",
                data={"filename": file.filename},
                send_notification=False,  # Don't send notification to reduce noise
            )
        else:
            # For Team files, no special handling needed
            # They're already available in the conversation
            logger.info(f"Team file created (not shared to project storage): {file.filename}")

        # Log file creation to project log for all files
        await ProjectStorage.log_project_event(
            context=context,
            project_id=project_id,
            entry_type="file_shared",
            message=f"File shared: {file.filename}",
            metadata={
                "file_id": getattr(file, "id", ""),
                "filename": file.filename,
                "is_coordinator_file": role.value == "coordinator",
            },
        )

    except Exception as e:
        logger.exception(f"Error handling file creation: {e}")


@assistant.events.conversation.file.on_updated
async def on_file_updated(
    context: ConversationContext,
    event: workbench_model.ConversationEvent,
    file: workbench_model.File,
) -> None:
    """
    Handle when a file is updated in the conversation.

    For Coordinator files:
    1. Update the copy in project storage
    2. Update copies in all Team conversations

    For Team files:
    1. Use as-is without updating in project storage
    """
    try:
        # Get project ID
        project_id = await ProjectManager.get_project_id(context)
        if not project_id or not file.filename:
            return

        # Get the conversation's role
        role = await ConversationProjectManager.get_conversation_role(context)

        # If role couldn't be determined, skip processing
        if not role:
            logger.warning(f"Could not determine conversation role for file update: {file.filename}")
            return

        # Use ProjectFileManager for file operations

        # Process based on role
        if role.value == "coordinator":
            # For Coordinator files:
            # 1. Update in project storage
            logger.info(f"Updating Coordinator file in project storage: {file.filename}")
            success = await ProjectFileManager.copy_file_to_project_storage(
                context=context,
                project_id=project_id,
                file=file,
                is_coordinator_file=True,
            )

            if not success:
                logger.error(f"Failed to update file in project storage: {file.filename}")
                return

            # 2. Update in all Team conversations
            # Get all Team conversations
            team_conversations = await ProjectFileManager.get_team_conversations(context, project_id)

            # Update in each Team conversation
            for team_conv_id in team_conversations:
                logger.info(f"Updating file in Team conversation {team_conv_id}: {file.filename}")
                await ProjectFileManager.copy_file_to_conversation(
                    context=context,
                    project_id=project_id,
                    filename=file.filename,
                    target_conversation_id=team_conv_id,
                )

            # 3. Update all UIs but don't send notifications to reduce noise
            await ProjectNotifier.notify_project_update(
                context=context,
                project_id=project_id,
                update_type="file_updated",
                message=f"Coordinator updated a file: {file.filename}",
                data={"filename": file.filename},
                send_notification=False,  # Don't send notification to reduce noise
            )
        else:
            # For Team files, no special handling needed
            # They're already available in the conversation
            logger.info(f"Team file updated (not shared to project storage): {file.filename}")

        # Log file update to project log for all files
        await ProjectStorage.log_project_event(
            context=context,
            project_id=project_id,
            entry_type="file_shared",
            message=f"File updated: {file.filename}",
            metadata={
                "file_id": getattr(file, "id", ""),
                "filename": file.filename,
                "is_coordinator_file": role.value == "coordinator",
            },
        )

    except Exception as e:
        logger.exception(f"Error handling file update: {e}")


@assistant.events.conversation.file.on_deleted
async def on_file_deleted(
    context: ConversationContext,
    event: workbench_model.ConversationEvent,
    file: workbench_model.File,
) -> None:
    """
    Handle when a file is deleted from the conversation.

    For Coordinator files:
    1. Delete from project storage
    2. Notify Team conversations to delete their copies

    For Team files:
    1. Just delete locally, no need to notify others
    """
    try:
        # Get project ID
        project_id = await ProjectManager.get_project_id(context)
        if not project_id or not file.filename:
            return

        # Get the conversation's role
        role = await ConversationProjectManager.get_conversation_role(context)

        # If role couldn't be determined, skip processing
        if not role:
            logger.warning(f"Could not determine conversation role for file deletion: {file.filename}")
            return

        # Use ProjectFileManager for file operations

        # Process based on role
        if role.value == "coordinator":
            # For Coordinator files:
            # 1. Delete from project storage
            logger.info(f"Deleting Coordinator file from project storage: {file.filename}")
            success = await ProjectFileManager.delete_file_from_project_storage(
                context=context, project_id=project_id, filename=file.filename
            )

            if not success:
                logger.error(f"Failed to delete file from project storage: {file.filename}")

            # 2. Update all UIs about the deletion but don't send notifications to reduce noise
            await ProjectNotifier.notify_project_update(
                context=context,
                project_id=project_id,
                update_type="file_deleted",
                message=f"Coordinator deleted a file: {file.filename}",
                data={"filename": file.filename},
                send_notification=False,  # Don't send notification to reduce noise
            )
        else:
            # For Team files, no special handling needed
            # Just delete locally
            logger.info(f"Team file deleted (not shared with project): {file.filename}")

        # Log file deletion to project log for all files
        await ProjectStorage.log_project_event(
            context=context,
            project_id=project_id,
            entry_type="file_deleted",
            message=f"File deleted: {file.filename}",
            metadata={
                "file_id": getattr(file, "id", ""),
                "filename": file.filename,
                "is_coordinator_file": role.value == "coordinator",
            },
        )

    except Exception as e:
        logger.exception(f"Error handling file deletion: {e}")


# Role detection for the project assistant
async def detect_assistant_role(context: ConversationContext) -> str:
    """
    Detects whether this conversation is in Coordinator Mode or Team Mode.

    Returns:
        "coordinator" if in Coordinator Mode, "team" if in Team Mode
    """
    try:
        # First check conversation metadata for role indicators
        conversation = await context.get_conversation()
        metadata = conversation.metadata or {}

        # Check if this is explicitly marked as a team conversation
        if metadata.get("is_team_conversation", False) or metadata.get("is_team_workspace", False):
            logger.info("Detected role from metadata: team conversation")
            return "team"

        # Check if this was created through a share redemption
        share_redemption = metadata.get("share_redemption", {})
        if share_redemption and share_redemption.get("conversation_share_id"):
            # Check if the share metadata has project information
            share_metadata = share_redemption.get("metadata", {})
            if (
                share_metadata.get("is_team_conversation", False)
                or share_metadata.get("is_team_workspace", False)
                or share_metadata.get("project_id")
            ):
                logger.info("Detected role from share redemption: team")
                return "team"

        # Next check if there's already a role set in project storage
        role = await ConversationProjectManager.get_conversation_role(context)
        if role:
            logger.info(f"Detected role from storage: {role.value}")
            return role.value

        # Get project ID
        project_id = await ProjectManager.get_project_id(context)
        if not project_id:
            # No project association yet, default to Coordinator
            logger.info("No project association, defaulting to coordinator")
            return "coordinator"

        # Check if this conversation created a project brief
        briefing = ProjectStorage.read_project_brief(project_id)

        # If the briefing was created by this conversation, we're in Coordinator Mode
        if briefing and briefing.conversation_id == str(context.id):
            logger.info("Detected role from briefing creation: coordinator")
            return "coordinator"

        # Otherwise, if we have a project association but didn't create the briefing,
        # we're likely in Team Mode
        logger.info("Detected role from project association: team")
        return "team"

    except Exception as e:
        logger.exception(f"Error detecting assistant role: {e}")
        # Default to Coordinator Mode if detection fails
        return "coordinator"


# Handle the event triggered when the assistant is added to a conversation.
@assistant.events.conversation.on_created_including_mine
async def on_conversation_created(context: ConversationContext) -> None:
    """
    Handle the event triggered when the assistant is added to a conversation.

    The assistant manages three types of conversations:
    1. Coordinator Conversation: The main conversation used by the project coordinator
    2. Shareable Team Conversation: A template conversation that has a share URL and is never directly used
    3. Team Conversation(s): Individual conversations for team members created when they redeem the share URL

    This handler automatically:
    1. Identifies which type of conversation this is based on metadata
    2. For new conversations, creates a project, sets up as coordinator, and creates a shareable team conversation
    3. For team conversations created from the share URL, sets up as team member
    4. For the shareable team conversation itself, initializes it properly
    """
    # Get conversation to access metadata
    conversation = await context.get_conversation()
    metadata = conversation.metadata or {}

    # send a focus event to notify the assistant to focus on the artifacts
    await context.send_conversation_state_event(
        AssistantStateEvent(
            state_id="project_dashboard",
            event="focus",
            state=None,
        )
    )

    # Define variables for each conversation type
    is_shareable_template = False
    is_team_from_redemption = False
    is_coordinator = False

    # Check if this conversation was imported from another (indicates it's from share redemption)
    if conversation.imported_from_conversation_id:
        # If it was imported AND has team metadata, it's a redeemed team conversation
        if metadata.get("is_team_conversation", False) and metadata.get("project_id"):
            is_team_from_redemption = True

    # First check for an explicit share redemption
    elif metadata.get("share_redemption", {}) and metadata.get("share_redemption", {}).get("conversation_share_id"):
        share_redemption = metadata.get("share_redemption", {})
        is_team_from_redemption = True
        share_metadata = share_redemption.get("metadata", {})

    # Check if this is a template conversation (original team conversation created by coordinator)
    elif (
        metadata.get("is_team_conversation", False)
        and metadata.get("project_id")
        and not conversation.imported_from_conversation_id
    ):
        # If it's a team conversation with project_id but NOT imported, it's the template
        is_shareable_template = True

    # Additional check for team conversations (from older versions without imported_from)
    elif metadata.get("is_team_conversation", False) and metadata.get("project_id"):
        is_team_from_redemption = True

    # If none of the above match, it's a coordinator conversation
    else:
        is_coordinator = True

    # Handle shareable template conversation - No welcome message
    if is_shareable_template:
        # This is a shareable template conversation, not an actual team conversation
        metadata["setup_complete"] = True
        metadata["assistant_mode"] = "team"
        metadata["project_role"] = "team"

        # Associate with the project ID if provided in metadata
        project_id = metadata.get("project_id")
        if project_id:
            # Set this conversation as a team member for the project
            await ConversationProjectManager.associate_conversation_with_project(context, project_id)
            await ConversationProjectManager.set_conversation_role(context, project_id, ProjectRole.TEAM)

        # Update conversation metadata
        await context.send_conversation_state_event(
            AssistantStateEvent(state_id="setup_complete", event="updated", state=None)
        )
        await context.send_conversation_state_event(
            AssistantStateEvent(state_id="project_role", event="updated", state=None)
        )
        await context.send_conversation_state_event(
            AssistantStateEvent(state_id="assistant_mode", event="updated", state=None)
        )

        # No welcome message for the shareable template
        return

    # Handle team conversation from share redemption - Show team welcome message
    if is_team_from_redemption:
        # Get project ID from metadata or share metadata
        project_id = metadata.get("project_id")

        # If no project_id directly in metadata, try to get it from share_redemption
        if not project_id and metadata.get("share_redemption"):
            share_metadata = metadata.get("share_redemption", {}).get("metadata", {})
            project_id = share_metadata.get("project_id")

        if project_id:
            # Set this conversation as a team member for the project
            await ConversationProjectManager.associate_conversation_with_project(context, project_id)
            await ConversationProjectManager.set_conversation_role(context, project_id, ProjectRole.TEAM)

            # Update conversation metadata
            metadata["setup_complete"] = True
            metadata["assistant_mode"] = "team"
            metadata["project_role"] = "team"

            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="setup_complete", event="updated", state=None)
            )
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="project_role", event="updated", state=None)
            )
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="assistant_mode", event="updated", state=None)
            )

            # Use team welcome message from config
            try:
                config = await assistant_config.get(context.assistant)
                welcome_message = config.team_config.welcome_message

                # Send welcome message
                await context.send_messages(
                    NewConversationMessage(
                        content=welcome_message,
                        message_type=MessageType.chat,
                        metadata={"generated_content": False},
                    )
                )
            except Exception as e:
                logger.error(f"Error sending team welcome message: {e}", exc_info=True)
            return
        else:
            logger.debug("Team conversation missing project_id in share metadata")

    # Handle coordinator conversation - Show coordinator welcome message
    if is_coordinator:
        # Create a new project
        success, project_id = await ProjectManager.create_project(context)

        if success and project_id:
            # Update conversation metadata
            metadata["setup_complete"] = True
            metadata["assistant_mode"] = "coordinator"
            metadata["project_role"] = "coordinator"

            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="setup_complete", event="updated", state=None)
            )
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="project_role", event="updated", state=None)
            )
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="assistant_mode", event="updated", state=None)
            )

            # Create a default project brief with placeholder information
            await ProjectManager.create_project_brief(
                context=context,
                project_name="New Project",
                project_description="This project was automatically created. Please update the project brief with your project details.",
            )

            # Create a team conversation and share URL
            (
                success,
                team_conversation_id,
                share_url,
            ) = await ProjectManager.create_team_conversation(
                context=context, project_id=project_id, project_name="Shared assistant"
            )

            if success and share_url:
                # Store the team conversation information in the coordinator's metadata
                # Using None for state as required by the type system
                metadata["team_conversation_id"] = team_conversation_id
                metadata["team_conversation_share_url"] = share_url

                await context.send_conversation_state_event(
                    AssistantStateEvent(state_id="team_conversation_id", event="updated", state=None)
                )

                await context.send_conversation_state_event(
                    AssistantStateEvent(
                        state_id="team_conversation_share_url",
                        event="updated",
                        state=None,
                    )
                )

                # Use coordinator welcome message from config with the share URL
                config = await assistant_config.get(context.assistant)
                welcome_message = config.coordinator_config.welcome_message.format(share_url=share_url)
            else:
                # Even if share URL creation failed, still use the welcome message
                # but it won't have a working share URL
                config = await assistant_config.get(context.assistant)
                welcome_message = config.coordinator_config.welcome_message.format(
                    share_url="<Share URL generation failed>"
                )
        else:
            # Failed to create project - use fallback mode
            metadata["setup_complete"] = False
            metadata["assistant_mode"] = "setup"

            # Use a simple fallback welcome message
            welcome_message = """# Welcome to the Project Assistant

I'm having trouble setting up your project. Please try again or contact support if the issue persists."""

        # Send the welcome message
        await context.send_messages(
            NewConversationMessage(
                content=welcome_message,
                message_type=MessageType.chat,
                metadata={"generated_content": False},
            )
        )


# Handle the event triggered when a participant joins a conversation
@assistant.events.conversation.participant.on_created
async def on_participant_joined(
    context: ConversationContext,
    event: ConversationEvent,
    participant: workbench_model.ConversationParticipant,
) -> None:
    """
    Handle the event triggered when a participant joins or returns to a conversation.

    This handler is used to detect when a team member returns to a conversation
    and automatically synchronize project files.
    """
    try:
        # Skip the assistant's own join event
        if participant.id == context.assistant.id:
            return

        # Get the project ID
        project_id = await ProjectManager.get_project_id(context)
        if not project_id:
            # Not a project conversation, nothing to do
            return

        # Get the conversation role
        role = await ConversationProjectManager.get_conversation_role(context)
        if not role or role != ProjectRole.TEAM:
            # Only need to synchronize files for team conversations
            return

        # This is a team member joining, synchronize project files
        from .project_files import ProjectFileManager

        await ProjectFileManager.synchronize_files(
            context=context,
            project_id=project_id,
        )

        # Synchronize the project whiteboard
        whiteboard = ProjectStorage.read_project_whiteboard(project_id)
        if whiteboard and whiteboard.content and whiteboard.content.strip():
            # Send welcome message with whiteboard link
            await context.send_messages(
                NewConversationMessage(
                    content="I've synchronized project files to your conversation.",
                    message_type=MessageType.notice,
                )
            )

    except Exception as e:
        logger.exception(f"Error handling participant join event: {e}")


# Response generation methods


async def respond_to_conversation(
    context: ConversationContext,
    message: ConversationMessage,
    attachments_extension: Any,
    metadata: Optional[Dict[str, Any]] = None,
    role_specific_prompt: str = "",
) -> None:
    """Generate a response to a conversation message."""
    try:
        # Get the configuration for the assistant
        config = await assistant_config.get(context.assistant)

        # Start building the messages array for the completion API
        messages = []

        # Get previous messages from the conversation context
        message_data = await context.get_messages()
        if not message_data or not hasattr(message_data, "__iter__"):
            previous_messages = []
        else:
            previous_messages = list(message_data)

        # Add system prompt first if we have a role-specific prompt
        if role_specific_prompt:
            messages.append({"role": "system", "content": role_specific_prompt})

        # Add previous messages for context (only up to 10 most recent for context)
        message_count = len(previous_messages)
        recent_messages = previous_messages[-10:] if message_count > 10 else previous_messages
        for prev_msg in recent_messages:
            # Skip if the message is not a proper object
            if not isinstance(prev_msg, object):
                continue

            # Skip if no content attribute or content is empty
            content = getattr(prev_msg, "content", None)
            if not content:
                continue

            # Default to user role unless we can confirm it's from the assistant
            msg_role = "user"

            # Try to determine if message is from assistant
            sender = getattr(prev_msg, "sender", None)
            if sender and hasattr(sender, "participant_role"):
                participant_role = getattr(sender, "participant_role", None)
                if participant_role == ParticipantRole.assistant:
                    msg_role = "assistant"

            # Add the message to our context
            messages.append({"role": msg_role, "content": content})

        # Add the current message
        messages.append({"role": "user", "content": message.content})

        # Process attachments using the extension
        if getattr(message, "attachments", None):
            # Analyze attachments and update messages
            messages = await attachments_extension.process_message_attachments(context, message, messages)

        # Create the completion
        async with openai_client.create_client(config.service_config, api_version="2024-06-01") as client:
            start_time = time.time()
            completion = await client.chat.completions.create(
                model=config.request_config.openai_model,
                temperature=0.7,  # Use a default temperature instead of accessing request_config.temperature
                max_tokens=config.request_config.max_tokens,
                messages=messages,
            )
            end_time = time.time()

            # Extract the completion content
            completion_content = completion.choices[0].message.content

            # If extracted content is empty, provide a default message
            if not completion_content:
                completion_content = "I'm not sure how to respond to that message. Could you please try again?"
            
            # Add detailed debug info to metadata
            if metadata:
                # Add complete completion response for debugging
                if "debug" not in metadata:
                    metadata["debug"] = {}
                
                metadata["debug"]["completion"] = {
                    "model": config.request_config.openai_model,
                    "request": {
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": config.request_config.max_tokens
                    },
                    "response": completion.model_dump(),
                    "duration_seconds": round(end_time - start_time, 2),
                    "token_usage": completion.usage.model_dump() if completion.usage else None
                }

        # Send the completed message back to the user
        await context.send_messages(
            NewConversationMessage(content=completion_content, message_type=MessageType.chat, metadata=metadata or {})
        )

    except Exception as e:
        logger.exception(f"Error generating response: {e}")
        await context.send_messages(
            NewConversationMessage(
                content="I'm sorry, I encountered an error while processing your message. Please try again.",
                message_type=MessageType.notice,
            )
        )
