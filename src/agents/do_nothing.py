import pydantic_ai


def do_nothing() -> str:
    """Skip acting this turn without submitting a game action.

    Call this when no other available tool is appropriate.
    """
    return "Did nothing."


tool = pydantic_ai.Tool(do_nothing, takes_ctx=False)
