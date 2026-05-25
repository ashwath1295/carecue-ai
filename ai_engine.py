from __future__ import annotations

import json
import os
import re
import warnings
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai
except ImportError:  # pragma: no cover - handled at runtime for easy demos
    genai = None


MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")


RED_FLAGS = [
    "fever",
    "vomit",
    "vomiting",
    "breathing trouble",
    "trouble breathing",
    "rash",
    "injury",
    "severe crying",
    "dehydration",
    "unusual behavior",
    "lethargic",
    "blue lips",
    "seizure",
]


def _model():
    if not GOOGLE_API_KEY or genai is None:
        return None
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel(MODEL_NAME)


def _format_block(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


def _call_gemini(prompt: str, fallback: str) -> str:
    model = _model()
    if not model:
        return fallback
    try:
        response = model.generate_content(prompt)
        return getattr(response, "text", None) or fallback
    except Exception as exc:
        return f"{fallback}\n\nAI note: Gemini was unavailable, so CareCue used a local demo response. ({exc})"


def _has_red_flags(text: str) -> bool:
    lowered = text.lower()
    return any(flag in lowered for flag in RED_FLAGS)


def analyze_mood(
    child_profile: dict[str, Any],
    today_logs: list[dict[str, Any]],
    recent_logs: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
    question: str,
) -> str:
    safety_line = (
        "Safety note: This is not medical advice. If fever, vomiting, breathing trouble, rash, injury, "
        "severe crying, dehydration, or unusual behavior is present, contact a pediatrician or emergency care."
    )
    red_flag_line = (
        "\n\nImportant: Your question mentions possible medical red flags. Please contact a pediatrician "
        "or emergency care as appropriate, especially if symptoms are severe or worsening."
        if _has_red_flags(question)
        else ""
    )
    fallback = f"""1. Likely reason
A likely explanation is tiredness or overstimulation, especially if the nap window was missed or the awake stretch is long.

2. Evidence from today
CareCue sees today's logs and will weigh recent wake, food, nap, activity, screen time, and mood entries. Add more logs for a sharper read.

3. Evidence from child history
Known patterns and feedback suggest this child may respond well to familiar comfort actions and a calmer routine.

4. Suggested next action
Try a low-stimulation reset: offer water or milk if appropriate, dim the room, reduce noise/screens, and start a short comfort routine.

5. Confidence level
Medium for a hackathon demo response; connect Gemini for deeper personalized reasoning.

6. {safety_line}{red_flag_line}"""

    prompt = f"""You are CareCue AI, a toddler care assistant for parents of children aged 0-5.
You are not a doctor and must not provide medical diagnosis.

Child profile:
{_format_block(child_profile)}

Today's logs:
{_format_block(today_logs)}

Recent child history:
{_format_block(recent_logs)}

Known child patterns:
{_format_block(patterns)}

Parent question:
{question}

Give a parent-friendly response with:
1. Likely reason
2. Evidence from today
3. Evidence from child history
4. Suggested next action
5. Confidence level
6. Safety note

Be specific to this child. Do not give generic advice unless needed.
If there are medical red flags, recommend contacting a pediatrician or emergency care."""
    return _call_gemini(prompt, fallback)


def generate_daily_summary(
    child_profile: dict[str, Any],
    today_logs: list[dict[str, Any]],
    recent_logs: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
) -> str:
    fallback = """Short parent summary
Today included a normal wake, meals, active play, a missed or difficult nap window, and later crankiness that improved with comfort.

Caregiver handoff
Keep the next routine calm and predictable. Offer a familiar snack or milk if appropriate, keep lights and noise low, and use story time for regulation.

Mood pattern for the day
Mood appears more sensitive after the nap window and improves with quiet connection.

Suggested evening routine
Early dinner, bath or quiet play, story time, dim lights, and bedtime close to the usual schedule.

Safety note
This is not medical advice. Contact a pediatrician for concerning symptoms or unusual behavior."""
    prompt = f"""You are CareCue AI. Create a daily toddler care summary.
Do not diagnose medical conditions.

Child profile:
{_format_block(child_profile)}

Today's logs:
{_format_block(today_logs)}

Recent child history:
{_format_block(recent_logs)}

Known child patterns:
{_format_block(patterns)}

Return sections:
- Short parent summary
- Caregiver/babysitter handoff summary
- Mood pattern for the day
- Suggested evening routine
- Safety note"""
    return _call_gemini(prompt, fallback)


def update_child_patterns(
    child_profile: dict[str, Any],
    recent_logs: list[dict[str, Any]],
    feedback: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fallback = [
        {
            "pattern_type": "sleep",
            "pattern_summary": "Gets cranky when the nap is skipped or the awake stretch runs long.",
            "confidence": "medium",
        },
        {
            "pattern_type": "comfort",
            "pattern_summary": "Calms down with milk, story time, and a quiet environment.",
            "confidence": "medium",
        },
        {
            "pattern_type": "activity",
            "pattern_summary": "Outdoor play appears to support a better morning mood.",
            "confidence": "early signal",
        },
    ]
    prompt = f"""You are CareCue AI. Infer personalized toddler routine patterns from logs and parent feedback.
Return only valid JSON as an array. Each item must have:
pattern_type, pattern_summary, confidence.

Child profile:
{_format_block(child_profile)}

Recent logs:
{_format_block(recent_logs)}

Parent feedback:
{_format_block(feedback)}

Do not diagnose medical conditions. Keep patterns practical and parent-friendly."""
    text = _call_gemini(prompt, json.dumps(fallback))
    parsed = _safe_json(text)
    if isinstance(parsed, list):
        cleaned = []
        for item in parsed[:8]:
            if isinstance(item, dict) and item.get("pattern_summary"):
                cleaned.append(
                    {
                        "pattern_type": str(item.get("pattern_type", "routine")),
                        "pattern_summary": str(item.get("pattern_summary", "")),
                        "confidence": str(item.get("confidence", "medium")),
                    }
                )
        if cleaned:
            return cleaned
    return fallback


def parse_natural_language_log(sentence: str) -> list[dict[str, Any]]:
    prompt = f"""Convert this parent sentence into a JSON array of events.
Allowed event types:
wake, food, nap, sleep, activity, screen_time, mood, diaper_potty, medicine, note.

Each event should include:
event_type, event_time, details, mood, intensity.
Use today's date if a date is missing. Use ISO-like local datetime when possible.
Return only valid JSON.

Sentence:
{sentence}"""
    fallback = _mock_parse(sentence)
    text = _call_gemini(prompt, json.dumps(fallback))
    parsed = _safe_json(text)
    if not isinstance(parsed, list):
        return fallback
    return [_normalize_event(item) for item in parsed if isinstance(item, dict)]


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except Exception:
            return None


def _normalize_event(item: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "wake",
        "food",
        "nap",
        "sleep",
        "activity",
        "screen_time",
        "mood",
        "diaper_potty",
        "medicine",
        "note",
    }
    event_type = str(item.get("event_type", "note")).lower()
    if event_type not in allowed:
        event_type = "note"
    return {
        "event_type": event_type,
        "event_time": str(item.get("event_time") or datetime.now().isoformat(timespec="seconds")),
        "details": str(item.get("details", "")),
        "mood": str(item.get("mood", "")),
        "intensity": item.get("intensity"),
    }


def _mock_parse(sentence: str) -> list[dict[str, Any]]:
    today = datetime.now().date().isoformat()
    lowered = sentence.lower()
    events: list[dict[str, Any]] = []
    hints = [
        ("woke", "wake", "Woke up"),
        ("ate", "food", "Ate food"),
        ("banana", "food", "Ate banana"),
        ("milk", "food", "Had milk"),
        ("played", "activity", "Played"),
        ("outside", "activity", "Outdoor play"),
        ("skipped nap", "nap", "Skipped nap"),
        ("nap", "nap", "Nap"),
        ("screen", "screen_time", "Screen time"),
        ("cranky", "mood", "Cranky mood"),
        ("tired", "mood", "Tired mood"),
    ]
    for keyword, event_type, details in hints:
        if keyword in lowered and not any(event["details"] == details for event in events):
            events.append(
                {
                    "event_type": event_type,
                    "event_time": f"{today}T{_extract_time_near(sentence, keyword)}:00",
                    "details": details,
                    "mood": "cranky" if keyword == "cranky" else "",
                    "intensity": 4 if keyword == "cranky" else None,
                }
            )
    return events or [
        {
            "event_type": "note",
            "event_time": datetime.now().isoformat(timespec="seconds"),
            "details": sentence,
            "mood": "",
            "intensity": None,
        }
    ]


def _extract_time_near(sentence: str, keyword: str) -> str:
    match = re.search(rf"{keyword}[^0-9]*(\d{{1,2}})(?::(\d{{2}}))?", sentence, re.IGNORECASE)
    if not match:
        return datetime.now().strftime("%H:%M")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if 1 <= hour <= 6:
        hour += 12
    return f"{hour:02d}:{minute:02d}"
