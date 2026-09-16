import asyncio
import dataclasses
import datetime
import logging
import string
import uuid
from typing import Final

import httpx2
import pydantic_ai
import teyuna_core
import teyuna_sdk

import settings

from . import do_nothing

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Dependencies:
    client: teyuna_sdk.GameClient


class Agent:
    _nickname: Final[str] = "Jorge Varon"

    _instructions: Final[string.Template] = string.Template(
        """
        You are a skilled Teyuna (a Catan-like game) player.
        You are given the rulebook and a guide about how to play the game 
        and you need to figure out things by yourself.

        Your nickname is $nickname.

        You have already joined the game. You will be prompted in situations
        where there is any meaningful action you can take and you will
        be told the list of possible actions at that moment.
        
        Don't ask the user for confirmation, guidance or anything else, 
        the user will just tell you when you need to respond and the results 
        of tool calls you requested.

        You cannot move the game with text. Every turn must call a tool.
        
        $rulebook

        $board_description
        
        """
    )

    def __init__(
        self, game_id: uuid.UUID, base_url: str, settings_: settings.Settings
    ):
        self._settings = settings_
        self._agent = self._build_agent()
        self._game_server_url = base_url
        self._game_id = game_id

    def _build_agent(
        self,
    ) -> pydantic_ai.Agent[Dependencies]:
        rulebook = self._settings.rulebook.read_text()
        howto = self._settings.howto.read_text()
        board_description = self._settings.board_description.read_text()
        agent = pydantic_ai.Agent(
            model=self._settings.llm_model,
            model_settings=self._settings.model_settings,
            deps_type=Dependencies,
            instructions=self._instructions.substitute(
                rulebook=rulebook,
                howto=howto,
                board_description=board_description,
                nickname=self._nickname,
            ),
            tools=[
                pydantic_ai.Tool(submit_action, takes_ctx=True, max_retries=5),
                do_nothing.tool,
            ],
        )
        return agent

    async def loop(self) -> None:

        client = teyuna_sdk.GameClient(
            base_url=self._game_server_url, game_id=self._game_id
        )
        client = await client.authenticate(self._nickname)
        deps = Dependencies(client=client)
        while True:
            game = await client.get_game()
            if game.phase is teyuna_core.GamePhaseName.END_GAME:
                return
            action_kinds = _PHASE_TO_ACTION_KINDS.get(game.phase)
            if action_kinds is None:
                await asyncio.sleep(self._settings.sleep_seconds)
                continue
            is_active = (
                bool(game.turn_order) and game.turn_order[0] == self._nickname
            )
            if game.phase is teyuna_core.GamePhaseName.DISCARD_RESOURCES:
                should_act = self._nickname in game.to_discard_resources
            elif game.phase is teyuna_core.GamePhaseName.TRADE_AND_BUILD:
                should_act = True
            else:
                should_act = is_active
            if not should_act:
                await asyncio.sleep(self._settings.sleep_seconds)
                continue
            if (
                game.phase is teyuna_core.GamePhaseName.TRADE_AND_BUILD
                and not is_active
            ):
                can_accept_trade = any(
                    self._nickname in proposal.to
                    for proposal in game.trade_proposals
                )
                action_kinds = (
                    ("propose_trade", "accept_trade")
                    if can_accept_trade
                    else ("propose_trade",)
                )
            if _phase_deadline_soon(
                game.phase_deadline, _PHASE_DEADLINE_BUFFER
            ):
                if "advance" in action_kinds:
                    logger.info(
                        "Phase deadline in less than %s; submitting advance",
                        _PHASE_DEADLINE_BUFFER,
                    )
                    try:
                        await client.submit_action(teyuna_core.PlayerAction())
                    except httpx2.HTTPStatusError as e:
                        logger.error("Error submitting advance: %s", e)
                continue
            hand = await client.get_hand()
            prompt = (
                f"Your hand: {hand.model_dump_json(indent=2)}\n"
                f"Game state: {game.model_dump_json(indent=2)}\n"
                f"Consider the following possible actions: {action_kinds}\n"
                "Pick the best action for you to take.\n"
                "After you have used a tool, tell a short summary of what you did. Include the action you took.\n"
            )
            await self._agent.run(prompt, deps=deps)


_PHASE_DEADLINE_BUFFER: Final[datetime.timedelta] = datetime.timedelta(
    seconds=20
)


def _phase_deadline_soon(
    phase_deadline: datetime.datetime | None, buffer: datetime.timedelta
) -> bool:
    if phase_deadline is None:
        return False
    deadline = phase_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=datetime.UTC)
    remaining = deadline - datetime.datetime.now(datetime.UTC)
    return remaining < buffer


_PHASE_TO_ACTION_KINDS: Final[
    dict[teyuna_core.GamePhaseName, tuple[str, ...]]
] = {
    teyuna_core.GamePhaseName.FIRST_PLACEMENT: (
        "free_placement",
        "advance",
    ),
    teyuna_core.GamePhaseName.SECOND_PLACEMENT: (
        "free_placement",
        "advance",
    ),
    teyuna_core.GamePhaseName.DICE_ROLL: ("advance", "play_wisdom_card"),
    teyuna_core.GamePhaseName.DISCARD_RESOURCES: ("discard_resources",),
    teyuna_core.GamePhaseName.MOVE_CONQUISTATOR: (
        "move_conquistator",
        "advance",
    ),
    teyuna_core.GamePhaseName.DICE_PLAY_WARRIOR: (
        "move_conquistator",
        "advance",
    ),
    teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_WARRIOR: (
        "move_conquistator",
        "advance",
    ),
    teyuna_core.GamePhaseName.DICE_PLAY_MAMO: ("play_mamo", "advance"),
    teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_MAMO: (
        "play_mamo",
        "advance",
    ),
    teyuna_core.GamePhaseName.DICE_PLAY_BLESSED: ("play_blessed", "advance"),
    teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_BLESSED: (
        "play_blessed",
        "advance",
    ),
    teyuna_core.GamePhaseName.DICE_PLAY_PATHFINDER: (
        "play_pathfinder",
        "advance",
    ),
    teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_PATHFINDER: (
        "play_pathfinder",
        "advance",
    ),
    teyuna_core.GamePhaseName.TRADE_AND_BUILD: (
        "advance",
        "build_settlement",
        "build_path",
        "buy_wisdom_card",
        "play_wisdom_card",
        "propose_trade",
        "accept_trade",
        "trade_with_supply",
    ),
}


async def submit_action(
    ctx: pydantic_ai.RunContext[Dependencies],
    /,
    action: teyuna_core.AnyPlayerAction,
) -> teyuna_core.AnyActionExecutionResult:
    """
    Submit one legal player action for the current
    phase.
    """
    try:
        result = await ctx.deps.client.submit_action(action)
    except httpx2.HTTPStatusError as e:
        logger.error("Error submitting action: %s", e)
        raise pydantic_ai.ModelRetry(
            f"Error submitting action: {e.response.text}"
        ) from None
    return result
