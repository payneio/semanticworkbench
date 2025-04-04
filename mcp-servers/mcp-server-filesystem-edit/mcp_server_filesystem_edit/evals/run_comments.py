# Copyright (c) Microsoft. All rights reserved.

import asyncio
import logging
import os

from dotenv import load_dotenv
from mcp_extensions.llm.openai_chat_completion import openai_client
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel

from mcp_server_filesystem_edit.evals.common import load_test_cases
from mcp_server_filesystem_edit.tools.add_comments import CommonComments
from mcp_server_filesystem_edit.types import (
    CommentOutput,
    CustomContext,
    FileOpRequest,
)

logger = logging.getLogger(__name__)

load_dotenv(override=True)


def print_output(
    output: CommentOutput,
    test_index: int,
    custom_context: CustomContext,
) -> None:
    console = Console()
    console.rule(f"Test Case {test_index} Results. Latency: {output.llm_latency:.2f} seconds.", style="cyan")
    console.print(
        Panel(
            custom_context.chat_history[-1].content,  # type: ignore
            title="User Request",
            border_style="blue",
            width=120,
        )
    )
    original_doc = Panel(
        custom_context.document,
        title="Original Document",
        border_style="yellow",
        width=90,
    )
    new_doc = Panel(
        output.new_content,
        title="Commented Document",
        border_style="green",
        width=90,
    )
    console.print(Columns([original_doc, new_doc]))
    console.print(
        Panel(
            output.comment_instructions,
            title="Comment Instructions",
            border_style="blue",
            width=120,
        )
    )
    console.print()


async def main() -> None:
    custom_contexts = load_test_cases(test_case_type="comments")
    client = openai_client(
        api_type="azure_openai",
        azure_endpoint=os.getenv("ASSISTANT__AZURE_OPENAI_ENDPOINT"),
        aoai_api_version="2025-01-01-preview",
    )

    for i, custom_context in enumerate(custom_contexts):
        edit_request = FileOpRequest(
            context=custom_context,
            file_type=custom_context.file_type,
            request_type="dev",
            chat_completion_client=client,
            file_content=custom_context.document,
        )
        commenter = CommonComments()
        output = await commenter.run(edit_request)
        print_output(output, i, custom_context)


if __name__ == "__main__":
    asyncio.run(main())
