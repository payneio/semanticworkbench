"""
Template migration utilities for Project Assistant.

This module provides tools for migrating project data between different templates
(default <-> context transfer) while preserving important information.
"""

from typing import Optional, Tuple

from semantic_workbench_assistant.assistant_app import ConversationContext

from .logging import logger
from .project_data import ProjectGoal, SuccessCriterion
from .project_storage import ProjectStorage, ProjectStorageManager
from .template_utils import get_template_id


class TemplateMigration:
    """Handles migrations between template types."""

    @staticmethod
    async def migrate_to_context_transfer(context: ConversationContext, project_id: str) -> Tuple[bool, Optional[str]]:
        """
        Migrates a project from default template to context transfer template.

        This handles:
        1. Updating project brief to focus on knowledge sharing
        2. Simplifying goals to knowledge areas
        3. Updating metadata to indicate template change

        Args:
            context: Current conversation context
            project_id: Project ID to migrate

        Returns:
            Tuple of (success, message) where message contains details about the migration
        """
        try:
            # Check if project exists
            if not ProjectStorageManager.project_exists(project_id):
                return False, "Project not found"

            # Check if already using context transfer template
            current_template = await get_template_id(context)
            if current_template == "context_transfer":
                return True, "Already using context transfer template"

            # Load existing brief
            brief = ProjectStorage.read_project_brief(project_id)
            if not brief:
                return False, "Project brief not found"

            # Transform goals into knowledge areas if needed
            knowledge_areas = []
            if brief.goals:
                for goal in brief.goals:
                    # Convert goal to knowledge area
                    knowledge_area = ProjectGoal(
                        name=goal.name, description=goal.description, priority=goal.priority, success_criteria=[]
                    )

                    # Convert success criteria to simple bullet points
                    # without completion tracking
                    for criterion in goal.success_criteria:
                        # Create a new criterion without completion status
                        knowledge_area.success_criteria.append(
                            SuccessCriterion(
                                description=criterion.description,
                                # Do not copy completion status
                                completed=False,
                                completed_at=None,
                                completed_by=None,
                            )
                        )

                    knowledge_areas.append(knowledge_area)

            # Update the brief
            brief.goals = knowledge_areas

            # Add migration notice to additional context
            migration_notice = (
                "\n\n[MIGRATION NOTE: This project was migrated from a standard "
                "project template to a knowledge transfer template. Goals have been "
                "converted to knowledge areas and progress tracking has been disabled.]"
            )

            if brief.additional_context:
                brief.additional_context += migration_notice
            else:
                brief.additional_context = migration_notice.strip()

            # Save the updated brief
            ProjectStorage.write_project_brief(project_id, brief)

            # Update conversation metadata to indicate template change
            from semantic_workbench_api_model.workbench_model import AssistantStateEvent

            # Update conversation metadata to indicate template change
            # Using None for state as required by type system, state_id will be found from context
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="template_id", event="updated", state=None)
            )

            # Update track_progress setting in metadata
            # Using None for state as required by type system, state_id will be found from context
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="track_progress", event="updated", state=None)
            )

            # Log the migration
            await ProjectStorage.log_project_event(
                context=context,
                project_id=project_id,
                entry_type="custom",
                message="Migrated project from default template to knowledge transfer template",
                metadata={"from_template": "default", "to_template": "context_transfer"},
            )

            # Update all project UIs
            await ProjectStorage.refresh_all_project_uis(context, project_id)

            return True, "Successfully migrated to context transfer template"

        except Exception as e:
            logger.exception(f"Error migrating to context transfer template: {e}")
            return False, f"Error during migration: {str(e)}"

    @staticmethod
    async def migrate_to_default(context: ConversationContext, project_id: str) -> Tuple[bool, Optional[str]]:
        """
        Migrates a project from context transfer template to default template.

        This handles:
        1. Updating project brief to focus on project management
        2. Converting knowledge areas to goals with success criteria
        3. Updating metadata to indicate template change

        Args:
            context: Current conversation context
            project_id: Project ID to migrate

        Returns:
            Tuple of (success, message) where message contains details about the migration
        """
        try:
            # Check if project exists
            if not ProjectStorageManager.project_exists(project_id):
                return False, "Project not found"

            # Check if already using default template
            current_template = await get_template_id(context)
            if current_template == "default":
                return True, "Already using default template"

            # Load existing brief
            brief = ProjectStorage.read_project_brief(project_id)
            if not brief:
                return False, "Project brief not found"

            # Transform knowledge areas into goals with success criteria
            project_goals = []
            if brief.goals:
                for knowledge_area in brief.goals:
                    # Convert knowledge area to project goal
                    goal = ProjectGoal(
                        name=knowledge_area.name,
                        description=knowledge_area.description,
                        priority=knowledge_area.priority,
                        success_criteria=[],
                    )

                    # Convert bullet points to success criteria with completion tracking
                    for bullet in knowledge_area.success_criteria:
                        goal.success_criteria.append(SuccessCriterion(description=bullet.description, completed=False))

                    # If no success criteria exist, add a default one
                    if not goal.success_criteria:
                        goal.success_criteria.append(
                            SuccessCriterion(description=f"Complete implementation of {goal.name}", completed=False)
                        )

                    project_goals.append(goal)

            # Add default goal if no knowledge areas
            if not project_goals:
                project_goals.append(
                    ProjectGoal(
                        name="Complete project tasks",
                        description="Successfully complete all project tasks",
                        priority=1,
                        success_criteria=[
                            SuccessCriterion(description="Implement core functionality", completed=False),
                            SuccessCriterion(description="Complete testing", completed=False),
                            SuccessCriterion(description="Finalize documentation", completed=False),
                        ],
                    )
                )

            # Update the brief
            brief.goals = project_goals

            # Add migration notice to additional context
            migration_notice = (
                "\n\n[MIGRATION NOTE: This project was migrated from a knowledge transfer "
                "template to a standard project template. Knowledge areas have been "
                "converted to project goals with success criteria and progress tracking has been enabled.]"
            )

            if brief.additional_context:
                brief.additional_context += migration_notice
            else:
                brief.additional_context = migration_notice.strip()

            # Save the updated brief
            ProjectStorage.write_project_brief(project_id, brief)

            # Update conversation metadata to indicate template change
            from semantic_workbench_api_model.workbench_model import AssistantStateEvent

            # Using None for state as required by type system, state_id will be found from context
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="template_id", event="updated", state=None)
            )

            # Update track_progress setting in metadata
            # Using None for state as required by type system, state_id will be found from context
            await context.send_conversation_state_event(
                AssistantStateEvent(state_id="track_progress", event="updated", state=None)
            )

            # Log the migration
            await ProjectStorage.log_project_event(
                context=context,
                project_id=project_id,
                entry_type="custom",
                message="Migrated project from knowledge transfer template to default template",
                metadata={"from_template": "context_transfer", "to_template": "default"},
            )

            # Update all project UIs
            await ProjectStorage.refresh_all_project_uis(context, project_id)

            return True, "Successfully migrated to default template"

        except Exception as e:
            logger.exception(f"Error migrating to default template: {e}")
            return False, f"Error during migration: {str(e)}"
