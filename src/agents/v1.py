import asyncio
import dataclasses
import logging
import string
import uuid
from typing import Any, Final

import httpx2
import pydantic_ai

import settings

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Dependencies:
    client: httpx2.AsyncClient


@dataclasses.dataclass
class HTTPResponse:
    status_code: int
    data: dict[str, Any]
    headers: dict[str, str]
    error: str | None = None


class Agent:
    _nickname: Final[str] = "Hernán Darío"

    _instructions: Final[string.Template] = string.Template(
        """
        Your nickname is $nickname.
        You are a skilled Teyuna player (a Catan-like game).
        You are given the rulebook and a guide about how to play the game
        and you need to figure out things by yourself.

        The first action you will need to do is to join the game. Afterwards,
        you will be prompted to check the game state and perform the best possible
        action. 

        $rulebook

        $howto
        """
    )

    def __init__(self, settings_: settings.Settings):
        self._settings = settings_
        self._agent = self._build_agent()
        self._history_id = 0

    def _build_agent(self) -> pydantic_ai.Agent[Dependencies]:
        rulebook = self._settings.rulebook.read_text()
        howto = self._settings.howto.read_text()

        agent = pydantic_ai.Agent(
            name=f"bare-{self._settings.llm_model.model_name}",
            model=self._settings.llm_model,
            deps_type=Dependencies,
            instructions=self._instructions.substitute(
                rulebook=rulebook, howto=howto, nickname=self._nickname
            ),
            tools=[
                pydantic_ai.Tool(
                    make_api_request, takes_ctx=True, max_retries=5
                )
            ],
        )
        return agent

    async def loop(
        self,
        *,
        game_id: uuid.UUID,
        base_url: str,
    ) -> None:

        async with httpx2.AsyncClient(base_url=base_url) as client:
            deps = Dependencies(client=client)
            while True:
                prompt = (
                    f"You are playing game {game_id}, now:\n"
                    "1. Figure out if there is any action for you to take\n"
                    "2. If there are some actions for you, pick the best possible action.\n"
                    "3. Reply with a short summary of what you observed and what you did.\n"
                )

                await self._agent.run(prompt, deps=deps)

                await asyncio.sleep(self._settings.sleep_seconds)


async def make_api_request(
    ctx: pydantic_ai.RunContext[Dependencies],
    method: str,
    endpoint: str,
    bearer_token: str = "",
    payload: dict[str, Any] | None = None,
) -> HTTPResponse:
    """Call the Teyuna game HTTP API.

    Args:
        method: HTTP method such as "GET" or "POST".
        endpoint: Path relative to the API base URL
            (e.g. "/some/endpoint").
        payload: JSON body for POST requests. Ignore for GET requests.
        bearer_token: token to use in endpoints that require authentication.
            Ignore for endpoints that don't require authentication.

    Returns:
        status_code, parsed JSON data (when available), response headers, and
        any error message. Read error/detail fields carefully on non-2xx responses.
    """
    client = ctx.deps.client
    headers = None
    if bearer_token is not None:
        headers = {"Authorization": f"Bearer {bearer_token}"}
    response = await client.request(
        method=method, url=endpoint, json=payload, headers=headers
    )
    response_headers = dict(response.headers)

    try:
        data = response.json()
    except httpx2.HTTPStatusError as e:
        logger.error("HTTP status error: %s", e)
        return HTTPResponse(
            status_code=response.status_code,
            data={},
            headers=response_headers,
            error=str(e),
        )
    return HTTPResponse(
        status_code=response.status_code,
        data=data,
        headers=response_headers,
        error=None,
    )
