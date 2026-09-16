import uuid

import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def trade_with_supply(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    offers: teyuna_core.ResourceCard,
    requests: teyuna_core.ResourceCard,
) -> teyuna_core.AnyActionExecutionResult | str:
    """Trade with the bank or a harbour at the applicable rate.

    Args:
        offers: Resource type you give.
        requests: Resource type you take.
    """
    fresh = await submit.refresh_game(ctx)
    skipped = submit.skip_if_not_trade_and_build(fresh)
    if skipped is not None:
        return skipped
    return await submit.submit_action(
        ctx,
        teyuna_core.TradeWithSupplyAction(offers=offers, requests=requests),
    )


async def offer_trade(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    offer: dict[teyuna_core.ResourceCard, int],
    request: dict[teyuna_core.ResourceCard, int],
    to: set[str],
) -> teyuna_core.AnyActionExecutionResult | str:
    """Propose a player-to-player trade to one or more opponents."""
    fresh = await submit.refresh_game(ctx)
    skipped = submit.skip_if_not_trade_and_build(fresh)
    if skipped is not None:
        return skipped
    return await submit.submit_action(
        ctx,
        teyuna_core.ProposeTradeAction(offer=offer, request=request, to=to),
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
    tools=[trade_with_supply, offer_trade, accept_trade],
    max_retries=5,
)
