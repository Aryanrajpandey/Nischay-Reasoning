"""
Intelligence Service — Analyzes chat interactions to extract psychological signals and memories.
"""

import json
import sqlite3
from typing import Dict, Any, List, Optional
from services.llm import LLMService
from db.queries import (
    get_student_profile,
    update_student_profile,
    save_memory,
    get_conversation_history,
)

INTELLIGENCE_PROMPT = """You are the Nischay Intelligence Engine. You analyze student-coach conversations to extract psychological markers, career preferences, and behavioral signals.

Return ONLY a JSON object. Do not include any other text.

[SCHEMA]
{
  "personality_signals": {
    "risk_tolerance": int (0-100, null if not clear),
    "intrinsic_motivation": int (0-100, null if not clear),
    "analytical_style": int (0-100, null if not clear),
    "conscientiousness": int (0-100, null if not clear)
  },
  "memories": [
    {
      "type": "fear" | "goal" | "preference" | "constraint" | "pattern",
      "content": "Short, clear insight (max 15 words)",
      "confidence": float (0.0-1.0)
    }
  ],
  "contradiction_score": int (0-100, null if not enough data),
  "current_stage": "EXPLORATION" | "COMPARISON" | "COMMITMENT",
  "behavioral_drift": "Short description of any shift in goals or tone, else null"
}

[RULES]
1. Be conservative. Only update signals if the user's language provides clear evidence.
2. Memories should be high-value. Don't repeat what's already known.
3. Contradiction score reflects tension between intrinsic interest and external pressure.
"""

class IntelligenceService:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.llm = LLMService()

    async def analyze_interaction(self, student_id: str, session_id: str, last_message: str):
        # 1. Get Context
        history = get_conversation_history(self.db, session_id, limit=5)
        profile = get_student_profile(self.db, student_id)
        
        # 2. Build Prompt
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        prompt = f"{INTELLIGENCE_PROMPT}\n\n[CONTEXT]\nProfile: {json.dumps(profile.get('personality_signals', {}))}\n\n[CONVERSATION]\n{history_str}\nuser: {last_message}"
        
        # 3. Call LLM
        try:
            response = await self.llm.completion([{"role": "system", "content": prompt}])
            # Strip markdown code blocks if present
            clean_json = response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:-3].strip()
            elif clean_json.startswith("```"):
                clean_json = clean_json[3:-3].strip()
                
            data = json.loads(clean_json)
            
            # 4. Apply Updates
            self._apply_intelligence(student_id, data)
            return data
        except Exception as e:
            print(f"Intelligence analysis failed: {e}")
            return None

    def _apply_intelligence(self, student_id: str, data: Dict[str, Any]):
        updates = {}
        
        # Update personality signals
        if data.get("personality_signals"):
            current = get_student_profile(self.db, student_id)
            sigs = current.get("personality_signals") or {}
            if isinstance(sigs, str):
                try:
                    sigs = json.loads(sigs)
                except json.JSONDecodeError:
                    sigs = {}
                
            new_sigs = data["personality_signals"]
            for k, v in new_sigs.items():
                if v is not None:
                    # Smoothing: don't jump 100% instantly
                    old_v = sigs.get(k, 50)
                    sigs[k] = int(old_v * 0.7 + v * 0.3)
            
            # Pass dict, NOT json string, because update_student_profile will json.dumps it
            updates["personality_signals"] = sigs

        # Update stage and contradiction
        if data.get("current_stage"):
            updates["conversation_stage"] = data["current_stage"]
        if data.get("contradiction_score") is not None:
            updates["contradiction_score"] = data["contradiction_score"]

        if updates:
            update_student_profile(self.db, student_id, updates)

        # Save memories
        for mem in data.get("memories", []):
            if mem.get("confidence", 0) > 0.6:
                save_memory(
                    self.db, 
                    student_id, 
                    mem["type"], 
                    mem["content"], 
                    mem["confidence"]
                )
                
        # Force commit to ensure background tasks persist
        try:
            self.db.commit()
        except Exception as e:
            print(f"Error committing intelligence to DB: {e}")
