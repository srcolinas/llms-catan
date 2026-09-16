import pydantic_ai
import teyuna_core
from teyuna_sdk import rules

from . import dependencies, submit


async def list_vertices_available_for_building(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
) -> tuple[teyuna_core.Coordinate, ...]:
    """List vertices where you can legally build a terrace.

    Call this before `build_settlement` and pass one of the returned
    coordinates.
    """
    return rules.vertices_available_for_building(
        ctx.deps.game, by=ctx.deps.nickname
    )


async def list_edges_available_for_building(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
) -> tuple[teyuna_core.Coordinate, ...]:
    """List edges where you can legally build a path.

    Call this before `build_path` and pass one of the returned coordinates.
    """
    return rules.edges_available_for_building(
        ctx.deps.game, by=ctx.deps.nickname
    )


async def list_terraces_available_to_upgrade(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
) -> tuple[teyuna_core.Coordinate, ...]:
    """List your terraces that can be upgraded to a great terrace.

    Call this before `upgrade_settlement` and pass one of the returned
    coordinates.
    """
    return rules.built_terraces(ctx.deps.game, by=ctx.deps.nickname)


async def build_settlement(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    coordinate: teyuna_core.Coordinate,
) -> teyuna_core.AnyActionExecutionResult:
    """Build a terrace at the given coordinate.

    Args:
        coordinate: Vertex where the new terrace sits.
    """
    return await submit.submit_action(
        ctx,
        teyuna_core.BuildSettlementAction(
            item=teyuna_core.SettlementType.TERRACE, coordinate=coordinate
        ),
    )


async def upgrade_settlement(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    coordinate: teyuna_core.Coordinate,
) -> teyuna_core.AnyActionExecutionResult:
    """Upgrade a terrace to a great terrace at the given coordinate.

    Args:
        coordinate: Vertex of one of your existing terraces.
    """
    return await submit.submit_action(
        ctx,
        teyuna_core.BuildSettlementAction(
            item=teyuna_core.SettlementType.GREAT_TERRACE, coordinate=coordinate
        ),
    )


async def build_path(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    coordinate: teyuna_core.Coordinate,
) -> teyuna_core.AnyActionExecutionResult:
    """Build a path on an edge.

    Args:
        coordinate: Edge coordinate for the new path.
    """
    return await submit.submit_action(
        ctx, teyuna_core.BuildPathAction(coordinate=coordinate)
    )


async def buy_wisdom_card(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
) -> teyuna_core.AnyActionExecutionResult:
    """Buy a face-down wisdom card from the deck."""
    return await submit.submit_action(ctx, teyuna_core.BuyWisdomCardAction())


toolset = pydantic_ai.FunctionToolset(
    tools=[
        list_vertices_available_for_building,
        list_edges_available_for_building,
        list_terraces_available_to_upgrade,
        build_settlement,
        upgrade_settlement,
        build_path,
        buy_wisdom_card,
    ],
    max_retries=5,
)
