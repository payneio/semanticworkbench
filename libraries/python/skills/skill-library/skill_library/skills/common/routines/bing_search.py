from typing import Any, Optional

from duckduckgo_search import DDGS
from skill_library import AskUserFn, EmitFn, RunContext, RunRoutineFn


async def main(
    context: RunContext,
    routine_state: dict[str, Any],
    emit: EmitFn,
    run: RunRoutineFn,
    ask_user: AskUserFn,
    q: str,
    num_results: Optional[int] = 7,
) -> list[str]:
    """Search using DuckDuckGo (free alternative to deprecated Bing API)."""

    # common_skill = cast(CommonSkill, context.skills["common"])

    try:
        with DDGS() as ddgs:
            # Get search results from DuckDuckGo
            results = list(ddgs.text(
                keywords=q,
                max_results=num_results or 7,
                region='us-en',
                safesearch='moderate'
            ))

            # Extract URLs from results
            urls = [result['href'] for result in results if 'href' in result]

            context.log(f"DuckDuckGo search completed for query: {q}", {
                "num_results_requested": num_results,
                "num_results_found": len(urls),
                "query": q
            })

            return urls

    except Exception as e:
        context.log("Error during DuckDuckGo search.", {
            "exception": str(e),
            "query": q,
            "num_results": num_results
        })
        raise e
