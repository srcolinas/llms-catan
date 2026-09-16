import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def move_conquistator(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    q: int,
    r: int,
    from_player: str | None = None,
) -> teyuna_core.AnyActionExecutionResult:
    """Move the conquistator to a different hex; optionally steal one resource.

    Args:
        q: Axial q of the destination hex. Must not be the current
            conquistator hex.
        r: Axial r of the destination hex.
        from_player: Nickname to steal one random resource from, if they hold
            cards. Omit to move without stealing.
    """
    return await submit.submit_action(
        ctx,
        teyuna_core.MoveConquistatorAction(q=q, r=r, from_player=from_player),
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[move_conquistator],
    max_retries=5,
)
