import asyncio
import dataclasses
import logging
import string
import uuid
from typing import Any, Final

import httpx2
import pydantic
import pydantic_ai
from pydantic_ai.capabilities import Hooks
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.tools import ToolDefinition

import settings

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Dependencies:
    client: httpx2.AsyncClient


class HTTPResponse(pydantic.BaseModel):
    status_code: int = pydantic.Field(description="HTTP status code.")
    data: dict[str, Any] = pydantic.Field(
        description="Parsed JSON data when available."
    )
    headers: dict[str, str] = pydantic.Field(description="Response headers.")
    error: str | None = pydantic.Field(
        default=None,
        description=(
            "Error message, if any. Read error/detail fields carefully "
            "on non-2xx responses."
        ),
    )


class Agent:
    _nickname: Final[str] = "Hernan Dario"

    _instructions: Final[string.Template] = string.Template(
        """
        You are a skilled Teyuna player (a Catan-like game).
        You are given the rulebook and a guide about how to play the game 
        and you need to figure out things by yourself.

        Your nickname is $nickname.
        
        Your role is to play the game on your own (as $nickname), using the
        make_api_request tool to interact with the game API.
        
        Don't ask the user for confirmation, guidance or anything else, 
        the user will just tell you when you need to respond and the results 
        of tool calls you requested.

        When prompted by the user the first time, you need to join the game. 
        Afterwards, the user will continue to prompt you and you need to
        figure out what to do.

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
            name=f"bare-{self._settings.llm_model}",
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
            capabilities=[_tool_arg_logging_hooks],
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
            await self._agent.run(f"The game is {game_id}", deps=deps)
            while True:
                prompt = (
                    "1. Figure out if there is any action for you to take (join, advance, build, trade, etc.)\n"
                    "2. If there are many possible actions for you to take, pick the best.\n"
                    "3. Reply with a short summary of your conclusions and what you did.\n"
                )

                await self._agent.run(prompt, deps=deps)

                await asyncio.sleep(self._settings.sleep_seconds)


_tool_arg_logging_hooks = Hooks()


@_tool_arg_logging_hooks.on.before_tool_validate
async def log_tool_args_before_validate(
    ctx: pydantic_ai.RunContext[Dependencies],
    /,
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: str | dict[str, Any],
) -> str | dict[str, Any]:
    logger.debug(
        "Tool %s args before validation (call_id=%s): %s",
        call.tool_name,
        call.tool_call_id,
        args,
    )
    return args


@_tool_arg_logging_hooks.on.after_tool_validate
async def log_tool_args_after_validate(
    ctx: pydantic_ai.RunContext[Dependencies],
    /,
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: dict[str, Any],
) -> dict[str, Any]:
    logger.debug(
        "Tool %s args after validation (call_id=%s): %s",
        call.tool_name,
        call.tool_call_id,
        args,
    )
    return args


class RequestParams(pydantic.BaseModel):
    method: str = pydantic.Field(
        description='HTTP method such as "GET" or "POST".'
    )
    endpoint: str = pydantic.Field(
        description='Path relative to the API base URL (e.g. "/some/endpoint").'
    )
    bearer_token: str | None = pydantic.Field(
        default=None,
        description=(
            "Token to use in endpoints that require authentication. "
            "Ignore for endpoints that don't require authentication."
        ),
    )
    payload: dict[str, Any] | None = pydantic.Field(
        default=None,
        description="JSON body for POST requests. Ignore for GET requests.",
    )


async def make_api_request(
    ctx: pydantic_ai.RunContext[Dependencies],
    params: RequestParams,
) -> HTTPResponse:
    """Call the Teyuna game HTTP API."""
    client = ctx.deps.client
    headers = None
    if params.bearer_token is not None:
        headers = {"Authorization": f"Bearer {params.bearer_token}"}

    logger.debug(
        "Making API request to %s with method %s and payload %s and headers %s",
        params.endpoint,
        params.method,
        params.payload,
        headers,
    )

    response = await client.request(
        method=params.method,
        url=params.endpoint,
        json=params.payload,
        headers=headers,
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
    resp = HTTPResponse(
        status_code=response.status_code,
        data=data,
        headers=response_headers,
        error=None,
    )
    logger.debug(
        "API request to %s with method %s and payload %s and headers %s returned %s",
        params.endpoint,
        params.method,
        params.payload,
        headers,
        resp,
    )
    return resp
