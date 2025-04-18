# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from mcp_extensions.llm.openai_chat_completion import openai_client
from rich.console import Console
from rich.panel import Panel

from mcp_server.app_interaction.word_editor import (
    get_active_document,
    get_word_app,
    write_markdown_to_document,
)
from mcp_server.evals.common import load_test_cases
from mcp_server.markdown_edit.feedback_step import run_feedback_step
from mcp_server.types import (
    CustomContext,
    FeedbackOutput,
    MarkdownEditRequest,
)


def write_context_to_word(custom_context: CustomContext) -> None:
    """
    Write the document content from the custom context to a Word document.

    Args:
        custom_context: Context containing the document to write
    """
    try:
        word_app = get_word_app()
        doc = get_active_document(word_app)
        write_markdown_to_document(doc, custom_context.document)
    except Exception as e:
        raise RuntimeError(f"Failed to write context to Word document.\n{e}") from e


def print_feedback_output(
    console: Console,
    output: FeedbackOutput,
    test_index: int,
    custom_context: CustomContext,
) -> None:
    """
    Print the feedback output to console using Rich formatting.

    Args:
        console: Rich console instance for formatted output
        output: The feedback output to display
        test_index: Index of the current test case
        custom_context: Context containing the document and chat history
    """
    console.rule(f"Test Case {test_index} Results. Latency: {output.llm_latency:.2f} seconds.", style="cyan")
    console.print(
        Panel(
            custom_context.chat_history[-1].content,  # type: ignore
            title="User Request",
            border_style="blue",
            width=120,
        )
    )
    console.print(
        Panel(
            output.feedback_summary,
            title="Feedback Summary",
            border_style="green",
            width=120,
        )
    )
    console.print()


async def main() -> None:
    console = Console()
    custom_contexts = load_test_cases(test_case_type="feedback")
    client = openai_client(
        api_type="azure_openai",
        azure_endpoint=os.getenv("ASSISTANT__AZURE_OPENAI_ENDPOINT"),
        aoai_api_version="2025-01-01-preview",
    )

    for i, custom_context in enumerate(custom_contexts):
        write_context_to_word(custom_context)

        markdown_edit_request = MarkdownEditRequest(
            context=custom_context,
            request_type="dev",
            chat_completion_client=client,
        )
        output = await run_feedback_step(markdown_edit_request)
        print_feedback_output(console, output, i + 1, custom_context)


if __name__ == "__main__":
    asyncio.run(main())
