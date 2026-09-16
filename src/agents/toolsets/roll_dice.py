import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def roll_dice(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
) -> teyuna_core.AnyActionExecutionResult:
    """Roll the dice to produce resources or trigger a 7.

    Only call this if you do not need to play a wisdom card first. Warrior is
    typically played before rolling. If you intend to play a wisdom card this
    phase, call play_wisdom_card instead and do not roll yet.
    """
    return await submit.submit_action(ctx, teyuna_core.PlayerAction())


toolset = pydantic_ai.FunctionToolset(
    tools=[roll_dice],
    max_retries=5,
)
