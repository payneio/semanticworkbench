from typing import Protocol

from events import events as skill_events
from semantic_workbench_api_model.workbench_model import (
    MessageType,
    NewConversationMessage,
    UpdateParticipant,
)
from semantic_workbench_assistant.assistant_app import (
    ConversationContext,
)

from .logging import extra_data, logger


class SkillEventMapperProtocol(Protocol):
    async def map(
        self,
        skill_event: skill_events.EventProtocol,
    ) -> None: ...


class SkillEventMapper(SkillEventMapperProtocol):
    def __init__(self, conversation_context: ConversationContext) -> None:
        self.conversation_context = conversation_context

    async def map(
        self,
        skill_event: skill_events.EventProtocol,
    ) -> None:
        """
        Maps events emitted by the skill assistant (from running actions or
        routines) to message types understood by the Semantic Workbench.
        """
        metadata = {"debug": skill_event.metadata} if skill_event.metadata else None
        logger.debug(
            "Mapping skill event to Workbench conversation message.",
            extra_data({
                "event_id": skill_event.id,
                "conversation_context_id": self.conversation_context.id,
            }),
        )

        match skill_event:
            case skill_events.MessageEvent():
                await self.conversation_context.send_messages(
                    NewConversationMessage(
                        content=skill_event.message or "",
                        metadata=metadata,
                    )
                )

            case skill_events.InformationEvent():
                if skill_event.message:
                    await self.conversation_context.send_messages(
                        NewConversationMessage(
                            content=f"Information event: {skill_event.message}",
                            message_type=MessageType.notice,
                            metadata=metadata,
                        ),
                    )

            case skill_events.ErrorEvent():
                await self.conversation_context.send_messages(
                    NewConversationMessage(
                        content=skill_event.message or "",
                        metadata=metadata,
                    )
                )

            case skill_events.StatusUpdatedEvent():
                await self.conversation_context.update_participant_me(UpdateParticipant(status=skill_event.message))

            case _:
                logger.warning("Unhandled event.", extra_data({"event": skill_event}))
