import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def discard_resources(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    count: dict[teyuna_core.ResourceCard, int],
) -> teyuna_core.AnyActionExecutionResult:
    """Discard resource cards after a 7 is rolled if you have more than 7.

    The totals in `count` must sum to the amount listed for you in
    `to_discard_resources`.

    Args:
        count: Resource type to number of cards to discard.
    """
    return await submit.submit_action(
        ctx, teyuna_core.DiscardResourcesAction(count=count)
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[discard_resources],
    max_retries=5,
)
