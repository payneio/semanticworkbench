# Backwards and forwards engineering with Claude code

Note: This is an example of "backwards/reverse engineering" where the design/specs are updated based on code changes. I started out just trying to clarify a design that evolved, but ended up refreshing the entire codebase.

## Design refactor (backwards engineering)

Developer:

```markdown

We probably shouldn't call the configuration template differences "modes". I can see you are already confusing this with our existing usage of the word "modes" to be whether or not the assistant is in "Coordinator mode" (in a conversation with the coordinator) or "Team mode" in a  conversation with a team member. So, we have two configurations with two modes each (four different states). How would you suggest we modify the language to make communicate this simply?

```

Claude:

```markdown
You're right about the terminology confusion. Let me clarify the distinction:

1. The assistant has two configuration templates:
  - Default Project Assistant template
  - Context Transfer template
2. Each template supports two conversation roles:
  - Coordinator role
  - Team member role

So we have a 2×2 matrix with four distinct states.

I'd suggest using consistent terminology:
- "Configuration templates" for the two assistant types
- "Conversation roles" for coordinator vs team member
- Avoid using "mode" in either context to prevent confusion

Would you like me to update the DESIGN.md with this clarified terminology?
```

Developer:

```markdown
Yes please. After we udpate the design doc, let's make a plan in the WORKING.md doc for how we can update all the code in the code base to support this design.
```

_... the assistant completed these and the developer then read through the new artifacts._

Developer:

```markdown
We need to update the design quite a bit more as I notice it has lagged work we've done in the code base. Specifically, we changed the project "KB" to be the assistant "whiteboard", but I notice it hasn't been updated in the DESIGN.md doc. Let's update the design doc to reflect the actual code (look at it to make sure you understand the design concepts). When you are done, I'll tell you about two more things we need to update in the design doc.
```

_... assistant did work_

Developer:

```markdown
You have correctly identified a few other aspects of the design doc we need to update. First of all, the stucture of the files in the "storage architecture" needs to be updated. At some point, we changed some of the directories and filename for the project data. Please take a look at the code (project_data.py is a good place to start) and  update the design doc appropriately.
```

_... assistant did work_

Developer:

```markdown
Excellent. We're almost there. Finally, at first we had the idea of a "dashboard" as being a data entity that would be represented in the state inspector, which is a visible tab in the Semantic Workbench. However, we noticed there was a lot of overlap between the dashboard and the other data entities and the state inspector started to contain other stuff that wasn't from the dashboard entity. This makes sense... we should have been coupling data with UI so directly. We made the decision to eliminate the dashboard entity in the code base and just build the state for the state inspector from other existing entities directly. To complete this decoupling, we needed to add a "project" entity (project.json) that held the overall info about the project (like the id and the share link, etc.). Please read the necessary code (at least state_inspector.py and project_data.py) and update the design doc to reflect our latest design.
```

_... assistant did work_

## Code refactor (forward engineering)

And then we play the design changes forward back into the code base...

Developer:

```markdown
 Ok. This design looks up to date now. Based on your new knowledge, do you want to update anything in ow WORKING.md work plan?
 ```

The result here was pretty spectacular. It ended up finding many of the things I had "in the back of my head" that I knew I would need to update in the assistant eventually, and it even found several bugs that I didn't yet know about that were introduced from refactors. In essence, the process of collaboratively refreshing the design and then using the design to refresh the code base.

WORKING.md:

