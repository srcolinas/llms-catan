import dataclasses

import teyuna_core
import teyuna_sdk


@dataclasses.dataclass
class Dependencies:
    client: teyuna_sdk.GameClient
    game: teyuna_core.Game
    nickname: str
