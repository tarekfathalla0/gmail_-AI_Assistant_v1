from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from langchain_core.messages import HumanMessage

from schemas.agent import AgentRequest, AgentResponse

from agents.supervisor.graph import supervisor_graph


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

    result = await supervisor_graph.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=request.message
                )
            ],

            "user_id": request.user_id,
            "thread_id": request.thread_id,
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