# Project Tools Improvements

This document outlines the specific changes needed to make project tools template-aware and improve their functionality. These changes are part of the work outlined in WORKING.md and tracked in IMPLEMENTATION_PROGRESS.md.

## Template-Aware Tools Implementation

### 1. Modify ProjectTools class initialization

The `ProjectTools` class in `project_tools.py` needs several changes to support template awareness:

```python
def __init__(self, context: ConversationContext, role: str):
    """
    Initialize the project tools with the current conversation context.

    Args:
        context: The conversation context
        role: The assistant's role ("coordinator" or "team")
    """
    self.context = context
    self.role = role
    self.tool_functions = ToolFunctions()
    
    # Determine if this is using the context transfer template
    # We need to initialize this asynchronously later
    self.is_context_transfer = False

    # Register common tools for both roles and templates
    self.tool_functions.add_function(
        self.get_project_info, "get_project_info", "Get information about the current project state"
    )
    
    # The suggest_next_action tool is always available regardless of role or template
    self.tool_functions.add_function(
        self.suggest_next_action, "suggest_next_action", "Suggest the next action to take in the project"
    )

    # Register role-specific tools
    # (Template-specific tools will be updated in setup_tools_for_template method,
    # which will be called asynchronously after initialization)
    if role == "coordinator":
        # Coordinator-specific tools that work in all templates
        self.tool_functions.add_function(
            self.create_project_brief,
            "create_project_brief",
            "Create a project brief with a name and description",
        )
        
        # Resolve requests works in all templates
        self.tool_functions.add_function(
            self.resolve_information_request,
            "resolve_information_request", 
            "Resolve an information request with information",
        )
        
        # These tools may be disabled later for context transfer template
        self.tool_functions.add_function(
            self.add_project_goal,
            "add_project_goal",
            "Add a goal to the project brief with optional success criteria",
        )
        self.tool_functions.add_function(
            self.mark_project_ready_for_working,
            "mark_project_ready_for_working",
            "Mark the project as ready for working",
        )
    else:
        # Team-specific tools that work in all templates
        self.tool_functions.add_function(
            self.create_information_request,
            "create_information_request",
            "Create an information request for information or to report a blocker",
        )
        self.tool_functions.add_function(
            self.delete_information_request,
            "delete_information_request",
            "Delete an information request that is no longer needed",
        )
        self.tool_functions.add_function(
            self.view_coordinator_conversation,
            "view_coordinator_conversation",
            "View recent messages from the coordinator's conversation",
        )
        
        # These tools may be disabled later for context transfer template
        self.tool_functions.add_function(
            self.update_project_dashboard,
            "update_project_dashboard",
            "Update the status and progress of the project",
        )
        self.tool_functions.add_function(
            self.mark_criterion_completed, 
            "mark_criterion_completed", 
            "Mark a success criterion as completed"
        )
        self.tool_functions.add_function(
            self.report_project_completion", 
            "report_project_completion", 
            "Report that the project is complete"
        )
```

### 2. Add setup_tools_for_template method

A new method is needed to configure tools based on template after initialization:

