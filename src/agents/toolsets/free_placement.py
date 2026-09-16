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
    """List legal terrace-and-path pairs for free placement.

    Call this before `free_placement`. Each option is a terrace plus only the
    paths that adjoin that terrace. Pass that option's `terrace` and one of
    **that same option's** `paths` to `free_placement`. Do not invent
    coordinates or mix a terrace from one option with a path from another.
    `produces` maps each resource at the terrace vertex to that hex's
    production number, the closer to 7 the better.
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

    Call `list_free_placement_options` first. `path` must be one of the
    `paths` on the same option as `terrace`. Do not invent coordinates or
    mix a terrace from one option with a path from another.

    Args:
        terrace: Vertex from one list option. Omit to let the server pick a
            legal vertex.
        path: One edge from that same option's `paths`. Omit to let the
            server pick a legal edge adjoining the terrace.
    """
    if terrace is not None and path is not None:
        legal = rules.edges_for_free_placement(ctx.deps.game, terrace)
        if path not in legal:
            raise pydantic_ai.ModelRetry(
                "Path "
                f"{path.model_dump(mode='json')} is not adjacent to terrace "
                f"{terrace.model_dump(mode='json')}. Use a path from the "
                "same list_free_placement_options entry. Legal paths for "
                f"this terrace: {[p.model_dump(mode='json') for p in legal]}."
            )
    return await submit.submit_action(
        ctx, teyuna_core.FreePlacementAction(terrace=terrace, path=path)
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[list_free_placement_options, free_placement],
    max_retries=5,
)
