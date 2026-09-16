import asyncio
import logging
import string
import uuid
from typing import Final

import pydantic_ai
import teyuna_sdk

import settings

from . import capabilities, do_nothing

logger = logging.getLogger(__name__)


class Agent:
    _nickname: Final[str] = "J Mario"

    _instructions: Final[string.Template] = string.Template(
        """
        You are a skilled Teyuna (a Catan-like game) player.
        You are given the rulebook and a guide about how to play the game 
        and you need to figure out things by yourself.

        Your nickname is $nickname.
        You have already joined the game. Play using the provided tools.
        
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
    ) -> pydantic_ai.Agent[capabilities.PlayerDependencies]:
        rulebook = self._settings.rulebook.read_text()
        howto = self._settings.howto.read_text()
        board_description = self._settings.board_description.read_text()
        agent = pydantic_ai.Agent(
            model=self._settings.llm_model,
            model_settings=self._settings.model_settings,
            deps_type=capabilities.PlayerDependencies,
            instructions=self._instructions.substitute(
                rulebook=rulebook,
                howto=howto,
                board_description=board_description,
                nickname=self._nickname,
            ),
            tools=[do_nothing.tool],
            capabilities=[capabilities.player_capability],
        )
        return agent

    async def loop(self) -> None:

        client = teyuna_sdk.GameClient(
            base_url=self._game_server_url, game_id=self._game_id
        )
        client = await client.authenticate(self._nickname)
        deps = capabilities.PlayerDependencies(client=client)
        while True:
            prompt = (
                "1. Figure out if there is any action for you to take (advance, build, trade, etc.)\n"
                "2. If there are many possible actions for you to take, pick the best.\n"
                "3. After you have used a tool, tell a short summary of what you did.\n"
            )
            await self._agent.run(prompt, deps=deps)

            await asyncio.sleep(self._settings.sleep_seconds)
