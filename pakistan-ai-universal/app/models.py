from typing import Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    mode: Literal["local", "visitor"] = "local"
    language: Literal["auto", "en", "ur", "roman-ur", "ps"] = "auto"
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class Source(BaseModel):
    title: str
    url: str
    source_type: Literal["wikipedia", "official"]
    authority: str | None = None
    language: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    used_retrieval: bool = False
    model: str
