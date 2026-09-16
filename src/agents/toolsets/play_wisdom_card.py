import pydantic_ai
import teyuna_core

from . import dependencies, submit


async def play_wisdom_card(
    ctx: pydantic_ai.RunContext[dependencies.Dependencies],
    /,
    card: teyuna_core.WisdomCard,
) -> teyuna_core.AnyActionExecutionResult:
    """Play a wisdom card from the playable hand (not cards bought this turn).

    During dice roll, play Warrior before rolling if you want to move the
    conquistator. Do not roll the dice if you still intend to play a card.

    Args:
        card: The wisdom card to play.
    """
    return await submit.submit_action(
        ctx, teyuna_core.PlayWisdomCardAction(card=card)
    )


toolset = pydantic_ai.FunctionToolset(
    tools=[play_wisdom_card],
    max_retries=5,
)
