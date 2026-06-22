from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ConversationState(TypedDict, total=False):
    session_id: str

    messages: Annotated[list[BaseMessage], add_messages]

    entities: dict[str, Any]

    active_intents: list[str]

    current_intent: str | None

    response: str | None

    # True when the patient was identified from JWT at connection time
    patient_preloaded: bool
