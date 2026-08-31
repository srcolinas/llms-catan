import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Protocol

import settings
from agents import v1

logger = logging.getLogger(__name__)
logging.getLogger("httpx2").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class Agent(Protocol):
    async def loop(self, *, game_id: uuid.UUID, base_url: str) -> None: ...


_AGENT_VERSIONS: dict[str, Callable[[settings.Settings], Agent]] = {
    "v1": v1.Agent,
}


async def main(game_id: uuid.UUID, base_url: str, agent_version: str) -> None:
    settings_ = settings.settings()
    loglevel = logging.getLevelNamesMapping()[settings_.loglevel]
    logging.basicConfig(level=loglevel)

    agent = _AGENT_VERSIONS[agent_version](settings_)
    await agent.loop(game_id=game_id, base_url=base_url)


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
