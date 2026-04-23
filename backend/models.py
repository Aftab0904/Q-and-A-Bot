from pydantic import BaseModel
from typing import Optional

class AskRequest(BaseModel):
    document_id: str
    question: str
    model: Optional[str] = "llama-3.3-70b-versatile"
