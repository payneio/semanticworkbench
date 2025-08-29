from typing import Any

import openai_client
from assistant_extensions.attachments import AttachmentsExtension
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel
from semantic_workbench_assistant.assistant_app import ConversationContext

from assistant.config import assistant_config
from assistant.data import InspectorTab, NewTaskInfo, TaskStatus
from assistant.domain.share_manager import ShareManager
from assistant.domain.tasks_manager import TasksManager
from assistant.logging import convert_to_serializable, logger
from assistant.notifications import Notifications
from assistant.prompt_utils import (
    ContextSection,
    ContextStrategy,
    Instructions,
    Prompt,
    add_context_to_prompt,
)
from assistant.utils import load_text_include


async def detect_knowledge_package_gaps(
    context: ConversationContext, attachments_extension: AttachmentsExtension
) -> None:
    config = await assistant_config.get(context.assistant)

    share = await ShareManager.get_share(context)

    # --------------------------------------------------------
    # STEP 1: Check if we have any knowledge package at all.
    # If we have no knowledge package at all, let's add an initial task to define it.
    # --------------------------------------------------------

    if (
        share.digest is None
        and share.tasks
        and not any(task.content == "The user must define the knowledge package content." for task in share.tasks)
    ):
        task = NewTaskInfo(
            content="The user must define the knowledge package content.",
            status=TaskStatus.PENDING,
        )
        await TasksManager.add_tasks(context, [task])
        await Notifications.notify_state_update(
            context,
            [InspectorTab.DEBUG],
        )
        return

    # --------------------------------------------------------
    # STEP 2: Check for gaps in the knowledge package.
    # --------------------------------------------------------

    debug: dict[str, Any] = {
        "context": convert_to_serializable(context.to_dict()),
        "agent": "knowledge_package_gaps_detection",
    }

    class Output(BaseModel):
        """Identified knowledge gaps."""

        gaps: list[str]  # Gaps in the knowledge package that need to be addressed.

    # Set up prompt instructions.
    instruction_text = load_text_include("detect_knowledge_package_gaps.md")
    instructions = Instructions(instruction_text)
    prompt = Prompt(
        instructions=instructions,
        context_strategy=ContextStrategy.MULTI,
    )

    # Add prompt context.
    role = await ShareManager.get_conversation_role(context)
    await add_context_to_prompt(
        prompt,
        context=context,
        role=role,
        model=config.request_config.openai_model,
        token_limit=config.request_config.max_tokens,
        attachments_extension=attachments_extension,
        attachments_config=config.attachments_config,
        attachments_in_system_message=True,
        include=[
            # ContextSection.KNOWLEDGE_INFO,
            ContextSection.KNOWLEDGE_BRIEF,
            # ContextSection.TASKS,
            ContextSection.TARGET_AUDIENCE,
            # ContextSection.LEARNING_OBJECTIVES,
            ContextSection.KNOWLEDGE_DIGEST,
            # ContextSection.INFORMATION_REQUESTS,
            # ContextSection.SUGGESTED_NEXT_ACTIONS,
            ContextSection.COORDINATOR_CONVERSATION,
            ContextSection.ATTACHMENTS,
        ],
    )

    # Chat completion
    async with openai_client.create_client(config.service_config) as client:
        try:
            completion_args = {
                "messages": prompt.messages(),
                "model": config.request_config.openai_model,
                "max_tokens": 500,
                "temperature": 0.8,
                "response_format": Output,
            }
            debug["completion_args"] = openai_client.serializable(completion_args)

            # LLM call
            response = await client.beta.chat.completions.parse(
                **completion_args,
            )
            openai_client.validate_completion(response)
            debug["completion_response"] = openai_client.serializable(response.model_dump())

            # Response
            if response and response.choices and response.choices[0].message.parsed:
                output: Output = response.choices[0].message.parsed
                if output.gaps:
                    task_contents = [f"Collect information about: {gap.strip()}" for gap in output.gaps if gap.strip()]
                    await Notifications.notify(
                        context,
                        f"Considering adding {len(task_contents)} tasks related to the knowledge content.",
                        debug_data=debug,
                    )
                else:
                    await Notifications.notify(
                        context, "No knowledge gaps identified. All required information is present.", debug_data=debug
                    )
                    return
            else:
                logger.warning("Empty response from LLM")
                return

        except Exception as e:
            logger.exception(f"Failed to make OpenIA call: {e}")
            debug["error"] = str(e)
            await Notifications.notify(
                context, "Error occurred while detecting knowledge package gaps.", debug_data=debug
            )
            return

    # --------------------------------------------------------
    # STEP 3: Now, deduplicate any gaps we already have tasks or information
    # requests for.
    # --------------------------------------------------------

    debug: dict[str, Any] = {
        "context": convert_to_serializable(context.to_dict()),
        "agent": "knowledge_package_gaps_deduplication",
    }

    class Output2(BaseModel):
        """Identified knowledge gaps."""

        tasks: list[str]  # Deduplicated tasks that need to be addressed.

    # Set up prompt instructions.
    instruction_text = load_text_include("deduplicate_knowledge_package_gaps.md")
    instructions = Instructions(instruction_text)
    prompt = Prompt(
        instructions=instructions,
        context_strategy=ContextStrategy.MULTI,
    )

    # Add prompt context.
    role = await ShareManager.get_conversation_role(context)
    await add_context_to_prompt(
        prompt,
        context=context,
        role=role,
        model=config.request_config.openai_model,
        token_limit=config.request_config.max_tokens,
        attachments_extension=attachments_extension,
        attachments_config=config.attachments_config,
        attachments_in_system_message=True,
        include=[
            # ContextSection.KNOWLEDGE_INFO,
            # ContextSection.KNOWLEDGE_BRIEF,
            ContextSection.TASKS,
            # ContextSection.TARGET_AUDIENCE,
            # ContextSection.LEARNING_OBJECTIVES,
            # ContextSection.KNOWLEDGE_DIGEST,
            ContextSection.INFORMATION_REQUESTS,
            # ContextSection.SUGGESTED_NEXT_ACTIONS,
            # ContextSection.COORDINATOR_CONVERSATION,
            # ContextSection.ATTACHMENTS,
        ],
    )

    # Add new tasks to be filtered.
    completion_messages = prompt.messages()
    user_message: ChatCompletionMessageParam = ChatCompletionUserMessageParam(
        role="user",
        content="Here are the potential new tasks:\n" + "\n".join(f"- {task}" for task in task_contents),
    )
    completion_messages.append(user_message)

    # Chat completion
    async with openai_client.create_client(config.service_config) as client:
        try:
            completion_args = {
                "messages": completion_messages,
                "model": config.request_config.openai_model,
                "max_tokens": 500,
                "temperature": 0.8,
                "response_format": Output2,
            }
            debug["completion_args"] = openai_client.serializable(completion_args)

            # LLM call
            response = await client.beta.chat.completions.parse(
                **completion_args,
            )
            openai_client.validate_completion(response)
            debug["completion_response"] = openai_client.serializable(response.model_dump())

            # Response
            if response and response.choices and response.choices[0].message.parsed:
                output2: Output2 = response.choices[0].message.parsed
                if output2.tasks:
                    task_contents = [gap.strip() for gap in output2.tasks if gap.strip()]
                    tasks = [NewTaskInfo(content=content) for content in task_contents]
                    await TasksManager.add_tasks(context, tasks)
                    await Notifications.notify(
                        context, f"Added {len(tasks)} new tasks related to the knowledge content.", debug_data=debug
                    )
                    await Notifications.notify_state_update(
                        context,
                        [InspectorTab.DEBUG],
                    )
                else:
                    await Notifications.notify(
                        context, "No knowledge gaps identified. All required information is present.", debug_data=debug
                    )
            else:
                logger.warning("Empty response from LLM for welcome message generation")

        except Exception as e:
            logger.exception(f"Failed to make OpenIA call: {e}")
            debug["error"] = str(e)
            await Notifications.notify(
                context, "Error occurred while deduplicating knowledge package gaps.", debug_data=debug
            )
