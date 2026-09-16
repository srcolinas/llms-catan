import asyncio
import json
import string
import uuid
from collections.abc import Sequence
from typing import Final

import pydantic_ai
import teyuna_core
import teyuna_sdk

import settings

from . import do_nothing, toolsets

type _Toolset = pydantic_ai.FunctionToolset[toolsets.Dependencies]


class Agent:
    _nickname: Final[str] = "Caldas"

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

        Map:
        $map

        Harbours:
        $harbours
        
        """
    )

    def __init__(
        self, game_id: uuid.UUID, base_url: str, settings_: settings.Settings
    ):
        self._settings = settings_
        self._game_server_url = base_url
        self._game_id = game_id

    def _build_agent(
        self, game: teyuna_core.Game
    ) -> pydantic_ai.Agent[toolsets.Dependencies]:
        rulebook = self._settings.rulebook.read_text()
        howto = self._settings.howto.read_text()
        board_description = self._settings.board_description.read_text()
        dumped = game.model_dump(mode="json")
        agent = pydantic_ai.Agent(
            model=self._settings.llm_model,
            model_settings=self._settings.model_settings,
            deps_type=toolsets.Dependencies,
            instructions=self._instructions.substitute(
                rulebook=rulebook,
                howto=howto,
                board_description=board_description,
                nickname=self._nickname,
                map=json.dumps(dumped["map"], indent=2),
                harbours=json.dumps(dumped["harbours"], indent=2),
            ),
            tools=[do_nothing.tool],
        )
        return agent

    async def loop(self) -> None:
        client = teyuna_sdk.GameClient(
            base_url=self._game_server_url, game_id=self._game_id
        )
        client = await client.authenticate(self._nickname)
        agent: pydantic_ai.Agent[toolsets.Dependencies] | None = None
        while True:
            game = await client.get_game()
            if agent is None:
                agent = self._build_agent(game)
            if game.phase is teyuna_core.GamePhaseName.END_GAME:
                return

            selected = _select_toolsets(game, self._nickname)
            if selected is None:
                await asyncio.sleep(self._settings.sleep_seconds)
                continue
            hand = await client.get_hand()
            prompt = (
                f"Your hand: {hand.model_dump_json(indent=2)}\n"
                f"Game state: {_turn_state_json(game)}\n"
                "Pick the best action for you to take using the available tools.\n"
                "After you have used a tool, tell a short summary of what you did.\n"
            )
            deps = toolsets.Dependencies(
                client=client, game=game, nickname=self._nickname
            )
            await agent.run(prompt, deps=deps, toolsets=selected)


def _turn_state_json(game: teyuna_core.Game) -> str:
    dumped = game.model_dump(mode="json")
    state = {
        "players": dumped["players"],
        "settlements": dumped["settlements"],
        "paths": dumped["paths"],
        "turn_order": dumped["turn_order"],
        "phase": dumped["phase"],
        "phase_deadline": dumped["phase_deadline"],
        "conquistator_location": dumped["conquistator_location"],
    }
    if game.phase is teyuna_core.GamePhaseName.TRADE_AND_BUILD:
        state["trade_proposals"] = dumped["trade_proposals"]
    return json.dumps(state, indent=2)


def _select_toolsets(
    game: teyuna_core.Game, nickname: str
) -> Sequence[_Toolset] | None:
    is_active = bool(game.turn_order) and game.turn_order[0] == nickname
    phase = game.phase

    if phase in (
        teyuna_core.GamePhaseName.FIRST_PLACEMENT,
        teyuna_core.GamePhaseName.SECOND_PLACEMENT,
    ):
        return (toolsets.free_placement,) if is_active else None

    if phase is teyuna_core.GamePhaseName.DICE_ROLL:
        if is_active:
            return (toolsets.play_wisdom_card, toolsets.roll_dice)
        return None

    if phase is teyuna_core.GamePhaseName.DISCARD_RESOURCES:
        if nickname in game.to_discard_resources:
            return (toolsets.discard_resources,)
        return None

    if phase in (
        teyuna_core.GamePhaseName.MOVE_CONQUISTATOR,
        teyuna_core.GamePhaseName.DICE_PLAY_WARRIOR,
        teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_WARRIOR,
    ):
        return (toolsets.move_conquistator,) if is_active else None

    if phase in (
        teyuna_core.GamePhaseName.DICE_PLAY_MAMO,
        teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_MAMO,
    ):
        return (toolsets.play_mamo,) if is_active else None

    if phase in (
        teyuna_core.GamePhaseName.DICE_PLAY_BLESSED,
        teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_BLESSED,
    ):
        return (toolsets.play_blessed,) if is_active else None

    if phase in (
        teyuna_core.GamePhaseName.DICE_PLAY_PATHFINDER,
        teyuna_core.GamePhaseName.TRADE_AND_BUILD_PLAY_PATHFINDER,
    ):
        return (toolsets.play_pathfinder,) if is_active else None

    if phase is teyuna_core.GamePhaseName.TRADE_AND_BUILD:
        if is_active:
            return (
                toolsets.build,
                toolsets.play_wisdom_card,
                toolsets.trade_in_turn,
                toolsets.end_turn,
            )
        return (toolsets.trade_out_of_turn,)

    return None