```python
async def setup_tools_for_template(self):
    """
    Configures tools based on the active template (context transfer or default).
    
    This needs to be called after initialization since it requires async operations
    to determine the template type.
    """
    # Determine if this is using context transfer template
    from .template_utils import is_context_transfer_template
    self.is_context_transfer = await is_context_transfer_template(self.context)
    
    # If this is context transfer template, disable progress tracking tools
    if self.is_context_transfer:
        # For coordinator in context transfer mode:
        # - Disable goal management
        # - Disable project lifecycle management
        if self.role == "coordinator":
            logger.info("Context transfer template: Disabling progress tracking tools for coordinator")
            
            # Create replacement function with appropriate message
            async def disabled_add_goal(*args, **kwargs):
                return "This feature is not available in the Context Transfer template. Focus on sharing knowledge context instead of setting formal goals."
            
            async def disabled_mark_ready(*args, **kwargs):
                return "The Context Transfer template doesn't use project lifecycle states. Focus on organizing and sharing knowledge instead."
            
            # Replace the functions with disabled versions
            self.tool_functions.function_map["add_project_goal"] = disabled_add_goal
            self.tool_functions.function_map["mark_project_ready_for_working"] = disabled_mark_ready
            
            # Update descriptions to indicate limited functionality
            for i, func in enumerate(self.tool_functions.schema["functions"]):
                if func["name"] == "add_project_goal":
                    self.tool_functions.schema["functions"][i]["description"] = "Not available in Context Transfer template"
                elif func["name"] == "mark_project_ready_for_working":
                    self.tool_functions.schema["functions"][i]["description"] = "Not available in Context Transfer template"
            
        # For team in context transfer mode:
        # - Disable progress tracking
        # - Disable dashboard updates
        # - Disable criterion completion
        elif self.role == "team":
            logger.info("Context transfer template: Disabling progress tracking tools for team")
            
            # Create replacement functions with appropriate messages
            async def disabled_dashboard(*args, **kwargs):
                return "This feature is not available in the Context Transfer template. Focus on exploring the shared knowledge instead of tracking progress."
            
            async def disabled_criterion(*args, **kwargs):
                return "The Context Transfer template doesn't use success criteria. Focus on asking questions about the shared knowledge context instead."
                
            async def disabled_completion(*args, **kwargs):
                return "The Context Transfer template doesn't use project completion tracking. Focus on knowledge exploration instead."
            
            # Replace the functions with disabled versions
            self.tool_functions.function_map["update_project_dashboard"] = disabled_dashboard
            self.tool_functions.function_map["mark_criterion_completed"] = disabled_criterion
            self.tool_functions.function_map["report_project_completion"] = disabled_completion
            
            # Update descriptions to indicate limited functionality
            for i, func in enumerate(self.tool_functions.schema["functions"]):
                if func["name"] == "update_project_dashboard":
                    self.tool_functions.schema["functions"][i]["description"] = "Not available in Context Transfer template"
                elif func["name"] == "mark_criterion_completed":
                    self.tool_functions.schema["functions"][i]["description"] = "Not available in Context Transfer template"
                elif func["name"] == "report_project_completion":
                    self.tool_functions.schema["functions"][i]["description"] = "Not available in Context Transfer template"
        
        # Update method and error messages to be template-aware
        # For information requests
        for i, func in enumerate(self.tool_functions.schema["functions"]):
            if func["name"] == "create_information_request":
                # Give the tool a more appropriate name in the context transfer template
                self.tool_functions.schema["functions"][i]["description"] = "Create a knowledge request for more information"
```

### 3. Update get_project_tools function

The `get_project_tools` function needs to be updated to call the new setup method:

```python
async def get_project_tools(context: ConversationContext, role: str) -> ProjectTools:
    """
    Get the appropriate tool functions for the given role.

    Args:
        context: The conversation context
        role: The role, either "coordinator" or "team"

    Returns:
        A ProjectTools instance with the appropriate tool functions
    """
    # Create the tools instance
    tools = ProjectTools(context, role)
    
    # Configure based on template
    await tools.setup_tools_for_template()
    
    return tools
```

### 4. Make get_project_info template-aware

The `get_project_info` method should also be updated to be template-aware:

```python
async def get_project_info(self, info_type: Literal["all", "brief", "whiteboard", "dashboard", "requests"]) -> str:
    """
    Get information about the current project.

    Args:
        info_type: Type of information to retrieve. Must be one of: all, brief, whiteboard, dashboard, requests.

    Returns:
        Information about the project in a formatted string
    """
    # Use template-aware naming
    if self.is_context_transfer:
        section_titles = {
            "brief": "Knowledge Context",
            "whiteboard": "Knowledge Content",
            "dashboard": "Status Information",
            "requests": "Knowledge Requests"
        }
    else:
        section_titles = {
            "brief": "Project Brief",
            "whiteboard": "Project Whiteboard",
            "dashboard": "Project Dashboard",
            "requests": "Information Requests"
        }
    
    # Validate input
    if info_type not in ["all", "brief", "whiteboard", "dashboard", "requests"]:
        return f"Invalid info_type: {info_type}. Must be one of: all, brief, whiteboard, dashboard, requests. Use 'all' to get all information types."

    # Get the project ID for the current conversation
    project_id = await ProjectManager.get_project_id(self.context)
    if not project_id:
        template_name = "context transfer" if self.is_context_transfer else "project"
        return f"No {template_name} associated with this conversation. Start by creating a brief."

    # Rest of the implementation follows with appropriate section titles
    # ...
```

## Update the Tool Functions for Context Transfer

The implementation of several tools needs to be updated to be template-aware:

1. `create_information_request` - Update naming and descriptions based on template
2. `delete_information_request` - Update naming and descriptions based on template
3. `view_coordinator_conversation` - Make text template-aware
4. `suggest_next_action` - Make suggestions template-appropriate

## Implementation Notes

1. The changes should maintain backward compatibility with existing projects
2. Tools should gracefully handle template switches if a project changes templates
3. Error messages should be informative and explain why certain features are unavailable
4. All user-visible text should use consistent terminology based on the template

## Testing Plan

1. Test all tool functions in both templates
2. Test disable/enable behavior when template changes
3. Test error handling for unavailable features
4. Test the display of tool schemas in both templates