```markdown
# Project Assistant Implementation Plan

## Configuration Templates Support

This document outlines the implementation plan for maintaining and improving the dual configuration template architecture of the Project Assistant.

### Background

The Project Assistant codebase supports two configuration templates:
1. **Default Template** (full project management)
2. **Context Transfer Template** (simplified knowledge sharing)

Each template supports two conversation roles:
- **Coordinator Role**
- **Team Member Role**

### Current Implementation Status

The basic architecture for configuration templates is already implemented:
- Configuration model classes defined in `assistant/configs/`
- Template selection in `assistant_config` in `chat.py`
- Different welcome messages for each template
- Support for disabling progress tracking in context transfer template
- UI adaptations in state inspector

### Improvement Plan

#### 1. Configuration Template Refactoring

1. **Template Type Detection**
   - Create a utility function to determine which template is active
   - Use consistent naming: `is_context_transfer_template()`
   - Add to a dedicated module for template utilities

2. **Configuration Model Improvements**
   - Move any duplicate code between templates to base classes
   - Create proper inheritance structure for template-specific configurations
   - Add documentation for each configuration parameter
   - Include validation rules to ensure template consistency

#### 2. UI Adaptation Enhancements

1. **State Inspector Improvements**
   - Ensure all labels consistently reflect the current template
   - Fix duplicated context section in state inspector
   - Enhance dynamic composition of data from multiple entities
   - Optimize the presentation of project information without relying on a dedicated dashboard entity
   - Add template-specific formatting for information requests
   - Include template-specific explanatory text

2. **Welcome Messages**
   - Review and update welcome messages for clarity
   - Ensure context transfer template welcome message better explains its purpose
   - Add contextual help tips for new users
   - Provide template-specific onboarding guidance

#### 3. Conversation Role Improvements

1. **Role Detection and Storage**
   - Review role detection logic for robustness
   - Ensure role information persists correctly
   - Handle role conflicts gracefully

2. **Permission Management**
   - Validate permissions for each role within each template
   - Implement template-aware capability checks
   - Ensure tool permissions match the current template

#### 4. Tool Function Enhancements

1. **Template-Aware Tools**
   - Update all tool functions to check the active template
   - Disable progress tracking tools in context transfer template
   - Add contextual success/error messages based on template

2. **LLM Prompting**
   - Update system prompts to be template-aware
   - Add template-specific examples to prompt text
   - Ensure information request detection adapts to template context

#### 5. Storage and Data Handling

1. **Model Adaptations**
   - Ensure ProjectBrief model gracefully handles missing fields in context transfer
   - Review all serialization/deserialization for template compatibility
   - Add migration path for projects switching between templates
   - Maintain clear separation between data entities and UI representation

2. **State Inspector Integration**
   - Enhance state inspector to dynamically build UI from multiple data sources
   - Ensure state inspector correctly adapts to the active template
   - Optimize formatting of information for readability
   - Add template-specific sections and labels to inspector view

3. **Whiteboard and Content Sharing**
   - Improve automatic whiteboard updates with more intelligent content extraction
   - Optimize coordinator conversation message sharing for better team context
   - Implement content filtering to prioritize most relevant information

#### 6. Documentation and Testing

1. **Documentation**
   - Update all code comments to reflect template differences
   - Document the 2×2 matrix of templates and roles
   - Create template-specific usage examples
   - Update design documentation to reflect data/UI decoupling
   - Provide clear explanations of the ProjectInfo entity's role

2. **Testing**
   - Add tests for template-specific behavior
   - Test all combinations of templates and roles
   - Verify state inspector correctly builds UI from multiple data sources
   - Validate whiteboard auto-update functionality
   - Automate validation of template consistency

### Implementation Sequence

1. First pass: Ensure all core functionality works in both templates
   - Focus on critical paths and user-facing features
   - Fix any current issues with template detection

2. Second pass: Improve template-specific user experience
   - Refine UI elements and prompts
   - Enhance tool behavior in each template

3. Third pass: Optimize and clean up
   - Remove any redundant code
   - Improve performance in both templates

### Success Criteria

- Users can seamlessly switch between templates
- Both templates provide optimal experiences for their intended use cases
- Code remains maintainable with minimal template-specific logic
- Documentation clearly explains the differences between templates
```

Developer:

```markdown
This is great. Please implement the changes outlined in WORKING.md in a methodical way. You may be interupted between steps and need to start over from a fresh context, so make sure you keep your context as you go. You can use WORKING.md for this or create new documents in the docs folder if you need.
```

_... assistant worked a bunch, but didn't complete everything..._

## The experience of getting Claude to do a large-ish refactor

Developer:

