"""
Manager directory for Knowledge Transfer Assistant.

This module provides the main KnowledgeTransferManager class for project management.
"""

from .coordinator_support import CoordinatorSupport
from .information_request_manager import InformationRequestManager
from .knowledge_brief_manager import KnowledgeBriefManager
from .knowledge_digest_manager import KnowledgeDigestManager
from .learning_objectives_manager import LearningObjectivesManager
from .project_lifecycle_manager import TransferLifecycleManager
from .share_management import ShareManagement


class KnowledgeTransferManager:
    """
    Manages the creation, modification, and lifecycle of knowledge transfer packages.

    The KnowledgeTransferManager provides a centralized set of operations for working with project data.
    It handles all the core business logic for interacting with projects, ensuring that
    operations are performed consistently and following the proper rules and constraints.

    This class implements the primary interface for both Coordinators and team members to interact
    with project entities like briefs, information requests, and knowledge bases. It abstracts
    away the storage details and provides a clean API for project operations.

    All methods are implemented as static methods to facilitate easy calling from
    different parts of the codebase without requiring instance creation.
    """

    # Share/Project Management
    create_shareable_team_conversation = ShareManagement.create_shareable_team_conversation
    create_share = ShareManagement.create_share
    join_share = ShareManagement.join_share
    get_share_id = ShareManagement.get_share_id
    get_share_role = ShareManagement.get_share_role
    get_share_log = ShareManagement.get_share_log
    get_share = ShareManagement.get_share
    get_share_info = ShareManagement.get_share_info

    # Knowledge Brief Operations
    get_knowledge_brief = KnowledgeBriefManager.get_knowledge_brief
    update_knowledge_brief = KnowledgeBriefManager.update_knowledge_brief

    # Learning Objectives & Outcomes
    add_learning_objective = LearningObjectivesManager.add_learning_objective
    update_learning_objective = LearningObjectivesManager.update_learning_objective
    delete_learning_objective = LearningObjectivesManager.delete_learning_objective
    get_learning_outcomes = LearningObjectivesManager.get_learning_outcomes
    add_learning_outcome = LearningObjectivesManager.add_learning_outcome
    update_learning_outcome = LearningObjectivesManager.update_learning_outcome
    delete_learning_outcome = LearningObjectivesManager.delete_learning_outcome

    # Information Request Management
    get_information_requests = InformationRequestManager.get_information_requests
    create_information_request = InformationRequestManager.create_information_request
    resolve_information_request = InformationRequestManager.resolve_information_request

    # Knowledge Digest Operations
    get_knowledge_digest = KnowledgeDigestManager.get_knowledge_digest
    update_knowledge_digest = KnowledgeDigestManager.update_knowledge_digest
    auto_update_knowledge_digest = KnowledgeDigestManager.auto_update_knowledge_digest

    # Project Lifecycle Management
    update_share_state = TransferLifecycleManager.update_share_state
    update_share_info = TransferLifecycleManager.update_share_info
    update_audience = TransferLifecycleManager.update_audience
    complete_transfer = TransferLifecycleManager.complete_transfer

    # Coordinator Support
    get_coordinator_next_action_suggestion = CoordinatorSupport.get_coordinator_next_action_suggestion


# Export individual managers for direct access if needed
__all__ = [
    "KnowledgeTransferManager",
    "CoordinatorSupport",
    "InformationRequestManager",
    "KnowledgeBriefManager",
    "KnowledgeDigestManager",
    "LearningObjectivesManager",
    "TransferLifecycleManager",
    "ShareManagement",
]