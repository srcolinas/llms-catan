import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def end_turn(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
) -> teyuna_core.AnyActionExecutionResult:
    """End your trade-and-build phase when no better actions remain."""
    return await submit.submit_action(ctx, teyuna_core.PlayerAction())


toolset = pydantic_ai.FunctionToolset(
    tools=[end_turn],
    max_retries=5,
)
