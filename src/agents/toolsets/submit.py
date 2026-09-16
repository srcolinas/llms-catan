import logging

import httpx2
import pydantic_ai
import teyuna_core

from . import dependencies

logger = logging.getLogger(__name__)


async def refresh_game(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
) -> teyuna_core.Game:
    fresh = await ctx.deps.client.get_game()
    ctx.deps.game = fresh
    return fresh


def skip_if_not_trade_and_build(game: teyuna_core.Game) -> str | None:
    if game.phase is teyuna_core.GamePhaseName.TRADE_AND_BUILD:
        return None
    return (
        f"Skipped: phase is now '{game.phase.value}', not trade and build. "
        "Do not retry this trade."
    )


async def submit_action(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    action: teyuna_core.AnyPlayerAction,
) -> teyuna_core.AnyActionExecutionResult:
    try:
        return await ctx.deps.client.submit_action(action)
    except httpx2.HTTPStatusError as e:
        logger.error("Error submitting action: %s", e)
        raise pydantic_ai.ModelRetry(
            f"Error submitting action: {e.response.text}"
        ) from None
