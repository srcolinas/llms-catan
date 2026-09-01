# LLMs Playing Catan

Here I experiment with LLMs to see whether they can reason in the challeging setting of playing Catan, the board game. I develop a few agents with different capabilities to see at which point the LLMs can make a decent player.

Due to copyright restrictions and unavailability of LLM friendly game server implementations, I had to build my own clone, which is basically a different skin of the traditional Catan game. It is called [Teyuna - The Lost City](https://github.com/srcolinas/teyuna) and it has pretty much the same rules, but some changes in naming conventions.

## Running simulations

Use three terminals (or keep the first two running in the background):

1. Start Langfuse once per machine with `task start-langfuse-server`.
2. Start the game server with `task start-game-server`.
3. Run a simulation with `task run AGENT_VERSION=v1`; replace `v1` with the agent version you wish to use.

`task run` creates a game, joins two builder adversaries, then joins the agent. It expects the Langfuse stack and the Teyuna server to already be up.

## Observability

Traces go to the local [Langfuse](https://langfuse.com) instance started above. Open [http://localhost:3000](http://localhost:3000) and sign in with the init user from `Taskfile.yml`.

Its ClickHouse container needs roughly 8GB of RAM available to Docker, otherwise it is OOM-killed and the whole stack restarts in a loop. On colima, `colima start --cpu 6 --memory 8` is enough.
