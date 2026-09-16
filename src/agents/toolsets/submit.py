import logging

import httpx2
import pydantic_ai
import teyuna_core

from . import dependencies

logger = logging.getLogger(__name__)


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
