from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from langchain_core.messages import HumanMessage

from schemas.agent import AgentRequest, AgentResponse

from agents.supervisor.graph import supervisor_graph
from agent import has_pending_email_approval, run_email_agent


router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.post(
    "/run",
    response_model=AgentResponse,
)
async def run_agent(
    request: AgentRequest,
):

    pending_approval = await has_pending_email_approval(request.thread_id)

    if pending_approval:
        result = await run_email_agent(
            message=request.message,
            thread_id=request.thread_id,
            user_id=request.user_id,
            pending_approval=True,
        )
        return AgentResponse(
            response=result["messages"][-1].content
        )

    result = await supervisor_graph.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=request.message
                )
            ],

            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "pending_email_approval": pending_approval,
        },

        config={
            "configurable": {
                "thread_id": request.thread_id,
            }
        },
    )

    return AgentResponse(
        response=result["final_response"]
    )