import logging
from typing import Any, Callable

import deepmerge
import openai_client
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam
from semantic_workbench_api_model.workbench_model import (
    #    AssistantStateEvent,
    ConversationMessage,
    ConversationParticipant,
    MessageType,
    NewConversationMessage,
    #    ParticipantRole,
)
from semantic_workbench_assistant.assistant_app import (
    ConversationContext,
    #    storage_directory_for_context,
)

from ..agents.attachment_agent import AttachmentAgent
from ..config import AssistantConfigModel

logger = logging.getLogger(__name__)

#
# region Agent
#


class DocumentAgent:
    """
    An agent for working on document content: creation, editing, translation, etc.
    """

    def __init__(self) -> None:
        self._commands = [self.draft_outline]

    @property
    def commands(self) -> list[Callable]:
        return self._commands

    async def receive_command(
        self,
        config: AssistantConfigModel,
        context: ConversationContext,
        message: ConversationMessage,
        metadata: dict[str, Any] = {},
    ) -> None:
        # remove initial "/". This is not intuitive to me.
        msg_command_name = message.command_name
        msg_command_name = msg_command_name.replace("/", "")

        # check if available. If not, ignore for now.
        command_found = False
        for command in self.commands:
            if command.__name__ == msg_command_name:
                print(f"Found command {message.command_name}")
                command_found = True
                await command(config, context, message, metadata)  # TO DO, handle commands with args
                break
        if not command_found:
            print(f"Could not find command {message.command_name}")

    async def draft_outline(
        self,
        config: AssistantConfigModel,
        context: ConversationContext,
        message: ConversationMessage,
        metadata: dict[str, Any] = {},
    ) -> None:
        method_metadata_key = "draft_outline"

        # get conversation related info
        conversation = await context.get_messages(before=message.id)
        if message.message_type == MessageType.chat:
            conversation.messages.append(message)
        participants_list = await context.get_participants(include_inactive=True)

        # create chat completion messages
        chat_completion_messages: list[ChatCompletionMessageParam] = []
        _add_main_system_message(chat_completion_messages, draft_outline_main_system_message)
        _add_chat_history_system_message(
            chat_completion_messages, conversation.messages, participants_list.participants
        )
        _add_attachments_system_message(
            chat_completion_messages, config, AttachmentAgent.generate_attachment_messages(context)
        )

        # make completion call to openai
        async with openai_client.create_client(config.service_config) as client:
            try:
                completion_args = {
                    "messages": chat_completion_messages,
                    "model": config.request_config.openai_model,
                    "response_format": {"type": "text"},
                }
                completion = await client.chat.completions.create(**completion_args)
                content = completion.choices[0].message.content
                _on_success_metadata_update(metadata, method_metadata_key, config, chat_completion_messages, completion)

            except Exception as e:
                logger.exception(f"exception occurred calling openai chat completion: {e}")
                content = (
                    "An error occurred while calling the OpenAI API. Is it configured correctly?"
                    "View the debug inspector for more information."
                )
                _on_error_metadata_update(metadata, method_metadata_key, config, chat_completion_messages, e)

        # send the response to the conversation
        message_type = MessageType.chat
        if message.message_type == MessageType.command:
            message_type = MessageType.command_response

        await context.send_messages(
            NewConversationMessage(
                content=content,
                message_type=message_type,
                metadata=metadata,
            )
        )


# endregion

#
# region Message Helpers
#


def _add_main_system_message(chat_completion_messages: list[ChatCompletionMessageParam], prompt: str) -> None:
    message: ChatCompletionSystemMessageParam = {"role": "system", "content": prompt}
    chat_completion_messages.append(message)


def _add_chat_history_system_message(
    chat_completion_messages: list[ChatCompletionMessageParam],
    conversation_messages: list[ConversationMessage],
    participants: list[ConversationParticipant],
) -> None:
    chat_history_message_list = []
    for conversation_message in conversation_messages:
        chat_history_message = _format_message(conversation_message, participants)
        chat_history_message_list.append(chat_history_message)
    chat_history_str = " ".join(chat_history_message_list)

    message: ChatCompletionSystemMessageParam = {
        "role": "system",
        "content": f"<CONVERSATION>{chat_history_str}</CONVERSATION>",
    }
    chat_completion_messages.append(message)


