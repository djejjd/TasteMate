from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from tastemate.tools.get_profile import get_profile_tool
from tastemate.tools.rank_candidates import rank_candidates_tool
from tastemate.tools.record_feedback import record_feedback_tool

mcp = FastMCP("tastemate")


@mcp.tool()
def rank_candidates(query: str, candidates: list[dict[str, Any]], taste_mode: str = "force") -> dict[str, Any]:
    """Rank recommendation candidates when the user explicitly asks with @taste."""
    return rank_candidates_tool(query=query, candidates=candidates, taste_mode=taste_mode)


@mcp.tool()
def record_feedback(
    query: str,
    user_feedback: str,
    selected_candidate_ids: list[str],
    rejected_candidate_ids: list[str],
    candidates_snapshot: list[dict[str, Any]],
) -> dict[str, Any]:
    """Record explicit user feedback after a TasteMate-ranked answer."""
    return record_feedback_tool(
        query=query,
        user_feedback=user_feedback,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        candidates_snapshot=candidates_snapshot,
    )


@mcp.tool()
def get_profile() -> dict[str, Any]:
    """Return the current local TasteMate profile summary."""
    return get_profile_tool()


if __name__ == "__main__":
    mcp.run()
