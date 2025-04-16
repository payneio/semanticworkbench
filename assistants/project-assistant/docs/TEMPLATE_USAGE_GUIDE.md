# Project Assistant Template Usage Guide

This document provides comprehensive guides for using both templates available in the Project Assistant:
1. **Default Template**: Project management with tracking features
2. **Context Transfer Template**: Knowledge sharing without formal project structure

Each template is designed for specific use cases, with distinct workflows and capabilities.

## Default Template: Project Management

### Use Cases

The Default Template is ideal for:
- Formal project management with well-defined goals
- Team collaboration on projects with clear deliverables
- Projects requiring progress tracking and status updates
- Tasks with measurable success criteria
- Structured workflows with distinct planning and working phases

### Coordinator Guide

As a Project Coordinator using the Default Template:

1. **Start a New Project**
   ```
   /start
   ```
   This initializes a new project with you as the Coordinator and creates a sharable link for team members.

2. **Set Up Project Brief**
   ```
   /brief create name:"Website Redesign" description:"Complete overhaul of the company website with new branding and functionality" goals:[{"name":"Design System", "description":"Create a unified design system", "success_criteria":["Define color scheme", "Create component library", "Document usage guidelines"]}, {"name":"Frontend Implementation", "description":"Implement responsive website", "success_criteria":["Create React component structure", "Implement responsive layouts", "Add interactive elements"]}, {"name":"Content Migration", "description":"Move content to new site", "success_criteria":["Audit existing content", "Adapt content to new format", "QA content on new site"]}]
   ```

3. **Share with Team Members**
   ```
   /share
   ```
   Provides the shareable link for team members to join the project. Send this link via external communication.

4. **View Project Dashboard**
   ```
   /dashboard
   ```
   Shows the current project status, goals, and success criteria with completion percentages.

5. **Set Project State to Ready for Team Work**
   ```
   /state ready
   ```
   Indicates the project is properly set up and team members can start working.

6. **Monitor Information Requests**
   ```
   /requests
   ```
   View all information requests from team members that need your attention.

7. **Resolve Information Requests**
   ```
   /resolve request_id:"51a2b3c4" resolution:"The design mockups are available in the Figma project. I've shared access with the team and uploaded the export as a file here."
   ```
   Then upload any relevant files to resolve the request.

8. **View and Update Project Whiteboard**
   ```
   /whiteboard
   ```
   View the auto-generated whiteboard containing key project information.

9. **Complete the Project**
   ```
   /state complete summary:"The website redesign has been successfully completed with all goals achieved. The new site is now live at company.com."
   ```

### Team Member Guide

As a Team Member using the Default Template:

1. **Join a Project**
   Join by clicking the share link provided by the Coordinator or use:
   ```
   /join code:<share-code>
   ```

2. **View Project Information**
   ```
   /dashboard
   ```
   View the project goals, success criteria and current status.

3. **Make Information Requests**
   ```
   /request title:"Need design mockups" description:"I need the final design mockups for the homepage and product pages to implement the frontend components" priority:"high"
   ```

4. **Delete Outdated Requests**
   ```
   /delete request_id:"51a2b3c4"
   ```

5. **View Coordinator Messages**
   ```
   /coordinator
   ```
   View recent messages between the Coordinator and the assistant for context.

6. **Mark Criteria as Complete**
   ```
   /complete criterion_id:"goal_1_criterion_2"
   ```
   This updates the project dashboard with your progress.

7. **View Project Whiteboard**
   ```
   /whiteboard
   ```
   Access the auto-updating knowledge repository for the project.

## Context Transfer Template: Knowledge Sharing

### Use Cases

The Context Transfer Template is ideal for:
- Knowledge sharing without formal project structure
- Educational contexts where one person explains complex topics to others
- Documentation of expertise or domain knowledge
- Handover scenarios when transferring responsibilities
- Context sharing when onboarding new team members

### Knowledge Owner Guide (Coordinator Role)

As a Knowledge Owner using the Context Transfer Template:

1. **Start Knowledge Space**
   ```
   /start
   ```
   Initializes a new knowledge space with you as the Knowledge Owner and creates a sharable link for recipients.

2. **Set Up Knowledge Overview**
   ```
   /brief create name:"Machine Learning Fundamentals" description:"Core concepts and practical approaches for understanding machine learning" knowledge_areas:[{"name":"Supervised Learning", "description":"Learning from labeled examples", "key_points":["Classification algorithms", "Regression techniques", "Evaluation metrics"]}, {"name":"Unsupervised Learning", "description":"Finding patterns in unlabeled data", "key_points":["Clustering methods", "Dimensionality reduction", "Anomaly detection"]}, {"name":"Model Deployment", "description":"Taking models to production", "key_points":["Model serialization", "API development", "Monitoring and maintenance"]}]
   ```

