import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def play_mamo(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    resource: teyuna_core.ResourceCard,
) -> teyuna_core.AnyActionExecutionResult:
    """Resolve Wisdom of Mamo: monopolize one resource type from all opponents.

    Args:
        resource: Resource type to take from every other player.
    """
    return await submit.submit_action(
        ctx, teyuna_core.PlayMamoAction(resource=resource)
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[play_mamo],
    max_retries=5,
)
