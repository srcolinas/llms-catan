import uuid

import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def offer_trade_to_active_player(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    offer: dict[teyuna_core.ResourceCard, int],
    request: dict[teyuna_core.ResourceCard, int],
) -> teyuna_core.AnyActionExecutionResult | str:
    """Propose a trade only to the player whose turn it is."""
    fresh = await submit.refresh_game(ctx)
    skipped = submit.skip_if_not_trade_and_build(fresh)
    if skipped is not None:
        return skipped
    return await submit.submit_action(
        ctx,
        teyuna_core.ProposeTradeAction(
            offer=offer,
            request=request,
            to={fresh.turn_order[0]},
        ),
    )


async def accept_trade(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    id: uuid.UUID,
) -> teyuna_core.AnyActionExecutionResult | str:
    """Accept an open trade proposal by id."""
    fresh = await submit.refresh_game(ctx)
    skipped = submit.skip_if_not_trade_and_build(fresh)
    if skipped is not None:
        return skipped
    return await submit.submit_action(ctx, teyuna_core.AcceptTradeAction(id=id))


toolset = pydantic_ai.FunctionToolset(
    tools=[offer_trade_to_active_player, accept_trade],
    max_retries=5,
)
