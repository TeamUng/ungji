from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph

from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.decision_policy import entry_route, route_agent
from app.services.nodes.classify import classify
from app.services.nodes.common import make_chat_response
from app.services.nodes.helper import helper
from app.services.nodes.motivator import motivator

logger = get_logger(__name__)


def _motivator_node(state: ChatState) -> dict:
    response = motivator(state)
    return {
        "response": response,
        "chat_history": [AIMessage(content=_response_to_chat_text(response))],
    }


def _helper_node(state: ChatState) -> dict:
    result = helper(state)
    response = make_chat_response(state["thread_id"], result["helper_response"])
    extra = {
        "response": response,
        "chat_history": [AIMessage(content=_response_to_chat_text(response))],
    }
    for key in ("current_problem", "tp4_phase", "tp4_turn_count"):
        if key in result:
            extra[key] = result[key]
    return extra


def _response_to_chat_text(response: ChatResponse) -> str:
    chunks: list[str] = []
    for message in response.messages:
        if message.type == "text":
            chunks.append(message.content)
        elif message.type == "choices":
            chunks.append("\n".join(f"- {item.id}: {item.label}" for item in message.items))
        elif message.type == "hint_card":
            chunks.append("\n".join(f"{step.step}. {step.content}" for step in message.steps))
        elif message.type == "image_card":
            chunks.append(f"[image] {message.caption}")
    return "\n\n".join(chunk for chunk in chunks if chunk)


_builder = StateGraph(ChatState)

_builder.add_node("classify", classify)
_builder.add_node("motivator", _motivator_node)
_builder.add_node("helper", _helper_node)

_builder.add_conditional_edges(START, entry_route)
_builder.add_conditional_edges("classify", route_agent)

memory = InMemorySaver()
graph = _builder.compile(checkpointer=memory)
