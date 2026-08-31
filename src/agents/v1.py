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
    _nickname: Final[str] = "Hernan Darío"

    _instructions: Final[string.Template] = string.Template(
        """
        Your nickname is $nickname.
        You are a skilled Teyuna player (a Catan-like game).
        Your goal is to reach 10 victory points before your opponents.

        ## Interface
        Play exclusively through `make_api_request`. Paths are relative to
        the API base URL.
        - If you are unsure about endpoints or request/response schemas,
          GET `/openapi.json` once and reuse what you learn.
        - Join with POST `/games/{game_id}/players` and a unique nickname
          (do not reuse names already seated).
        - Persist the `token` from the join response. On later authenticated
          calls (hand, actions, etc.), pass
          `headers={"Authorization": "Bearer <token>"}`.
        - Submit moves with POST `/games/{game_id}/actions` using the
          `kind` and fields from the how-to below.
        - Inspect public state with GET `/games/{game_id}` and your private
          hand with GET `/games/{game_id}/hand` when needed.

        ## Turn discipline
        Each tick: read game state, then act only when required (see how-to).
        Prefer legal, high-value moves. If a request returns 400, read the
        error detail, correct the payload, and retry once if still useful.
        Do not re-join after you already have a token. Do not spam the same
        failed action.

        ## Rulebook
        $rulebook

        ## How to play
        $howto
        """
    )

    def __init__(self, settings_: settings.Settings):
        self._settings = settings_
        self._agent = self._build_agent()

    def _build_agent(self) -> pydantic_ai.Agent[Dependencies]:
        raise NotImplementedError

    async def loop(
        self,
        *,
        game_id: uuid.UUID,
        base_url: str,
    ) -> None:

        raise NotImplementedError


async def make_api_request(
    ctx: pydantic_ai.RunContext[Dependencies],
    method: str,
    endpoint: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> HTTPResponse:
    """Call the Teyuna game HTTP API.

    Args:
        method: HTTP method such as "GET" or "POST".
        endpoint: Path relative to the API base URL
            (e.g. "/openapi.json", "/games/{game_id}", "/games/{game_id}/actions").
        payload: JSON body for POST requests. Use an empty dict for GET.
        headers: Optional HTTP headers. After joining, pass
            {"Authorization": "Bearer <token>"} on authenticated endpoints.

    Returns:
        status_code, parsed JSON data (when available), response headers, and
        any error message. Read error/detail fields carefully on non-2xx responses.
    """
    client = ctx.deps.client
    response = await client.request(
        method=method, url=endpoint, json=payload, headers=headers
    )
    response_headers = dict(response.headers)

    try:
        data = response.json()
    except httpx2.HTTPStatusError as e:
        logger.error("HTTP status error: {%s}", e)
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
