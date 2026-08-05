from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

from agent import run_email_agent, stream_email_agent
from schemas.agent import AgentRequest, AgentResponse

router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.post(
    "/run",
    response_model=AgentResponse,
)
async def run_agent(request: AgentRequest):

    result = await run_email_agent(
        message=request.message,
        thread_id=request.thread_id,
        user_id=request.user_id,
    )

    message_content = result["messages"][-1].content

    if isinstance(message_content, list):
        response_text = "\n".join(
            block.get("text", "")
            for block in message_content
            if isinstance(block, dict)
        )
    else:
        response_text = message_content

    return AgentResponse(
        response=response_text
    )


@router.post("/stream")
async def stream_agent(request: AgentRequest):

    async def event_generator():

        async for chunk in stream_email_agent(
            message=request.message,
            thread_id=request.thread_id,
            user_id=request.user_id,
        ):

            message = chunk[0]

            if hasattr(message, "content") and message.content:
                yield (
                    f"data: {json.dumps({'token': message.content})}\n\n"
                )

        yield "event: end\ndata: done\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )