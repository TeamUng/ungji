from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.core.logging import get_logger
from app.data.loader import load_student
from app.schemas.chat import ChatRequest
from app.services.graph import graph

logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    # student_id 존재 여부를 스트리밍 전에 검증한다
    try:
        load_student(request.student_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"student not found: {request.student_id}")

    initial_state: dict = {
        "thread_id": request.thread_id,
        "student_id": request.student_id,
        "use_case": request.use_case,
        "current_touchpoint": request.current_touchpoint,
        "chat_history": (
            [HumanMessage(content=request.message.content)]
            if request.message.content
            else []
        ),
        "response": None,
    }
    config = {
        "configurable": {"thread_id": request.thread_id},
        "run_name": f"chat:{request.current_touchpoint.value}:{request.student_id}",
        "tags": [
            "chat-api",
            request.use_case.value,
            request.current_touchpoint.value,
            request.student_id,
        ],
        "metadata": {
            "student_id": request.student_id,
            "use_case": request.use_case.value,
            "touchpoint": request.current_touchpoint.value,
        },
    }

    async def generate():
        try:
            async for event in graph.astream(initial_state, config):
                for node_output in event.values():
                    if not isinstance(node_output, dict):
                        continue
                    response = node_output.get("response")
                    if response is not None:
                        yield f"data: {response.model_dump_json()}\n\n"
        except Exception:
            logger.exception(
                "chat 스트리밍 오류",
                extra={"student_id": request.student_id},
            )
            raise

    return StreamingResponse(generate(), media_type="text/event-stream")
