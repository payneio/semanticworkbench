from textwrap import dedent
from typing import Any, ClassVar

import openai_client
from assistant_extensions.attachments import AttachmentsExtension
from openai import BaseModel
from openai.types.chat import (
    ChatCompletionMessageParam,
)
from openai_client.errors import CompletionError
from openai_client.tools import complete_with_tool_calls
from pydantic import ConfigDict, Field
from semantic_workbench_api_model.workbench_model import (
    MessageType,
    NewConversationMessage,
)
from semantic_workbench_assistant.assistant_app import (
    ConversationContext,
)

from assistant.config import assistant_config
from assistant.data import InspectorTab
from assistant.domain.share_manager import ShareManager
from assistant.domain.tasks_manager import TasksManager
from assistant.logging import logger
from assistant.notifications import Notifications
from assistant.prompt_utils import (
    ContextSection,
    ContextStrategy,
    Instructions,
    Prompt,
    add_context_to_prompt,
)
from assistant.tools import ShareTools
from assistant.utils import load_text_include


class ActorOutput(BaseModel):
    """
    Attributes:
        response: The response from the assistant.
    """

    tool_call_results: str = Field(
        description="A summary of the tool calls taken and their results. Should not mention 'tools' or 'call', focus on the results. If no tool calls were made, this will be an empty string.",  # noqa: E501
    )
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


async def act(
    context: ConversationContext,
    attachments_extension: AttachmentsExtension,
    metadata: dict[str, Any],
) -> ActorOutput | None:
    """
    Work, work, work, work, work...
    """

    local_conversation: list[ChatCompletionMessageParam] = []

    tasks = await TasksManager.get_tasks_to_work_on(context)
    while tasks:
        debug = metadata["debug"] or {}
        debug["context"] = (context.to_dict(),)
        debug["agent"] = "actor"

        config = await assistant_config.get(context.assistant)
        model = config.request_config.openai_model
        role = await ShareManager.get_conversation_role(context)
        debug["role"] = role

        instructions = load_text_include("actor_instructions.md")
        instructions = Instructions(instructions)
        prompt = Prompt(
            instructions=instructions,
            context_strategy=ContextStrategy.MULTI,
        )
        sections = [
            ContextSection.KNOWLEDGE_INFO,
            ContextSection.KNOWLEDGE_BRIEF,
            ContextSection.TARGET_AUDIENCE,
            ContextSection.KNOWLEDGE_DIGEST,
            ContextSection.INFORMATION_REQUESTS,
            ContextSection.ATTACHMENTS,
            ContextSection.TASKS,
            ContextSection.COORDINATOR_CONVERSATION,
        ]
        await add_context_to_prompt(
            prompt,
            context=context,
            role=role,
            model=model,
            token_limit=config.request_config.max_tokens,
            attachments_extension=attachments_extension,
            attachments_config=config.attachments_config,
            attachments_in_system_message=False,
            include=sections,
        )

        local_conversation = prompt.messages()
        async with openai_client.create_client(config.service_config) as client:
            try:
                completion_args = {
                    "messages": local_conversation,
                    "model": model,
                    "max_tokens": config.request_config.response_tokens,
                    "temperature": 0.7,
                    "response_format": ActorOutput,
                }
                debug["completion_args"] = openai_client.serializable(completion_args)

                response, new_messages = await complete_with_tool_calls(
                    async_client=client,
                    completion_args=completion_args,
                    tool_functions=ShareTools(context).act_tools(),
                    metadata=debug,
                    max_tool_call_rounds=32,
                )
                openai_client.validate_completion(response)
                local_conversation.extend(new_messages)

                if response and response.choices and response.choices[0].message.parsed:
                    output: ActorOutput | None = response.choices[0].message.parsed
                    debug["completion_response"] = openai_client.serializable(response.model_dump())

                    if output and output.tool_call_results:
                        # for req in output.user_information_requests:
                        #     await InformationRequestManager.create_information_request(
                        #         context=context,
                        #         title=req.title,
                        #         description=req.description,
                        #         priority=req.priority,
                        #         source=InformationRequestSource.INTERNAL,
                        #         debug_data=debug,
                        #     )

                        # response_message: ChatCompletionMessageParam = ChatCompletionAssistantMessageParam(
                        #     role="assistant",
                        #     content=output.accomplishments,
                        # )
                        # local_conversation.append(response_message)

                        await context.send_messages(
                            NewConversationMessage(
                                content=output.tool_call_results,
                                message_type=MessageType.notice,
                                metadata=metadata,
                            )
                        )
                        await Notifications.notify_state_update(
                            context,
                            [InspectorTab.DEBUG],
                        )

                    tasks = await TasksManager.get_unresolved_tasks(context)

            except CompletionError as e:
                logger.exception(f"Exception occurred calling OpenAI chat completion: {e}")
                debug["error"] = str(e)
                if isinstance(e.body, dict) and "message" in e.body:
                    content = e.body.get("message", e.message)
                elif e.message:
                    content = e.message
                else:
                    content = "An error occurred while processing your request."
                await context.send_messages(
                    NewConversationMessage(
                        content=content,
                        message_type=MessageType.notice,
                        metadata=metadata,
                    )
                )
                return


def get_formatted_token_count(tokens: int) -> str:
    # if less than 1k, return the number of tokens
    # if greater than or equal to 1k, return the number of tokens in k
    # use 1 decimal place for k
    # drop the decimal place if the number of tokens in k is a whole number
    if tokens < 1000:
        return str(tokens)
    else:
        tokens_in_k = tokens / 1000
        if tokens_in_k.is_integer():
            return f"{int(tokens_in_k)}k"
        else:
            return f"{tokens_in_k:.1f}k"


def get_token_usage_message(
    max_tokens: int,
    total_tokens: int,
    request_tokens: int,
    completion_tokens: int,
) -> str:
    """
    Generate a display friendly message for the token usage, to be added to the footer items.
    """

    return dedent(f"""
        Tokens used: {get_formatted_token_count(total_tokens)}
        ({get_formatted_token_count(request_tokens)} in / {get_formatted_token_count(completion_tokens)} out)
        of {get_formatted_token_count(max_tokens)} ({int(total_tokens / max_tokens * 100)}%)
    """).strip()


def get_response_duration_message(response_duration: float) -> str:
    """
    Generate a display friendly message for the response duration, to be added to the footer items.
    """

    return f"Response time: {response_duration:.2f} seconds"
