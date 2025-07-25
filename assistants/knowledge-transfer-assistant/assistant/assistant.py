# Copyright (c) Microsoft. All rights reserved.

# Project Assistant implementation

import asyncio
import pathlib
from typing import Any

from assistant_extensions import attachments, dashboard_card, navigator
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
    ContentSafety,
    ContentSafetyEvaluator,
    ConversationContext,
)

from assistant.respond import respond_to_conversation
from assistant.team_welcome import generate_team_welcome_message
from assistant.utils import (
    DEFAULT_TEMPLATE_ID,
    load_text_include,
)

from .common import detect_assistant_role, detect_conversation_type, get_shared_conversation_id, ConversationType
from .config import assistant_config
from .conversation_share_link import ConversationKnowledgePackageManager
from .data import InspectorTab, LogEntryType
from .files import ShareManager
from .logging import logger
from .manager import KnowledgeTransferManager
from .notifications import Notifications
from .inspectors import BriefInspector, LearningInspector, SharingInspector, DebugInspector
from .storage import ShareStorage
from .storage_models import ConversationRole

service_id = "knowledge-transfer-assistant.made-exploration"
service_name = "Knowledge Transfer Assistant"
service_description = "A mediator assistant that facilitates sharing knowledge between parties."


async def content_evaluator_factory(
    context: ConversationContext,
) -> ContentSafetyEvaluator:
    config = await assistant_config.get(context.assistant)
    return CombinedContentSafetyEvaluator(config.content_safety_config)


content_safety = ContentSafety(content_evaluator_factory)

assistant = AssistantApp(
    assistant_service_id=service_id,
    assistant_service_name=service_name,
    assistant_service_description=service_description,
    config_provider=assistant_config.provider,
    content_interceptor=content_safety,
    capabilities={AssistantCapability.supports_conversation_files},
    inspector_state_providers={
        InspectorTab.BRIEF: BriefInspector(assistant_config),
        InspectorTab.LEARNING: LearningInspector(assistant_config),
        InspectorTab.SHARING: SharingInspector(assistant_config),
        InspectorTab.DEBUG: DebugInspector(assistant_config),
    },
    assistant_service_metadata={
        **dashboard_card.metadata(
            dashboard_card.TemplateConfig(
                enabled=True,
                template_id=DEFAULT_TEMPLATE_ID,
                background_color="rgb(198, 177, 222)",
                icon=dashboard_card.image_to_url(
                    pathlib.Path(__file__).parent / "assets" / "icon-knowledge-transfer.svg", "image/svg+xml"
                ),
                card_content=dashboard_card.CardContent(
                    content_type="text/markdown",
                    content=load_text_include("card_content.md"),
                ),
            ),
        ),
        **navigator.metadata_for_assistant_navigator({
            "default": load_text_include("assistant_info.md"),
        }),
    },
)

attachments_extension = attachments.AttachmentsExtension(assistant)

app = assistant.fastapi_app()

@assistant.events.conversation.on_created_including_mine
async def on_conversation_created(context: ConversationContext) -> None:
    """
    The assistant manages three types of conversations:
    1. Coordinator Conversation: The main conversation used by the knowledge coordinator
    2. Shareable Team Conversation: A template conversation that has a share URL and is never directly used
    3. Team Conversation(s): Individual conversations for team members created when they redeem the share URL
    """

    conversation = await context.get_conversation()
    conversation_metadata = conversation.metadata or {}
    share_id = conversation_metadata.get("share_id")

    config = await assistant_config.get(context.assistant)
    conversation_type = detect_conversation_type(conversation)

    match conversation_type:
        case ConversationType.SHAREABLE_TEMPLATE:

            # Associate the shareable template with a share ID
            if not share_id:
                logger.error("No share ID found for shareable team conversation.")
                return
            await ConversationKnowledgePackageManager.associate_conversation_with_share(context, share_id)
            return

        case ConversationType.TEAM:

            if not share_id:
                logger.error("No share ID found for team conversation.")
                return

            # I'd put status messages here, but the attachment's extension is causing race conditions.
            await context.send_messages(
                NewConversationMessage(
                    content="Hold on a second while I set up your space...",
                    message_type=MessageType.chat,
                )
            )

            await ConversationKnowledgePackageManager.associate_conversation_with_share(context, share_id)
            await ConversationKnowledgePackageManager.set_conversation_role(context, share_id, ConversationRole.TEAM)
            await ShareManager.synchronize_files_to_team_conversation(context=context, share_id=share_id)

            welcome_message, debug = await generate_team_welcome_message(context)
            await context.send_messages(
                NewConversationMessage(
                    content=welcome_message,
                    message_type=MessageType.chat,
                    metadata={
                        "generated_content": True,
                        "debug": debug,
                    },
                )
            )

            # Pop open the inspector panel.
            await context.send_conversation_state_event(
                AssistantStateEvent(
                    state_id="brief",
                    event="focus",
                    state=None,
                )
            )

            return

        case ConversationType.COORDINATOR:
            try:
                # In the beginning, we created a share...
                share_id = await KnowledgeTransferManager.create_share(context)

                # And it was good. So we then created a sharable conversation that we use as a template.
                share_url = await KnowledgeTransferManager.create_shareable_team_conversation(
                    context=context, share_id=share_id
                )

                welcome_message = config.coordinator_config.welcome_message.format(
                    share_url=share_url or "<Share URL generation failed>"
                )

            except Exception as e:
                welcome_message = f"I'm having trouble setting up your knowledge transfer. Please try again or contact support if the issue persists. {str(e)}"

            await context.send_messages(
                NewConversationMessage(
                    content=welcome_message,
                    message_type=MessageType.chat,
                )
            )

            # Pop open the inspector panel.
            await context.send_conversation_state_event(
                AssistantStateEvent(
                    state_id="brief",
                    event="focus",
                    state=None,
                )
            )