```markdown
If you'll recall, you were in the middle of a larger mission. It is detailed in docs/WORKING.md and if you look at your git status you'll see where you are at with everything. Also, it looks like you are currently keeping notes in docs/IMPLEMENTATION_PROGRESS.md (but feel free to do whatever you need). Please continue to methodically complete the working plan while ensuring you stick to our docs/DESIGN.md using good practices as outlined in our docs/DEV_GUIDE.md.
```

... and later

Developer:

```markdown
Do not commit changes using git. As you are doing a lot of work, we'll use git status to see what all you've done. Only I will change the git history.
```

... many messages like this

Claude:

```markdown
Let's summarize what we've accomplished today:

● Bash(cd /data/repos/semanticworkbench/assistants/project-assistant && uv run pytest tests/test_template_utilities.py -v)…
  ⎿  ============================= test session starts ==============================
     platform linux -- Python 3.11.11, pytest-8.3.5, pluggy-1.5.0 -- /data/repos/semanticworkbench/assistants/project-assistant/.venv/bin/python
     cachedir: .pytest_cache
     rootdir: /data/repos/semanticworkbench/assistants/project-assistant
     configfile: pyproject.toml

     … +7 lines (ctrl+r to expand)

     tests/test_template_utilities.py::TestTemplateSpecificTools::test_setup_tools_for_template PASSED [ 66%]
     tests/test_template_utilities.py::TestTemplateSpecificTools::test_add_project_goal_in_templates PASSED [ 83%]
     tests/test_template_utilities.py::TestTemplateSpecificTools::test_get_project_info_in_templates PASSED [100%]

     ============================== 6 passed in 0.55s ===============================

● In today's work, we've made significant progress on implementing the planned improvements for the Project Assistant. Here's a summary of what we've accomplished:

  1. Configuration Template Refactoring:
    - Created a comprehensive base configuration structure in configs/base.py
    - Reorganized the configuration models into a proper inheritance hierarchy
    - Improved the documentation and structure of configuration parameters
    - Added validation rules to ensure consistency across templates
  2. Tool Function Enhancements:
    - Extended the project_tools.py implementation to support template-specific behaviors
    - Added explicit checks for the active template in each tool function
    - Implemented template-specific responses and behaviors in key functions
    - Improved function documentation to clarify template-specific behaviors
  3. Testing:
    - Added comprehensive tests for template utilities in test_template_utilities.py
    - Created tests to validate template-specific behavior of tool functions
    - Verified that core functionality works correctly across both templates
    - Added proper mocking for async functions and external dependencies

  The configuration model improvements provide a more robust foundation for managing template-specific settings, while the tool function enhancements ensure consistent and appropriate behavior based on the active template. Our tests validate that this functionality is working as expected.

  Next steps in our implementation plan include updating welcome messages to be more template-specific, improving role detection logic, and updating system prompts to better reflect the active template. These changes will further enhance the user experience and ensure that the assistant's behavior is properly tailored to
  each template's intended use case.
```

## Other manual interventions (recipe step fodder)

When it paused to notify me of its updates.

Developer:

```markdown
Let's continue! Your work is detailed in docs/WORKING.md. If you look at your git status you'll see where you are at with everything. Also, it looks like you are currently keeping notes in docs/IMPLEMENTATION_PROGRESS.md (but feel free to do whatever you need). Please continue to methodically complete the working plan while ensuring you stick to our docs/DESIGN.md using good practices as outlined in our docs/DEV_GUIDE.md. Don't commit anything with git.
```

Sometimes it finished with some type-check errors in the code:

```
 Oh! You created a few problems! Try `make lint && make format && make type-check && make test` from the project directory to see them.
 ```

Sometimes Claude would say it was done with type-checks but still had some test errors it considered as not important because they were from the old implementation, so I needed to add:

```markdown
You should always update tests to match our new implementations.
```

Sometimes it attempted to run pytest directly and I needed to prompt with:

```markdown
As the docs/DEV_GUIDE.md says, you always need to use `uv` to run python scripts so they are run in the correct environment. Please review the dev guide and continue.
```

This resulted in:

- Cost: $27.90
- Commit: 9911bf4f08b916748872eb60782020cd4c52840c

