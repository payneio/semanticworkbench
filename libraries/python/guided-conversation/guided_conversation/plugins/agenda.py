# FIXME: Copied code from Semantic Kernel repo, using as-is despite type errors
# TODO: Search for and find the `# type: ignore` comments in the copied code and remove them

import logging
from typing import Annotated, Any

from pydantic import Field, ValidationError
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.functions import KernelArguments
from semantic_kernel.functions.kernel_function_decorator import kernel_function

from guided_conversation.utils.base_model_llm import BaseModelLLM
from guided_conversation.utils.conversation_helpers import Conversation, ConversationMessageType
from guided_conversation.utils.openai_tool_calling import ToolValidationResult
from guided_conversation.utils.plugin_helpers import PluginOutput, fix_error, update_attempts
from guided_conversation.utils.resources import ResourceConstraintMode, ResourceConstraintUnit, format_resource

AGENDA_ERROR_CORRECTION_SYSTEM_TEMPLATE = """<message role="system">You are a helpful, thoughtful, and meticulous assistant.
You are conducting a conversation with a user. You tried to update the agenda, but the update was invalid.
You will be provided the history of your conversation with the user, \
your previous attempt(s) at updating the agenda, and the error message(s) that resulted from your attempt(s).
Your task is to correct the update so that it is valid. \
Your changes should be as minimal as possible - you are focused on fixing the error(s) that caused the update to be invalid.
Note that if the resource allocation is invalid, you must follow these rules:
1. You should not change the description of the first item (since it has already been executed), but you can change its resource allocation
2. For all other items, you can combine or split them, or assign them fewer or more resources, \
but the content they cover collectively should not change (i.e. don't eliminate or add new topics).
For example, the invalid attempt was "item 1 = ask for date of birth (1 turn), item 2 = ask for phone number (1 turn), \
item 3 = ask for phone type (1 turn), item 4 = explore treatment history (6 turns)", \
and the error says you need to correct the total resource allocation to 7 turns. \
A bad solution is "item 1 = ask for date of birth (1 turn), \
item 2 = explore treatment history (6 turns)" because it eliminates the phone number and phone type topics. \
A good solution is "item 1 = ask for date of birth (2 turns), item 2 = ask for phone number, phone type,
and treatment history (2 turns), item 3 = explore treatment history (3 turns)."</message>

<message role="user">Conversation history:
{{ conversation_history }}

Previous attempts to update the agenda:
{{ previous_attempts }}</message>"""

UPDATE_AGENDA_TOOL = "update_agenda"


class _BaseAgendaItem(BaseModelLLM):
    title: str = Field(description="Brief description of the item")
    resource: int = Field(description="Number of turns required for the item")


class _BaseAgenda(BaseModelLLM):
    items: list[_BaseAgendaItem] = Field(
        description="Ordered list of items to be completed in the remainder of the conversation",
        default_factory=list,
    )


