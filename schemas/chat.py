from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    message: str
    agent_override: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    metadata: Optional[Dict[str, Any]] = None
