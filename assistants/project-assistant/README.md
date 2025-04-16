# Project Assistant

A versatile collaboration and knowledge transfer system that offers two configuration templates to support different use cases: a fully-featured Project Management template and a streamlined Knowledge Sharing template.

## Overview

The Project Assistant is designed to bridge the information gap between Coordinators/Knowledge Owners and Team Members/Knowledge Recipients by providing structured communication with shared artifacts, real-time updates, and bidirectional information flow. It includes:

### Two Configuration Templates

1. **Default Template (Project Management)**
   - Full project management with goals and success criteria
   - Progress tracking and completion status
   - Project lifecycle states (Planning, Ready, In Progress, Complete)
   - Perfect for formal projects with well-defined deliverables

2. **Context Transfer Template (Knowledge Sharing)**
   - Simplified knowledge sharing without formal project structure
   - Focus on knowledge organization without progress tracking
   - Optimized for educational contexts and knowledge handover
   - Ideal for subject matter experts explaining complex topics

### Core Capabilities

- **Information Organization**: Create structured briefs with goals/knowledge areas
- **Knowledge Sharing**: Transfer knowledge between separate conversations
- **Information Requests**: Request clarification or additional information
- **Dynamic Whiteboard**: Auto-updating knowledge repository
- **Inspector Panel**: Visual dashboard showing project/knowledge state

## Key Features

### Conversation Types and Roles

The Project Assistant creates and manages three distinct types of conversations:

1. **Coordinator/Knowledge Owner Conversation**: The personal conversation used by the project coordinator or knowledge owner to create and manage the project or knowledge space.

2. **Shareable Template Conversation**: A template conversation that's automatically created along with a share URL. This conversation is never directly used - it serves as the template for creating individual team/recipient conversations when users click the share link.

3. **Team/Recipient Conversation(s)**: Individual conversations created when users redeem the share URL. Each team member/knowledge recipient gets their own personal conversation connected to the project/knowledge space.

### Template-Specific Roles

#### Default Template (Project Management)

1. **Coordinator Role**
   - Create project briefs with clear goals and success criteria
   - Maintain an auto-updating project whiteboard with critical information
   - Provide guidance and respond to information requests
   - Control project lifecycle state transitions
   - Share files and resources with the team

2. **Team Member Role**
   - Access project brief and whiteboard content
   - Mark success criteria as completed
   - Create requests for information or assistance
   - Update project progress
   - Report task completion

#### Context Transfer Template (Knowledge Sharing)

1. **Knowledge Owner Role**
   - Create knowledge overview with key topic areas
   - Share expertise through natural conversation
   - Answer questions and clarify complex topics
   - Provide resources and supporting materials
   - Structure knowledge for optimal transfer

2. **Knowledge Recipient Role**
   - Access knowledge overview and whiteboard
   - Request clarification or additional information
   - Explore shared resources and explanations
   - View conversations between knowledge owner and assistant
   - Learn without progress tracking overhead

### Key Artifacts and Data Models

The system manages several core artifacts that adapt to the selected template:

#### Shared Artifacts (Both Templates)

- **Whiteboard**: Dynamically updated, auto-organizing knowledge repository that captures key information from conversations
- **Information/Knowledge Requests**: Documented questions, clarifications, or resource needs
- **Project/Knowledge Log**: Chronological history of events, actions, and updates
- **Shared Files**: Resources uploaded and distributed among participants

#### Default Template Artifacts

- **Project Brief**: Formal definition with goals, success criteria, and completion tracking
- **Project Info**: Status, lifecycle state, and progress metrics
- **Success Criteria**: Individual trackable items with completion status

#### Context Transfer Template Artifacts

- **Knowledge Overview**: Structured topic areas with key points (no progress tracking)
- **Knowledge Map**: Relationships between topics and concepts
- **Reference Materials**: Supporting resources with contextual organization

The State Inspector UI dynamically composes information from these artifacts based on the active template, presenting a unified view that adapts to the context.

### State Management

The assistant uses a multi-layered state management approach:

- **Cross-Conversation Linking**: Connects Coordinator and Team conversations
- **File Synchronization**: Automatic file sharing between conversations, including when files are uploaded by Coordinators or when team members return to a conversation
- **Inspector Panel**: Real-time visual status dashboard for project progress
- **Conversation-Specific Storage**: Each conversation maintains role-specific state

## Usage

The assistant automatically adapts commands and terminology based on the selected template. For detailed usage examples, see [Template Usage Guide](docs/TEMPLATE_USAGE_GUIDE.md).

### Common Commands (Both Templates)

- `/start` - Create a new project/knowledge space
- `/join <code>` - Join an existing project/knowledge space
- `/dashboard` - View current project/knowledge overview
- `/whiteboard` - View the auto-generated knowledge repository
- `/requests` - View all information/knowledge requests
- `/help` - Get template-specific help and command list

### Default Template Commands (Project Management)

#### Coordinator Commands
- `/brief create` - Create a detailed project brief with goals and success criteria
- `/brief update` - Modify the project brief details
- `/state ready` - Mark project as ready for team operations
- `/state complete` - Mark project as completed
- `/share` - Generate project invitation for team members
- `/resolve <request-id>` - Resolve an information request from team

