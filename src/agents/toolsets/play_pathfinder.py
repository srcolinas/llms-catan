import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def play_pathfinder(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    paths: tuple[teyuna_core.Coordinate, ...],
) -> teyuna_core.AnyActionExecutionResult:
    """Resolve Pathfinder: place the given free paths.

    Args:
        paths: Edge coordinates to build for free. Empty is allowed; the server
            truncates to remaining path supply.
    """
    return await submit.submit_action(
        ctx, teyuna_core.PlayPathfinderAction(paths=paths)
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[play_pathfinder],
    max_retries=5,
)