@assistant.events.conversation.on_updated
async def on_conversation_updated(context: ConversationContext) -> None:
    """
    Handle conversation updates (including title changes) and sync with shareable template.
    """
    try:
        conversation = await context.get_conversation()
        conversation_type = detect_conversation_type(conversation)
        if conversation_type != ConversationType.COORDINATOR:
            return

        shared_conversation_id = await get_shared_conversation_id(context)
        if not shared_conversation_id:
            return

        # Update the shareable template conversation's title if needed.
        try:
            target_context = context.for_conversation(shared_conversation_id)
            target_conversation = await target_context.get_conversation()
            if target_conversation.title != conversation.title:
                await target_context.update_conversation_title(conversation.title)
                logger.debug(f"Updated conversation {shared_conversation_id} title from '{target_conversation.title}' to '{conversation.title}'")
            else:
                logger.debug(f"Conversation {shared_conversation_id} title already matches: '{conversation.title}'")
        except Exception as title_update_error:
            logger.error(f"Error updating conversation {shared_conversation_id} title: {title_update_error}")

    except Exception as e:
        logger.error(f"Error syncing conversation title: {e}")


@assistant.events.conversation.message.chat.on_created
async def on_message_created(
    context: ConversationContext, event: ConversationEvent, message: ConversationMessage
) -> None:
    await context.update_participant_me(UpdateParticipant(status="thinking..."))

    metadata: dict[str, Any] = {
        "debug": {
            "content_safety": event.data.get(content_safety.metadata_key, {}),
        }
    }

    try:
        share_id = await KnowledgeTransferManager.get_share_id(context)
        metadata["debug"]["share_id"] = share_id

        # If this is a Coordinator conversation, store the message for Team access
        async with context.set_status("jotting..."):
            role = await detect_assistant_role(context)
            if role == ConversationRole.COORDINATOR and message.message_type == MessageType.chat:
                try:
                    if share_id:
                        # Get the sender's name
                        sender_name = "Coordinator"
                        if message.sender:
                            participants = await context.get_participants()
                            for participant in participants.participants:
                                if participant.id == message.sender.participant_id:
                                    sender_name = participant.name
                                    break

                        # Store the message for Team access
                        ShareStorage.append_coordinator_message(
                            share_id=share_id,
                            message_id=str(message.id),
                            content=message.content,
                            sender_name=sender_name,
                            is_assistant=message.sender.participant_role == ParticipantRole.assistant,
                            timestamp=message.timestamp,
                        )

                        # If this is the coordinator's first message, pop the share canvas
                        messages = await context.get_messages()
                        if len(messages.messages) == 2:
                            await context.send_conversation_state_event(
                                AssistantStateEvent(
                                    state_id="brief",
                                    event="focus",
                                    state=None,
                                )
                            )
                except Exception as e:
                    # Don't fail message handling if storage fails
                    logger.exception(f"Error storing Coordinator message for Team access: {e}")

        async with context.set_status("pondering..."):
            await respond_to_conversation(
                context,
                new_message=message,
                attachments_extension=attachments_extension,
                metadata=metadata,
            )

        # If the message is from a Coordinator, update the whiteboard in the background
        if role == ConversationRole.COORDINATOR and message.message_type == MessageType.chat:
            asyncio.create_task(KnowledgeTransferManager.auto_update_knowledge_digest(context))

    except Exception as e:
        logger.exception(f"Error handling message: {e}")
        await context.send_messages(
            NewConversationMessage(
                content=f"Error: {str(e)}",
                message_type=MessageType.notice,
                metadata={"generated_content": False, **metadata},
            )
        )
    finally:
        await context.update_participant_me(UpdateParticipant(status=None))