#### Team Commands
- `/request <title> <description> <priority>` - Create information request
- `/complete <criterion-id>` - Mark a success criterion as complete
- `/delete <request-id>` - Remove an information request
- `/coordinator` - View messages from the coordinator

### Context Transfer Template Commands (Knowledge Sharing)

#### Knowledge Owner Commands
- `/brief create` - Create a knowledge overview with topic areas
- `/brief update` - Update the knowledge structure
- `/share` - Generate knowledge space invitation for recipients
- `/resolve <request-id>` - Answer a knowledge request

#### Knowledge Recipient Commands  
- `/request <title> <description> <priority>` - Ask for clarification or additional information
- `/delete <request-id>` - Remove a knowledge request
- `/coordinator` - View messages from the knowledge owner

### Template-Specific Workflows

#### Default Template Workflow (Project Management)

1. **Coordinator Setup Phase**:
   - Create project brief with goals and success criteria
   - The whiteboard automatically updates with key project information
   - Generate and share invitation link for team members
   - Mark project as "Ready for Working" when definition is complete

2. **Team Execution Phase**:
   - Join project using invitation link
   - Review project brief and whiteboard content
   - Execute project tasks and create information requests as needed
   - Mark success criteria as completed when achieved
   - Update project progress through dashboard

3. **Project Completion**:
   - All success criteria are marked complete
   - Coordinator marks project as completed
   - Final project artifacts are available for reference

#### Context Transfer Template Workflow (Knowledge Sharing)

1. **Knowledge Owner Setup**:
   - Create knowledge overview with key topic areas
   - Share expertise through conversation with the assistant
   - The whiteboard automatically organizes knowledge shared
   - Generate and share invitation link for knowledge recipients

2. **Knowledge Recipient Exploration**:
   - Join knowledge space using invitation link
   - Review knowledge overview and whiteboard content
   - Create knowledge requests for clarification or additional information
   - Access the knowledge owner's conversations for context
   - Reference the auto-organized whiteboard as a knowledge resource

3. **Knowledge Transfer Process**:
   - Knowledge owner answers questions and provides clarification
   - Recipients continue to explore and ask follow-up questions
   - Knowledge whiteboard continuously improves with new information
   - Files and resources are automatically shared with all recipients

## Development

### Project Structure

- `/assistant/`: Core implementation files
  - `chat.py`: Main assistant implementation with event handlers
  - `configs/`: Template-specific configuration models
    - `default.py`: Project management template configuration
    - `context_transfer.py`: Knowledge sharing template configuration
    - `base.py`: Shared configuration base classes
  - `template_utils.py`: Template detection and utility functions
  - `template_migration.py`: Functions for migrating between templates
  - `role_utils.py`: Role detection and management utilities
  - `permission_utils.py`: Template-aware permission system
  - `project_tools.py`: Template-adaptive tool functions
  - `state_inspector.py`: Dynamic template-aware inspector panel
  - `project_manager.py`: Project/knowledge state and artifact management
  - `command_processor.py`: Template-specific command handling
  - `text_includes/`: Template-specific prompts and detection patterns

- `/docs/`: Documentation files
  - `DESIGN.md`: System design and architecture
  - `DEV_GUIDE.md`: Development guidelines
  - `TEMPLATE_USAGE_GUIDE.md`: Detailed usage examples for each template
  - `IMPLEMENTATION_PROGRESS.md`: Progress tracking for template improvements
  - `CLAUDE_PROMPTS.md`: Template-specific LLM prompt design

- `/tests/`: Test files covering template-specific behavior
  - `test_template_utilities.py`: Tests for template detection
  - `test_config_models.py`: Tests for template configuration

### Development Commands

```bash
# Install dependencies
make install

# Run tests
make test

# Type checking
make type-check

# Linting
make lint
```

## Architecture

The Project Assistant uses a template-based architecture that adapts its behavior to different use cases while maintaining a unified codebase:

### Template System Architecture

1. **Unified Codebase with Dual Templates**:
   - Single assistant implementation supporting two distinct templates
   - Template detection via `template_utils.py` for consistent identification
   - Template-specific configuration classes with inheritance structure
   - Configuration autoloading based on template ID

2. **Template-Aware Components**:
   - Dynamic command processing with template-specific permissions
   - Adaptive state inspector that changes based on template context
   - Template-specific system prompts and LLM instructions
   - Role terminology that changes based on template (Coordinator/Team vs Knowledge Owner/Recipient)

3. **Data Model Adaptations**:
   - Core models with template-specific field handling
   - Safe missing field access for context transfer template
   - Intelligent content organization based on template purpose
   - Template migration capability for switching between templates

### Core Architecture Components

1. **Cross-Conversation Communication**: Using the conversation sharing API
2. **Artifact Management**: Structured data models that adapt to template context
3. **State Inspection**: Dynamic template-aware status dashboard
4. **Tool-based Interaction**: Template-adaptive LLM functions
5. **Role-Specific Experiences**: Tailored interfaces for different roles in each template

The system follows a centralized artifact storage model with template-specific processing logic and event-driven updates to keep all conversations synchronized.
