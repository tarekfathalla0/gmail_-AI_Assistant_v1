from pydantic import BaseModel


class AgentRequest(BaseModel):
    message: str
    thread_id: str = "default"
    user_id: str = "default"


class AgentResponse(BaseModel):
    response: str