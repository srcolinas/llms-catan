import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def play_blessed(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    resources: tuple[teyuna_core.ResourceCard, teyuna_core.ResourceCard],
) -> teyuna_core.AnyActionExecutionResult:
    """Resolve Blessing of Aluna: take two resources from the bank.

    Args:
        resources: The two resource types to take (duplicates allowed).
    """
    return await submit.submit_action(
        ctx, teyuna_core.PlayBlessedAction(resources=resources)
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[play_blessed],
    max_retries=5,
)