3. **Share with Knowledge Recipients**
   ```
   /share
   ```
   Provides the shareable link for recipients to access the knowledge space.

4. **Add Context Through Conversation**
   Simply chat naturally about the topic. The assistant will automatically extract key information into the whiteboard, organizing it for easy reference.

5. **Address Knowledge Requests**
   ```
   /requests
   ```
   View questions or clarification requests from recipients.

6. **Respond to Knowledge Requests**
   ```
   /resolve request_id:"51a2b3c4" resolution:"Linear regression works by finding the best-fitting line through your data points by minimizing the sum of squared residuals. Here's a detailed explanation with an example..."
   ```

7. **Upload Supporting Materials**
   Share documents, diagrams, and other resources by uploading files directly in the conversation.

8. **View Knowledge Whiteboard**
   ```
   /whiteboard
   ```
   Review the auto-organized knowledge extracted from your conversations.

### Knowledge Recipient Guide (Team Member Role)

As a Knowledge Recipient using the Context Transfer Template:

1. **Access Knowledge Space**
   Join by clicking the share link provided by the Knowledge Owner or use:
   ```
   /join code:<share-code>
   ```

2. **View Knowledge Overview**
   ```
   /dashboard
   ```
   Access the structured knowledge overview and key areas.

3. **Request Clarification or Additional Information**
   ```
   /request title:"Neural Network Activation Functions" description:"Could you explain the differences between ReLU, sigmoid, and tanh activation functions and when to use each one?" priority:"medium"
   ```

4. **Delete Resolved Requests**
   ```
   /delete request_id:"51a2b3c4"
   ```

5. **View Knowledge Owner's Explanations**
   ```
   /coordinator
   ```
   Access the Knowledge Owner's conversation history for context.

6. **Reference the Knowledge Whiteboard**
   ```
   /whiteboard
   ```
   Access the organized knowledge repository that updates automatically.

## Template Comparison

| Feature | Default Template | Context Transfer Template |
|---------|------------------|---------------------------|
| **Primary Purpose** | Project management with tracking | Knowledge sharing without tracking |
| **Terminology** | Coordinator & Team Members | Knowledge Owner & Recipients |
| **Dashboard** | Goals, criteria & completion status | Knowledge areas & key points |
| **Success Criteria** | Trackable with completion status | Simple bullet points without tracking |
| **Project States** | Planning → Ready → In Progress → Complete | Not applicable |
| **Commands** | Full set of project management commands | Knowledge sharing focused commands |
| **Whiteboard** | Project-focused information organization | Knowledge-focused information organization |
| **Message Storage** | Up to 50 regular, 100 important messages | Up to 50 regular, 100 important messages |

## Best Practices

### Default Template

1. **Start with a detailed brief**: Clearly define goals and measurable success criteria
2. **Use meaningful goal names**: Brief, action-oriented descriptions work best
3. **Break down complex goals**: Use multiple success criteria for complex tasks
4. **Transition states appropriately**: Use `/state ready` when planning is complete
5. **Upload relevant files**: Share documents directly in the conversation
6. **Address information requests promptly**: Keep the team unblocked

### Context Transfer Template

1. **Structure knowledge areas logically**: Organize by topics or complexity
2. **Explain concepts conversationally**: Have a natural dialogue with the assistant
3. **Upload supporting materials**: Include diagrams, examples, and references
4. **Encourage knowledge requests**: Let recipients know they should ask questions
5. **Use the whiteboard as reference**: Direct recipients to check the auto-organized whiteboard
6. **Be specific in knowledge areas**: Focus on clear, distinct topics

## Switching Templates

Templates must be selected at assistant creation time and cannot be changed mid-conversation. If you need to switch templates:

1. Create a new assistant with the desired template
2. Manually transfer key information to the new assistant
3. Share the new assistant with team members

## Command Reference

| Command | Default Template | Context Transfer Template |
|---------|------------------|---------------------------|
| `/start` | Creates new project | Creates new knowledge space |
| `/join` | Joins existing project | Joins existing knowledge space |
| `/brief` | Project goals & criteria | Knowledge areas & key points |
| `/dashboard` | Shows project status | Shows knowledge overview |
| `/requests` | Project-related requests | Knowledge-related questions |
| `/whiteboard` | Project knowledge base | Knowledge repository |
| `/resolve` | Resolves blockers | Answers knowledge questions |
| `/state` | Updates project lifecycle | Not available |
| `/complete` | Marks criteria complete | Not available |
| `/coordinator` | Shows coordinator messages | Shows knowledge owner messages |
| `/help` | Template-specific help | Template-specific help |
