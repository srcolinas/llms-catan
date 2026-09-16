import asyncio
import contextlib
import logging
import pathlib
import uuid
from typing import Protocol

import pydantic_ai
import teyuna_core
import teyuna_sdk

import langfuse
import settings
from agents import v1, v2, v3, v4

logger = logging.getLogger(__name__)
logging.getLogger("httpx2").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpcore2").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Agent(Protocol):
    def __init__(
        self,
        game_id: uuid.UUID,
        base_url: str,
        settings_: settings.Settings,
    ) -> None: ...

    async def loop(self) -> None: ...


_AGENT_VERSIONS: dict[str, type[Agent]] = {
    "v1": v1.Agent,
    "v2": v2.Agent,
    "v3": v3.Agent,
    "v4": v4.Agent,
}


async def _wait_until_active(client: teyuna_sdk.GameClient) -> None:
    """Block until the lobby closes; ``/events`` rejects lobby-phase games."""
    while True:
        game = await client.get_game()
        if game.phase is not teyuna_core.GamePhaseName.LOBBY:
            return
        logger.info("Waiting for game to start...")
        await asyncio.sleep(2)


async def _log_game_events(
    client: teyuna_sdk.GameClient, path: pathlib.Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    await _wait_until_active(client)
    with path.open("a", encoding="utf-8") as file:
        while True:
            try:
                async for event in client.stream_events():
                    try:
                        file.write(event.model_dump_json() + "\n")
                        file.flush()
                    except Exception:
                        logger.exception("Failed to write game event")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Game event stream failed")
                await asyncio.sleep(1)


async def main(game_id: uuid.UUID, base_url: str, agent_version: str) -> None:
    settings_ = settings.settings()
    loglevel = logging.getLevelNamesMapping()[settings_.loglevel]
    logging.basicConfig(level=loglevel)

    observer = langfuse.Langfuse(
        public_key=settings_.langfuse_public_key.get_secret_value(),
        secret_key=settings_.langfuse_secret_key.get_secret_value(),
        base_url=settings_.langfuse_base_url,
    )
    pydantic_ai.Agent.instrument_all()

    events_log = settings_.events_log
    events_log.parent.mkdir(parents=True, exist_ok=True)
    events_log.write_text("", encoding="utf-8")
    events_client = teyuna_sdk.GameClient(base_url=base_url, game_id=game_id)
    log_task = asyncio.create_task(_log_game_events(events_client, events_log))

    agent = _AGENT_VERSIONS[agent_version](game_id, base_url, settings_)
    try:
        await agent.loop()
    finally:
        log_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await log_task
        observer.flush()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--game-id", type=uuid.UUID, required=True)
    parser.add_argument("--base-url", type=str, required=True)
    parser.add_argument(
        "--agent-version",
        type=str,
        default="v1",
        choices=list(_AGENT_VERSIONS.keys()),
    )
    args = parser.parse_args()
    asyncio.run(main(args.game_id, args.base_url, args.agent_version))
