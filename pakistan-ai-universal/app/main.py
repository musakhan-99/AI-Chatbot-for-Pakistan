from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .models import ChatRequest, ChatResponse, Source
from .services.llm import LLMError, UniversalLLM, build_provider_config
from .services.prompt import build_system_prompt, build_user_prompt
from .services.source_router import official_sources_for_query, topic_warnings
from .services.wikipedia import WikipediaRetriever

settings = get_settings()
provider_config = build_provider_config(settings)

app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

wiki = WikipediaRetriever(
    results=settings.wikipedia_results,
    chars_per_page=settings.wikipedia_chars_per_page,
)


class RequestGuard:
    def __init__(self):
        self.by_ip: dict[str, deque[float]] = defaultdict(deque)
        self.daily_count = 0
        self.day_key = time.strftime("%Y-%m-%d", time.gmtime())
        self.lock = asyncio.Lock()

    async def check(self, ip: str) -> None:
        async with self.lock:
            now = time.time()
            q = self.by_ip[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= settings.max_requests_per_minute_per_ip:
                raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute and try again.")
            q.append(now)

            current_day = time.strftime("%Y-%m-%d", time.gmtime())
            if current_day != self.day_key:
                self.day_key = current_day
                self.daily_count = 0

            if settings.max_daily_llm_requests > 0 and self.daily_count >= settings.max_daily_llm_requests:
                raise HTTPException(
                    status_code=429,
                    detail="This deployment has reached its configured daily AI request limit.",
                )
            self.daily_count += 1


guard = RequestGuard()


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "provider": provider_config.provider,
        "provider_configured": provider_config.configured,
        "api_style": provider_config.style,
        "model": provider_config.model or "not configured",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    ip = request.client.host if request.client else "unknown"
    await guard.check(ip)

    query = payload.message.strip()
    warnings = topic_warnings(query)

    # Retrieve general/background context from Wikipedia.
    wiki_pages = await wiki.search(query, payload.language)
    official = official_sources_for_query(query)

    sources: list[Source] = []
    for page in wiki_pages:
        sources.append(
            Source(
                title=page.title,
                url=page.url,
                source_type="wikipedia",
                authority="Wikipedia",
                language=page.language,
            )
        )
    for item in official:
        sources.append(Source(**item))

    system_prompt = build_system_prompt(payload.mode, payload.language, warnings)
    user_prompt = build_user_prompt(query, wiki_pages, official)
    history = [{"role": item.role, "content": item.content} for item in payload.history[-8:]]

    try:
        llm = UniversalLLM(provider_config)
        answer = await llm.answer(system_prompt, user_prompt, history)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        answer=answer,
        sources=sources,
        warnings=warnings,
        used_retrieval=bool(wiki_pages),
        model=provider_config.model,
    )