@assistant.events.conversation.message.command.on_created
async def on_command_created(
    context: ConversationContext, event: ConversationEvent, message: ConversationMessage
) -> None:
    if message.message_type != MessageType.command:
        return

    await context.update_participant_me(UpdateParticipant(status="processing command..."))
    try:
        metadata = {"debug": {"content_safety": event.data.get(content_safety.metadata_key, {})}}

        # Respond to the conversation
        await respond_to_conversation(
            context,
            new_message=message,
            attachments_extension=attachments_extension,
            metadata=metadata,
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
    1. Store a copy in share storage
    2. Synchronize to all Team conversations

    For Team files:
    1. Use as-is without copying to share storage
    """
    try:
        share_id = await KnowledgeTransferManager.get_share_id(context)
        if not share_id or not file.filename:
            logger.warning(f"No share ID found or missing filename: share_id={share_id}, filename={file.filename}")
            return

        role = await detect_assistant_role(context)

        # Process based on role
        if role == ConversationRole.COORDINATOR:
            # For Coordinator files:
            # 1. Store in share storage (marked as coordinator file)

            success = await ShareManager.copy_file_to_share_storage(
                context=context,
                share_id=share_id,
                file=file,
                is_coordinator_file=True,
            )

            if not success:
                logger.error(f"Failed to copy file to share storage: {file.filename}")
                return

            # 2. Synchronize to all Team conversations
            # Get all Team conversations
            team_conversations = await ShareManager.get_team_conversations(context, share_id)

            if team_conversations:
                for team_conv_id in team_conversations:
                    await ShareManager.copy_file_to_conversation(
                        context=context,
                        share_id=share_id,
                        filename=file.filename,
                        target_conversation_id=team_conv_id,
                    )

            # 3. Update all UIs but don't send notifications to reduce noise
            await Notifications.notify_all_state_update(context, share_id, [InspectorTab.DEBUG])
        # Team files don't need special handling as they're already in the conversation

        # Log file creation to knowledge transfer log for all files
        await ShareStorage.log_share_event(
            context=context,
            share_id=share_id,
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
    try:
        # Get share ID
        share_id = await KnowledgeTransferManager.get_share_id(context)
        if not share_id or not file.filename:
            return

        role = await detect_assistant_role(context)
        if role == ConversationRole.COORDINATOR:
            # For Coordinator files:
            # 1. Update in share storage
            success = await ShareManager.copy_file_to_share_storage(
                context=context,
                share_id=share_id,
                file=file,
                is_coordinator_file=True,
            )

            if not success:
                logger.error(f"Failed to update file in share storage: {file.filename}")
                return

            team_conversations = await ShareManager.get_team_conversations(context, share_id)
            for team_conv_id in team_conversations:
                await ShareManager.copy_file_to_conversation(
                    context=context,
                    share_id=share_id,
                    filename=file.filename,
                    target_conversation_id=team_conv_id,
                )

            # 3. Update all UIs but don't send notifications to reduce noise
            await Notifications.notify_all_state_update(context, share_id, [InspectorTab.DEBUG])

        await ShareStorage.log_share_event(
            context=context,
            share_id=share_id,
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
    try:
        # Get share ID
        share_id = await KnowledgeTransferManager.get_share_id(context)
        if not share_id or not file.filename:
            return

        role = await detect_assistant_role(context)
        if role == ConversationRole.COORDINATOR:
            # For Coordinator files:
            # 1. Delete from share storage
            success = await ShareManager.delete_file_from_knowledge_share_storage(
                context=context, share_id=share_id, filename=file.filename
            )

            if not success:
                logger.error(f"Failed to delete file from share storage: {file.filename}")

            # 2. Update all UIs about the deletion but don't send notifications to reduce noise
            await Notifications.notify_all_state_update(context, share_id, [InspectorTab.DEBUG])
        # Team files don't need special handling

        await ShareStorage.log_share_event(
            context=context,
            share_id=share_id,
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


@assistant.events.conversation.participant.on_created
async def on_participant_joined(
    context: ConversationContext,
    event: ConversationEvent,
    participant: workbench_model.ConversationParticipant,
) -> None:
    try:
        if participant.id == context.assistant.id:
            return

        # Open the Brief tab (state inspector).
        await context.send_conversation_state_event(
            AssistantStateEvent(
                state_id="brief",
                event="focus",
                state=None,
            )
        )

        role = await detect_assistant_role(context)
        if role != ConversationRole.TEAM:
            return

        share_id = await ConversationKnowledgePackageManager.get_associated_share_id(context)
        if not share_id:
            return

        await ShareManager.synchronize_files_to_team_conversation(context=context, share_id=share_id)

        await ShareStorage.log_share_event(
            context=context,
            share_id=share_id,
            entry_type=LogEntryType.PARTICIPANT_JOINED,
            message=f"Participant joined: {participant.name}",
            metadata={
                "participant_id": participant.id,
                "participant_name": participant.name,
                "conversation_id": str(context.id),
            },
        )

    except Exception as e:
        logger.exception(f"Error handling participant join event: {e}")