class Agenda:
    """An abstraction to manage a conversation agenda. The expected use case is that another agent will generate an agenda.
    This class will validate if it is valid, and help correct it if it is not.

    Args:
        kernel (Kernel): The Semantic Kernel instance to use for calling the LLM. Don't forget to set your
                req_settings since this class uses tool calling functionality from the Semantic Kernel.
        service_id (str): The service ID to use for the Semantic Kernel tool calling. One kernel can have multiple
                services. The service ID is used to identify which service to use for LLM calls. The Agenda object
                assumes that the service has tool calling capabilities and is some flavor of chat completion.
        resource_constraint_mode (ResourceConstraintMode): The mode for resource constraints.
        max_agenda_retries (int): The maximum number of retries for updating the agenda.
    """

    def __init__(
        self,
        kernel: Kernel,
        service_id: str,
        resource_constraint_mode: ResourceConstraintMode | None,
        max_agenda_retries: int = 2,
    ) -> None:
        logger = logging.getLogger(__name__)

        self.id = "agenda_plugin"
        self.kernel = Kernel()
        self.logger = logger
        self.kernel = kernel
        self.service_id = service_id

        self.resource_constraint_mode = resource_constraint_mode
        self.max_agenda_retries = max_agenda_retries

        self.agenda = _BaseAgenda()

    async def update_agenda(
        self,
        items: list[dict[str, str]],
        remaining_turns: int,
        conversation: Conversation,
    ) -> PluginOutput:
        """Updates the agenda model with the given items (generally generated by an LLM) and validates if the update is valid.
        The agenda update reasons in terms of turns for validating the if the proposed agenda is valid.
        If you wish to use a different resource unit, convert the value to turns in some way because
        we found that LLMs do much better at reasoning in terms of turns.

        Args:
            items (list[dict[str, str]]): A list of agenda items.
                Each item should have the following keys:
                - title (str): A brief description of the item.
                - resource (int): The number of turns required for the item.
            remaining_turns (int): The number of remaining turns.
            conversation (Conversation): The conversation object.

        Returns:
            PluginOutput: A PluginOutput object with the success status. Does not generate any messages.
        """
        previous_attempts = []
        while True:
            try:
                # Try to update the agenda, and do extra validation checks
                self.agenda.items = items  # type: ignore
                self._validate_agenda_update(items, remaining_turns)
                self.logger.info(f"Agenda updated successfully: {self.get_agenda_for_prompt()}")
                return PluginOutput(True, [])
            except (ValidationError, ValueError) as e:
                # Update the previous attempts and get instructions for the LLM
                previous_attempts, llm_formatted_attempts = update_attempts(
                    error=e,
                    attempt_id=str(items),
                    previous_attempts=previous_attempts,
                )

                # If we have reached the maximum number of retries return a failure
                if len(previous_attempts) > self.max_agenda_retries:
                    self.logger.warning(f"Failed to update agenda after {self.max_agenda_retries} attempts.")
                    return PluginOutput(False, [])
                else:
                    self.logger.info(f"Attempting to fix the agenda error. Attempt {len(previous_attempts)}.")
                    response = await self._fix_agenda_error(llm_formatted_attempts, conversation)
                    if response is None:
                        raise ValueError("Invalid response from the LLM.")
                    if response["validation_result"] != ToolValidationResult.SUCCESS:
                        self.logger.warning(
                            f"Failed to fix the agenda error due to a failure in the LLM tool call: {response['validation_result']}"
                        )
                        return PluginOutput(False, [])
                    else:
                        # Use the result of the first tool call to try the update again
                        items = response["tool_args_list"][0]["items"]

    def get_agenda_for_prompt(self) -> str:
        """Gets a string representation of the agenda for use in an LLM prompt.

        Returns:
            str: A string representation of the agenda.
        """
        agenda_json = self.agenda.model_dump()
        agenda_items = agenda_json.get("items", [])
        if len(agenda_items) == 0:
            return "None"
        agenda_str = "\n".join([
            f"{i + 1}. [{format_resource(item['resource'], ResourceConstraintUnit.TURNS)}] {item['title']}"
            for i, item in enumerate(agenda_items)
        ])
        total_resource = format_resource(sum([item["resource"] for item in agenda_items]), ResourceConstraintUnit.TURNS)
        agenda_str += f"\nTotal = {total_resource}"
        return agenda_str

    # The following is the kernel function that will be provided to the LLM call
    class Items:
        title: Annotated[str, "Description of the item"]
        resource: Annotated[int, "Number of turns required for the item"]

    @kernel_function(
        name=UPDATE_AGENDA_TOOL,
        description="Updates the agenda.",
    )
    def update_agenda_items(
        self,
        items: Annotated[list[Items], "Ordered list of items to be completed in the remainder of the conversation"],
    ):
        pass

    async def _fix_agenda_error(self, previous_attempts: str, conversation: Conversation) -> dict[Any, Any]:
        """Calls an LLM to try and fix an error in the agenda update."""
        req_settings = self.kernel.get_prompt_execution_settings_from_service_id(self.service_id)
        req_settings.max_tokens = 2000  # type: ignore
        req_settings.tool_choice = "auto"  # type: ignore
        self.kernel.add_function(plugin_name=self.id, function=self.update_agenda_items)
        req_settings.function_choice_behavior = FunctionChoiceBehavior.Auto(
            auto_invoke=False, filters={"included_plugins": [self.id]}
        )

        arguments = KernelArguments(
            conversation_history=conversation.get_repr_for_prompt(exclude_types=[ConversationMessageType.REASONING]),
            previous_attempts=previous_attempts,
        )

        return await fix_error(
            kernel=self.kernel,
            prompt_template=AGENDA_ERROR_CORRECTION_SYSTEM_TEMPLATE,
            req_settings=req_settings,  # type: ignore
            arguments=arguments,
        )

    def _validate_agenda_update(self, items: list[dict[str, str]], remaining_turns: int) -> None:
        """Validates if any constraints were violated while performing the agenda update.

        Args:
            items (list[dict[str, str]]): A list of agenda items.
            remaining_turns (int): The number of remaining turns.

        Raises:
            ValueError: If any validation checks fail.
        """
        # The total, proposed allocation of resources.
        total_resources = sum([item["resource"] for item in items])  # type: ignore

        violations = []
        # In maximum mode, the total resources should not exceed the remaining turns
        if (self.resource_constraint_mode == ResourceConstraintMode.MAXIMUM) and (total_resources > remaining_turns):
            total_resource_instruction = (
                f"The total turns allocated in the agenda must not exceed the remaining amount ({remaining_turns})"
            )
            violations.append(f"{total_resource_instruction}; but the current total is {total_resources}.")

        # In exact mode if the total resources were not exactly equal to the remaining turns
        if (self.resource_constraint_mode == ResourceConstraintMode.EXACT) and (total_resources != remaining_turns):
            total_resource_instruction = (
                f"The total turns allocated in the agenda must equal the remaining amount ({remaining_turns})"
            )
            violations.append(f"{total_resource_instruction}; but the current total is {total_resources}.")

        # Check if any item has a resource value of 0
        if any(item["resource"] <= 0 for item in items):  # type: ignore
            violations.append("All items must have a resource value greater than 0.")

        # Raise an error if any violations were found
        if len(violations) > 0:
            self.logger.debug(f"Agenda update failed due to the following violations: {violations}.")
            raise ValueError(" ".join(violations))

    def to_json(self) -> dict:
        agenda_dict = self.agenda.model_dump()
        return {
            "agenda": agenda_dict,
        }

    @classmethod
    def from_json(
        cls,
        json_data: dict,
        kernel: Kernel,
        service_id: str,
        resource_constraint_mode: ResourceConstraintMode | None,
        max_agenda_retries: int = 2,
    ) -> "Agenda":
        agenda = cls(kernel, service_id, resource_constraint_mode, max_agenda_retries)
        agenda.agenda.items = json_data["agenda"]["items"]
        return agenda
