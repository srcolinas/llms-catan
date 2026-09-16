import uuid

import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def offer_trade_to_active_player(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    offer: dict[teyuna_core.ResourceCard, int],
    request: dict[teyuna_core.ResourceCard, int],
) -> teyuna_core.AnyActionExecutionResult:
    """Propose a trade only to the player whose turn it is."""
    return await submit.submit_action(
        ctx,
        teyuna_core.ProposeTradeAction(
            offer=offer,
            request=request,
            to={ctx.deps.game.turn_order[0]},
        ),
    )


async def accept_trade(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    id: uuid.UUID,
) -> teyuna_core.AnyActionExecutionResult:
    """Accept an open trade proposal by id."""
    return await submit.submit_action(ctx, teyuna_core.AcceptTradeAction(id=id))


toolset = pydantic_ai.FunctionToolset(
    tools=[offer_trade_to_active_player, accept_trade],
    max_retries=5,
)
