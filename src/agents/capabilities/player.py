import dataclasses

import pydantic_ai
import teyuna_core
import teyuna_sdk
from pydantic_ai import capabilities


@dataclasses.dataclass
class PlayerDependencies:
    client: teyuna_sdk.GameClient


player_capability = capabilities.Capability[PlayerDependencies](
    description=(
        "Interact with a Teyuna game you already joined. Use get_game_state to "
        "inspect the public board and turn state, get_hand for your private "
        "resources/cards, and submit_action to play legal moves for the current phase."
    ),
)


@player_capability.tool
async def get_game_state(
    ctx: pydantic_ai.RunContext[PlayerDependencies],
    /,
) -> teyuna_core.Game:
    """Fetch the public game state.

    Call this first on every tick before deciding whether to act.

    The following are important fiels from the result object:
    - `phase`: current phase name (e.g. "dice roll", "trade and build").
    - `turn_order`: nicknames in turn order; index 0 is the active player.
    - `to_discard_resources`: map of nickname → cards to discard. If your
      nickname is listed, you must discard even when it is not your turn.
    - `players`: public information about the players, like settlement/path
        counts of resources or wisdom cards (but not exact cards).
    - `settlements` / `paths` / `map` / `conquistator_location` / `harbours`:
      board geometry for placement and blocking decisions.
    - `trade_proposals`: open offers you may accept.

    Sample call: get_game_state()
    """
    return await ctx.deps.client.get_game()


@player_capability.tool
async def get_hand(
    ctx: pydantic_ai.RunContext[PlayerDependencies],
    /,
) -> teyuna_core.PlayerHand:
    """Fetch your private hand (resources + wisdom cards).

    Public game state does not reveal your exact resource counts or card types.
    Call this when you need to:
    - decide what to discard (`discard resources` phase),
    - decide what you can afford to build or buy,
    - choose which wisdom card to play,
    - craft a trade offer/request.

    Returns `{ "resources": {"wood": 2, ...}, "wisdom_cards": ["warrior", ...] }`.

    Sample call: get_hand()
    """
    return await ctx.deps.client.get_hand()


@player_capability.tool(retries=5)
async def submit_action(
    ctx: pydantic_ai.RunContext[PlayerDependencies],
    /,
    action: teyuna_core.AnyPlayerAction,
) -> teyuna_core.AnyActionExecutionResult:
    """
    Submit one legal player action for the current
    phase.
    """
    return await ctx.deps.client.submit_action(action)
