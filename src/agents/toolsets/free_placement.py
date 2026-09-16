import pydantic
import pydantic_ai
import teyuna_core
from teyuna_sdk import rules

from . import dependencies, submit


class FreePlacementOption(pydantic.BaseModel):
    terrace: teyuna_core.Coordinate
    paths: tuple[teyuna_core.Coordinate, ...]
    produces: dict[teyuna_core.ResourceCard, int]


async def list_free_placement_options(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
) -> tuple[FreePlacementOption, ...]:
    """List legal terrace vertices with adjacent paths and production.

    Call this before `free_placement`. Pick `terrace` from an option and one
    of that option's `paths`. `produces` maps each resource at the terrace
    vertex to that hex's production number, the closer to 7 the better.
    """
    game = ctx.deps.game
    hex_by_location = {hex_tile.coordinate: hex_tile for hex_tile in game.map}
    options: list[FreePlacementOption] = []
    for terrace in rules.vertices_available_for_free_placement(game):
        paths = rules.edges_for_free_placement(game, terrace)
        if not paths:
            continue
        options.append(
            FreePlacementOption(
                terrace=terrace,
                paths=paths,
                produces=_produces_at_vertex(terrace, hex_by_location),
            )
        )
    return tuple(options)


def _produces_at_vertex(
    terrace: teyuna_core.Coordinate,
    hex_by_location: dict[teyuna_core.HexLocation, teyuna_core.Hex],
) -> dict[teyuna_core.ResourceCard, int]:
    produces: dict[teyuna_core.ResourceCard, int] = {}
    for location in teyuna_core.hex_locations_at_vertex(
        terrace.q, terrace.r, terrace.d
    ):
        hex_tile = hex_by_location.get(location)
        if hex_tile is None or hex_tile.number is None:
            continue
        resource = teyuna_core.HEX_TYPE_TO_RESOURCE.get(hex_tile.type)
        if resource is None:
            continue
        produces[resource] = hex_tile.number
    return produces


async def free_placement(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    terrace: teyuna_core.Coordinate | None = None,
    path: teyuna_core.Coordinate | None = None,
) -> teyuna_core.AnyActionExecutionResult:
    """Place one free terrace and one adjacent path during setup.

    Args:
        terrace: Vertex coordinate for the terrace. Omit to let the server
            pick a legal vertex.
        path: Edge coordinate for the path, adjacent to the terrace. Omit to
            let the server pick a legal edge.
    """
    return await submit.submit_action(
        ctx, teyuna_core.FreePlacementAction(terrace=terrace, path=path)
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[list_free_placement_options, free_placement],
    max_retries=5,
)
