"""
Nischay AI — Chat Service
Real LLM-powered coaching via Groq API.
"""

import json
import sqlite3
from typing import AsyncGenerator, Dict, Any, Optional

from groq import Groq

from core.config import settings
from services.llm import LLMService
from services.intelligence_service import IntelligenceService
from db.queries import (
    get_conversation_history,
    get_student_profile,
    get_student_memories,
    save_chat_message,
)

SYSTEM_PROMPT = """You are Nischay, an AI life and career coach built for Indian students.

You have deep psychological intelligence. You analyze what the user shares, identify hidden patterns, detect contradictions between stated goals and revealed preferences, and provide grounded, actionable guidance.

Your reasoning principles:
- Never echo the user's message back. Always reason before responding.
- Detect when a student is driven by external pressure (family, society) vs. intrinsic motivation.
- Name contradictions directly but compassionately: "You said X, but earlier you mentioned Y — let's explore that tension."
- Use real data when possible: placement stats, salary ranges, career timelines relevant to India.
- Ask insightful follow-up questions that help the student discover their own answer.
- Track behavioral drift: if the student's stated goals shift between sessions, flag it.
- Be specific, not generic. Avoid platitudes like "follow your passion." Instead: "Your analytical signal is strong, but your risk tolerance is low — here's what that combination usually means for career satisfaction at year 5."

You respond as a senior coach, not a chatbot. You are direct, warm, and precise.

When analyzing stress, anxiety, or emotional topics:
- Validate the feeling first, then explore root causes
- Connect emotional patterns to career decision-making
- Offer concrete coping strategies alongside career guidance
- Never dismiss or minimize what the user is experiencing"""

AGENT_KEYWORDS = {
    "Profile Agent": [
        "tell me about", "who am i", "my profile", "my background",
        "introduce", "about me", "personality", "traits",
    ],
    "Career Agent": [
        "career", "job", "salary", "placement", "engineer", "doctor",
        "mbbs", "btech", "nit", "iit", "company", "interview",
        "resume", "internship", "work",
    ],
    "Contradiction Agent": [
        "confused", "not sure", "conflict", "torn", "dilemma",
        "parents want", "family pressure", "but i want", "can't decide",
    ],
    "Wellness Agent": [
        "stress", "anxiety", "depressed", "overwhelmed", "burnout",
        "mental health", "can't sleep", "pressure", "worried", "scared",
        "lonely", "struggling",
    ],
}


def _detect_agent(message: str) -> str:
    msg_lower = message.lower()
    scores = {}
    for agent, keywords in AGENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > 0:
            scores[agent] = score

    if not scores:
        return "Profile Agent"

    return max(scores, key=scores.get)


def _build_messages(
    system_prompt: str,
    profile_context: str,
    memory_context: str,
    conversation_history: list,
    current_message: str,
) -> list:
    messages = [{"role": "system", "content": system_prompt}]

    if profile_context:
        messages.append({
            "role": "system",
            "content": f"[USER PROFILE CONTEXT]\n{profile_context}",
        })

    if memory_context:
        messages.append({
            "role": "system",
            "content": f"[MEMORY CONTEXT — insights from previous conversations]\n{memory_context}",
        })

    for msg in conversation_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })

    messages.append({"role": "user", "content": current_message})
    return messages


def _format_profile_context(profile: Optional[Dict]) -> str:
    if not profile:
        return ""
    parts = []
    if profile.get("name"):
        parts.append(f"Name: {profile['name']}")
    if profile.get("bio"):
        parts.append(f"Bio: {profile['bio']}")
    if profile.get("goals"):
        goals = profile["goals"]
        if isinstance(goals, str):
            try:
                goals = json.loads(goals)
            except (json.JSONDecodeError, TypeError):
                goals = [goals]
        if goals:
            parts.append(f"Goals: {', '.join(str(g) for g in goals)}")
    if profile.get("personality_signals"):
        sigs = profile["personality_signals"]
        if isinstance(sigs, str):
            try:
                sigs = json.loads(sigs)
            except (json.JSONDecodeError, TypeError):
                sigs = {}
        if sigs:
            parts.append(f"Personality signals: {json.dumps(sigs)}")
    return "\n".join(parts)


def _format_memory_context(memories: list) -> str:
    if not memories:
        return ""
    lines = []
    for m in memories[:15]:
        lines.append(f"[{m['type']}] {m['content']} (confidence: {m.get('confidence', 0)})")
    return "\n".join(lines)


class ChatService:
    def __init__(self, db: sqlite3.Connection, student_id: str):
        self.db = db
        self.student_id = student_id
        self.llm = LLMService()
        self.intel = IntelligenceService(db)

    async def process_message(
        self, session_id: str, message: str, agent_override: Optional[str] = None
    ) -> Dict[str, Any]:
        agent = agent_override or _detect_agent(message)

        profile = get_student_profile(self.db, self.student_id)
        profile_ctx = _format_profile_context(profile)

        memories = get_student_memories(self.db, self.student_id, limit=15)
        memory_ctx = _format_memory_context(memories)

        history = get_conversation_history(self.db, session_id, limit=20)

        messages = _build_messages(
            SYSTEM_PROMPT, profile_ctx, memory_ctx, history, message
        )

        save_chat_message(self.db, session_id, "user", message)

        response_text = await self.llm.completion(messages)
        
        confidence = round(0.65 + (len(history) * 0.02), 2)
        confidence = min(confidence, 0.95)

        save_chat_message(
            self.db, session_id, "assistant", response_text,
            agent=agent, confidence=confidence,
        )

        # Background analysis (sync in this simple setup)
        import asyncio
        asyncio.create_task(self.intel.analyze_interaction(self.student_id, session_id, message))

        return {
            "session_id": session_id,
            "response": response_text,
            "metadata": {
                "agent": agent,
                "confidence": f"{int(confidence * 100)}%",
            },
        }

    async def stream_message(
        self, session_id: str, message: str, agent_override: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        agent = agent_override or _detect_agent(message)

        profile = get_student_profile(self.db, self.student_id)
        profile_ctx = _format_profile_context(profile)

        memories = get_student_memories(self.db, self.student_id, limit=15)
        memory_ctx = _format_memory_context(memories)

        history = get_conversation_history(self.db, session_id, limit=20)

        messages = _build_messages(
            SYSTEM_PROMPT, profile_ctx, memory_ctx, history, message
        )

        save_chat_message(self.db, session_id, "user", message)

        confidence = round(0.65 + (len(history) * 0.02), 2)
        confidence = min(confidence, 0.95)

        yield {
            "type": "meta",
            "agent": agent,
            "confidence": f"{int(confidence * 100)}%",
            "session_id": session_id,
        }

        full_response = []
        async for token in self.llm.stream_completion(messages):
            full_response.append(token)
            yield {
                "type": "token",
                "token": token,
                "session_id": session_id,
            }

        response_text = "".join(full_response)

        save_chat_message(
            self.db, session_id, "assistant", response_text,
            agent=agent, confidence=confidence,
        )

        # Trigger Intelligence Analysis
        await self.intel.analyze_interaction(self.student_id, session_id, message)

        yield {
            "type": "done",
            "session_id": session_id,
            "agent": agent,
            "confidence": f"{int(confidence * 100)}%",
        }
