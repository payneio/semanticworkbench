# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Semantic Workbench Developer Guidelines

## Common Commands
* Build/Install: `make install` (recursive for all subdirectories)
* Format: `make format` (runs ruff formatter)
* Lint: `make lint` (runs ruff linter)
* Type-check: `make type-check` (runs pyright)
* Test: `make test` (runs pytest)
* Single test: `uv run pytest tests/test_file.py::test_function -v`

## Code Style
### Python
* Indentation: 4 spaces
* Line length: 120 characters
* Imports: stdlib → third-party → local, alphabetized within groups
* Naming: `snake_case` for functions/variables, `CamelCase` for classes, `UPPER_SNAKE_CASE` for constants
* Types: Use type annotations consistently; prefer Union syntax (`str | None`) for Python 3.10+
* Documentation: Triple-quote docstrings with param/return descriptions

## Tools
* Python: Uses uv for environment/dependency management
* Linting/Formatting: Ruff (Python)
* Type checking: Pyright (Python)
* Testing: pytest (Python)
* Package management: uv (Python)

## Project Assistant Architecture

The Project Assistant supports two configuration templates:

1. **Default Project Assistant** - For project management with goals, success criteria, and progress tracking
2. **Context Transfer** - For transferring knowledge context without progress tracking

Template detection happens in `template_utils.py` with the function `is_context_transfer_template()`.

Within each template, there are two roles:

1. **Coordinator** - Creates project brief, resolves information requests
2. **Team Member** - Works on tasks, creates information requests

When making code work with both templates:

1. Use `is_context_transfer_template()` to detect the active template
2. Check early in functions to give template-specific responses
3. Use "Knowledge request" terminology in Context Transfer template instead of "Information request"
4. Make progress tracking tools return helpful messages in Context Transfer template