def _add_attachments_system_message(
    chat_completion_messages: list[ChatCompletionMessageParam],
    config: AssistantConfigModel,
    attachment_messages: list[ChatCompletionMessageParam],
) -> None:
    if len(attachment_messages) > 0:
        chat_completion_messages.append({
            "role": "system",
            "content": config.agents_config.attachment_agent.context_description,
        })
        chat_completion_messages.extend(attachment_messages)


draft_outline_main_system_message = (
    "Generate an outline for the document, including title. The outline should include the key points that will"
    " be covered in the document. If attachments exist, consider the attachments and the rationale for why they"
    " were uploaded. Consider the conversation that has taken place. If a prior version of the outline exists,"
    " consider the prior outline. The new outline should be a hierarchical structure with multiple levels of"
    " detail, and it should be clear and easy to understand. The outline should be generated in a way that is"
    " consistent with the document that will be generated from it."
)
# ("You are an AI assistant that helps draft outlines for a future flushed-out document."
# " You use information from a chat history between a user and an assistant, a prior version of a draft"
# " outline if it exists, as well as any other attachments provided by the user to inform a newly revised "
# "outline draft. Provide ONLY any outline. Provide no further instructions to the user.")


def _on_success_metadata_update(
    metadata: dict[str, Any],
    method_metadata_key: str,
    config: AssistantConfigModel,
    chat_completion_messages: list[ChatCompletionMessageParam],
    completion: Any,
) -> None:
    deepmerge.always_merger.merge(
        metadata,
        {
            "debug": {
                f"{method_metadata_key}": {
                    "request": {
                        "model": config.request_config.openai_model,
                        "messages": chat_completion_messages,
                        "max_tokens": config.request_config.response_tokens,
                    },
                    "response": completion.model_dump() if completion else "[no response from openai]",
                },
            }
        },
    )
    metadata = _reduce_metadata_debug_payload(metadata)


def _on_error_metadata_update(
    metadata: dict[str, Any],
    method_metadata_key: str,
    config: AssistantConfigModel,
    chat_completion_messages: list[ChatCompletionMessageParam],
    e: Exception,
) -> None:
    deepmerge.always_merger.merge(
        metadata,
        {
            "debug": {
                f"{method_metadata_key}": {
                    "request": {
                        "model": config.request_config.openai_model,
                        "messages": chat_completion_messages,
                    },
                    "error": str(e),
                },
            }
        },
    )
    metadata = _reduce_metadata_debug_payload(metadata)


# endregion


#
# borrowed temporarily from Prospector chat.py
#


def _format_message(message: ConversationMessage, participants: list[ConversationParticipant]) -> str:
    """
    Format a conversation message for display.
    """
    conversation_participant = next(
        (participant for participant in participants if participant.id == message.sender.participant_id),
        None,
    )
    participant_name = conversation_participant.name if conversation_participant else "unknown"
    message_datetime = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return f"[{participant_name} - {message_datetime}]: {message.content}"


def _reduce_metadata_debug_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Reduce the size of the metadata debug payload.
    """

    # map of payload reducers and keys they should be called for
    # each reducer should take a value and return a reduced value
    payload_reducers: dict[str, list[Any]] = {
        "content": [
            AttachmentAgent.reduce_attachment_payload_from_content,
        ]
    }

    # NOTE: use try statements around each recursive call to reduce_metadata to report the parent key in case of error

    # now iterate recursively over all metadata keys and call the payload reducers for the matching keys
    def reduce_metadata(metadata: dict[str, Any] | Any) -> dict[str, Any] | Any:
        # check if the metadata is not a dictionary
        if not isinstance(metadata, dict):
            return metadata

        # iterate over the metadata keys
        for key, value in metadata.items():
            # check if the key is in the payload reducers
            if key in payload_reducers:
                # call the payload reducer for the key
                for reducer in payload_reducers[key]:
                    metadata[key] = reducer(value)
            # check if the value is a dictionary
            if isinstance(value, dict):
                try:
                    # recursively reduce the metadata
                    metadata[key] = reduce_metadata(value)
                except Exception as e:
                    logger.exception(f"exception occurred reducing metadata for key '{key}': {e}")
            # check if the value is a list
            elif isinstance(value, list):
                try:
                    # recursively reduce the metadata for each item in the list
                    metadata[key] = [reduce_metadata(item) for item in value]
                except Exception as e:
                    logger.exception(f"exception occurred reducing metadata for key '{key}': {e}")

        # return the reduced metadata
        return metadata

    try:
        # reduce the metadata
        return reduce_metadata(metadata)
    except Exception as e:
        logger.exception(f"exception occurred reducing metadata: {e}")
        return metadata


# endregion