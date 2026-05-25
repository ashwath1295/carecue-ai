from __future__ import annotations

from datetime import datetime, date
from typing import Any

from nicegui import ui

import ai_engine
import database as db


EVENT_TYPES = [
    ("wake", "Wake", "☀️"),
    ("food", "Food", "🍌"),
    ("nap", "Nap", "😴"),
    ("sleep", "Sleep", "🌙"),
    ("activity", "Activity", "🧸"),
    ("screen_time", "Screen Time", "📱"),
    ("mood", "Mood", "😊"),
    ("diaper_potty", "Diaper / Potty", "🧻"),
    ("medicine", "Medicine", "💊"),
    ("note", "Note", "📝"),
]

EVENT_LABELS = {key: label for key, label, _ in EVENT_TYPES}
EVENT_EMOJIS = {key: emoji for key, _, emoji in EVENT_TYPES}

state: dict[str, Any] = {
    "page": "Dashboard",
    "selected_child_id": None,
    "last_question_id": None,
    "ai_answer": "",
    "daily_summary": "",
    "parsed_events": [],
}


def setup() -> None:
    db.create_tables()
    children = db.get_children()
    if children:
        state["selected_child_id"] = children[0]["id"]


def selected_child() -> dict[str, Any] | None:
    return db.get_child(state.get("selected_child_id"))


def nice_time(value: str | None) -> str:
    if not value:
        return "Not logged yet"
    try:
        return datetime.fromisoformat(value).strftime("%-I:%M %p")
    except ValueError:
        return value


def nice_date_time(value: str | None) -> str:
    if not value:
        return "Now"
    try:
        return datetime.fromisoformat(value).strftime("%b %-d, %-I:%M %p")
    except ValueError:
        return value


def dashboard_summary(child_id: int) -> dict[str, Any]:
    last_meal = db.get_latest_meal(child_id)
    last_nap = db.get_latest_nap(child_id)
    last_mood = db.get_latest_mood(child_id)
    last_wake = db.get_last_wake(child_id)
    today_logs = db.get_today_logs(child_id)
    awake_duration = "Add wake time"
    if last_wake:
        try:
            wake_dt = datetime.fromisoformat(last_wake["event_time"])
            delta = datetime.now() - wake_dt
            if delta.total_seconds() >= 0:
                hours = int(delta.total_seconds() // 3600)
                minutes = int((delta.total_seconds() % 3600) // 60)
                awake_duration = f"{hours}h {minutes}m"
        except ValueError:
            pass
    return {
        "last_meal": last_meal,
        "last_nap": last_nap,
        "last_mood": last_mood,
        "last_wake": last_wake,
        "today_logs": today_logs,
        "awake_duration": awake_duration,
    }


def event_datetime_from_input(value: str | None) -> str:
    if not value:
        return datetime.now().isoformat(timespec="seconds")
    try:
        return datetime.fromisoformat(value).isoformat(timespec="seconds")
    except ValueError:
        return datetime.now().isoformat(timespec="seconds")


def require_child() -> dict[str, Any] | None:
    child = selected_child()
    if not child:
        ui.notify("Create or load a child profile first.", type="warning")
        state["page"] = "Child Profile"
        render_page.refresh()
    return child


def load_demo() -> None:
    child_id = db.load_demo_data()
    state["selected_child_id"] = child_id
    state["page"] = "Dashboard"
    state["ai_answer"] = ""
    state["daily_summary"] = ""
    state["parsed_events"] = []
    ui.notify("Demo data loaded for Aarav.", type="positive")
    render_shell.refresh()


def quick_add_event(event_type: str, details: str = "") -> None:
    child = require_child()
    if not child:
        return
    db.add_event(child["id"], event_type, datetime.now().isoformat(timespec="seconds"), details)
    ui.notify(f"{EVENT_LABELS[event_type]} logged.", type="positive")
    render_page.refresh()


def stat_card(title: str, value: str, subtitle: str, icon: str) -> None:
    with ui.card().classes("stat-card"):
        ui.label(icon).classes("stat-icon")
        ui.label(title).classes("stat-title")
        ui.label(value).classes("stat-value")
        ui.label(subtitle).classes("stat-subtitle")


def timeline(logs: list[dict[str, Any]]) -> None:
    if not logs:
        ui.label("No events yet today. Add a quick log to start the care memory.").classes("muted")
        return
    for event in logs:
        with ui.row().classes("timeline-row"):
            ui.label(EVENT_EMOJIS.get(event["event_type"], "•")).classes("timeline-emoji")
            with ui.column().classes("gap-0"):
                ui.label(f"{EVENT_LABELS.get(event['event_type'], event['event_type'])} · {nice_time(event['event_time'])}").classes("timeline-title")
                detail = event.get("details") or event.get("mood") or "Logged"
                ui.label(detail).classes("timeline-detail")


def render_dashboard() -> None:
    child = selected_child()
    if not child:
        with ui.column().classes("empty-state"):
            ui.label("CareCue AI").classes("empty-title")
            ui.label("Start by creating a child profile or load the polished demo data.").classes("muted")
            ui.button("Load Demo Data", on_click=load_demo).classes("primary-btn")
        return

    summary = dashboard_summary(child["id"])
    with ui.row().classes("section-head"):
        with ui.column().classes("gap-1"):
            ui.label(f"{child['name']}, age {child['age']}").classes("page-title")
            ui.label("A personalized care memory for today’s tiny signals.").classes("muted")
        ui.button("Load Demo Data", on_click=load_demo).classes("secondary-btn")

    with ui.grid(columns=4).classes("dashboard-grid"):
        stat_card("Last meal", nice_time(summary["last_meal"]["event_time"]) if summary["last_meal"] else "Not yet", summary["last_meal"]["details"] if summary["last_meal"] else "Food logs appear here", "🍽️")
        stat_card("Last nap", nice_time(summary["last_nap"]["event_time"]) if summary["last_nap"] else "Not yet", summary["last_nap"]["details"] if summary["last_nap"] else "Nap and sleep clues", "😴")
        stat_card("Last mood", summary["last_mood"]["mood"] or summary["last_mood"]["details"] if summary["last_mood"] else "Not yet", nice_time(summary["last_mood"]["event_time"]) if summary["last_mood"] else "Mood trend", "💛")
        stat_card("Awake duration", summary["awake_duration"], f"{len(summary['today_logs'])} events today", "⏱️")

    with ui.card().classes("panel"):
        ui.label("Quick actions").classes("section-title")
        with ui.row().classes("quick-grid"):
            for event_type, label, emoji in EVENT_TYPES[:8]:
                ui.button(f"{emoji} {label}", on_click=lambda et=event_type: quick_add_event(et)).classes("quick-btn")

    with ui.card().classes("panel"):
        ui.label("Today’s timeline").classes("section-title")
        timeline(summary["today_logs"])


def render_child_profile() -> None:
    children = db.get_children()
    options = {child["id"]: f"{child['name']} · age {child['age']}" for child in children}

    with ui.row().classes("section-head"):
        with ui.column().classes("gap-1"):
            ui.label("Child Profile").classes("page-title")
            ui.label("The profile gives CareCue context before it reasons about mood and routine.").classes("muted")
        ui.button("Load Demo Data", on_click=load_demo).classes("secondary-btn")

    if options:
        ui.select(
            options,
            label="Selected child",
            value=state.get("selected_child_id"),
            on_change=lambda e: (state.update(selected_child_id=e.value), render_shell.refresh()),
        ).classes("wide-field")

    child = selected_child() or {}
    with ui.card().classes("panel form-panel"):
        ui.label("Profile details").classes("section-title")
        name = ui.input("Name", value=child.get("name", "")).classes("wide-field")
        age = ui.input("Age", value=child.get("age", "")).classes("wide-field")
        with ui.row().classes("form-row"):
            wake = ui.input("Usual wake time", value=child.get("usual_wake_time", "")).classes("form-field")
            nap = ui.input("Usual nap time", value=child.get("usual_nap_time", "")).classes("form-field")
            bedtime = ui.input("Usual bedtime", value=child.get("usual_bedtime", "")).classes("form-field")
        triggers = ui.textarea("Known triggers", value=child.get("known_triggers", "")).classes("wide-field")
        comforts = ui.textarea("Comfort actions", value=child.get("comfort_actions", "")).classes("wide-field")
        foods = ui.textarea("Food preferences", value=child.get("food_preferences", "")).classes("wide-field")
        notes = ui.textarea("General notes", value=child.get("notes", "")).classes("wide-field")

        def save_profile() -> None:
            if not name.value.strip() or not age.value.strip():
                ui.notify("Name and age are required.", type="warning")
                return
            payload = {
                "name": name.value,
                "age": age.value,
                "usual_wake_time": wake.value,
                "usual_nap_time": nap.value,
                "usual_bedtime": bedtime.value,
                "known_triggers": triggers.value,
                "comfort_actions": comforts.value,
                "food_preferences": foods.value,
                "notes": notes.value,
            }
            if child.get("id"):
                db.update_child(child["id"], payload)
                state["selected_child_id"] = child["id"]
            else:
                state["selected_child_id"] = db.create_child(payload)
            ui.notify("Profile saved.", type="positive")
            render_shell.refresh()

        ui.button("Save Profile", on_click=save_profile).classes("primary-btn")


def render_quick_log() -> None:
    child = require_child()
    if not child:
        return
    ui.label("Quick Log").classes("page-title")
    ui.label(f"Add care events for {child['name']} as they happen, or backfill the day for a better AI read.").classes("muted")

    with ui.card().classes("panel form-panel"):
        event_type = ui.select({key: f"{emoji} {label}" for key, label, emoji in EVENT_TYPES}, label="Event type", value="mood").classes("wide-field")
        event_time = ui.input("Event time", value=datetime.now().strftime("%Y-%m-%dT%H:%M")).props("type=datetime-local").classes("wide-field")
        details = ui.textarea("Details", placeholder="e.g., Ate yogurt, skipped nap, cranky after screen time").classes("wide-field")
        with ui.row().classes("form-row"):
            mood = ui.input("Mood (optional)", placeholder="cranky, calm, cheerful").classes("form-field")
            intensity = ui.number("Intensity 1-5", min=1, max=5, step=1, value=None).classes("form-field")

        def save_event() -> None:
            db.add_event(
                child["id"],
                event_type.value,
                event_datetime_from_input(event_time.value),
                details.value or "",
                mood.value or "",
                int(intensity.value) if intensity.value else None,
            )
            ui.notify("Event saved.", type="positive")
            state["page"] = "Dashboard"
            render_shell.refresh()

        ui.button("Save Event", on_click=save_event).classes("primary-btn")

    with ui.card().classes("panel"):
        ui.label("Fast tap buttons").classes("section-title")
        with ui.row().classes("quick-grid"):
            for key, label, emoji in EVENT_TYPES:
                ui.button(f"{emoji} {label}", on_click=lambda et=key: quick_add_event(et)).classes("quick-btn")


def render_ask_ai() -> None:
    child = require_child()
    if not child:
        return
    ui.label("Ask CareCue AI").classes("page-title")
    ui.label("CareCue combines profile, today’s logs, recent history, patterns, and feedback before answering.").classes("muted")

    with ui.card().classes("panel form-panel"):
        question = ui.textarea("Parent question", value="Why is he cranky now?").classes("wide-field")

        def ask() -> None:
            answer = ai_engine.analyze_mood(
                child,
                db.get_today_logs(child["id"]),
                db.get_recent_logs(child["id"]),
                db.get_patterns(child["id"]),
                question.value,
            )
            state["ai_answer"] = answer
            state["last_question_id"] = db.save_ai_question(child["id"], question.value, answer)
            render_page.refresh()

        ui.button("Ask CareCue AI", on_click=ask).classes("primary-btn")

    if state.get("ai_answer"):
        with ui.card().classes("answer-panel"):
            ui.markdown(state["ai_answer"]).classes("answer-text")
            ui.label("Was CareCue right?").classes("section-title")
            with ui.row().classes("feedback-row"):
                for feedback in [
                    "Correct",
                    "Somewhat correct",
                    "Not correct",
                    "Actually hungry",
                    "Actually tired",
                    "Actually overstimulated",
                    "Needed attention",
                    "Other",
                ]:
                    ui.button(feedback, on_click=lambda fb=feedback: save_ai_feedback(fb)).classes("feedback-btn")


def save_ai_feedback(feedback: str) -> None:
    child = selected_child()
    question_id = state.get("last_question_id")
    if not child or not question_id:
        ui.notify("Ask CareCue first, then leave feedback.", type="warning")
        return
    db.save_feedback(question_id, child["id"], feedback)
    ui.notify("Feedback saved into this child’s memory.", type="positive")


def render_daily_summary() -> None:
    child = require_child()
    if not child:
        return
    ui.label("Daily Summary").classes("page-title")
    ui.label("Generate a parent recap, babysitter handoff, mood pattern, and evening routine.").classes("muted")

    def generate() -> None:
        state["daily_summary"] = ai_engine.generate_daily_summary(
            child,
            db.get_today_logs(child["id"]),
            db.get_recent_logs(child["id"]),
            db.get_patterns(child["id"]),
        )
        render_page.refresh()

    ui.button("Generate Daily Summary", on_click=generate).classes("primary-btn")
    if state.get("daily_summary"):
        with ui.card().classes("answer-panel"):
            ui.markdown(state["daily_summary"]).classes("answer-text")


def render_patterns() -> None:
    child = require_child()
    if not child:
        return
    ui.label("Personalized Child Memory").classes("page-title")
    ui.label("Patterns are generated from logs and parent feedback, then reused in future AI answers.").classes("muted")

    def update_patterns() -> None:
        patterns = ai_engine.update_child_patterns(child, db.get_recent_logs(child["id"]), db.get_feedback(child["id"]))
        db.replace_patterns(child["id"], patterns)
        ui.notify("Child patterns updated.", type="positive")
        render_page.refresh()

    ui.button("Update Child Patterns", on_click=update_patterns).classes("primary-btn")

    patterns = db.get_patterns(child["id"])
    if not patterns:
        ui.label("No patterns yet. Add logs or load demo data, then update patterns.").classes("muted")
        return
    with ui.grid(columns=3).classes("patterns-grid"):
        for pattern in patterns:
            with ui.card().classes("pattern-card"):
                ui.label(pattern["pattern_type"].title()).classes("pattern-type")
                ui.label(pattern["pattern_summary"]).classes("pattern-summary")
                ui.label(f"Confidence: {pattern.get('confidence') or 'medium'}").classes("pattern-confidence")


def render_parser() -> None:
    child = require_child()
    if not child:
        return
    ui.label("Natural Language Log Parser").classes("page-title")
    ui.label("Type what happened naturally, review the events, then save them into the timeline.").classes("muted")

    with ui.card().classes("panel form-panel"):
        sentence = ui.textarea(
            "Parent sentence",
            value="He woke up at 7, ate banana at 8, played outside, skipped nap, and now he is cranky.",
        ).classes("wide-field")

        def parse() -> None:
            state["parsed_events"] = ai_engine.parse_natural_language_log(sentence.value)
            render_page.refresh()

        ui.button("Parse Sentence", on_click=parse).classes("primary-btn")

    if state.get("parsed_events"):
        with ui.card().classes("panel"):
            ui.label("Review parsed events").classes("section-title")
            for event in state["parsed_events"]:
                ui.label(
                    f"{EVENT_EMOJIS.get(event['event_type'], '•')} "
                    f"{EVENT_LABELS.get(event['event_type'], event['event_type'])} · "
                    f"{nice_date_time(event.get('event_time'))} · {event.get('details', '')}"
                ).classes("review-line")

            def save_parsed() -> None:
                for event in state["parsed_events"]:
                    db.add_event(
                        child["id"],
                        event["event_type"],
                        event_datetime_from_input(event.get("event_time")),
                        event.get("details", ""),
                        event.get("mood", ""),
                        int(event["intensity"]) if event.get("intensity") else None,
                    )
                state["parsed_events"] = []
                ui.notify("Parsed events saved.", type="positive")
                state["page"] = "Dashboard"
                render_shell.refresh()

            ui.button("Save Parsed Events", on_click=save_parsed).classes("primary-btn")


@ui.refreshable
def render_page() -> None:
    with ui.column().classes("content"):
        page = state["page"]
        if page == "Dashboard":
            render_dashboard()
        elif page == "Child Profile":
            render_child_profile()
        elif page == "Quick Log":
            render_quick_log()
        elif page == "Ask AI":
            render_ask_ai()
        elif page == "Daily Summary":
            render_daily_summary()
        elif page == "Patterns":
            render_patterns()
        elif page == "Natural Language":
            render_parser()


@ui.refreshable
def render_shell() -> None:
    ui.query("body").classes("carecue-body")
    ui.add_head_html(
        """
        <style>
        :root {
            --cream: #fffaf3;
            --paper: #ffffff;
            --ink: #24302f;
            --muted: #6e7c78;
            --sage: #4f7b68;
            --mint: #dff2e9;
            --coral: #ee7f6f;
            --sun: #f7c95f;
            --line: #e9e0d4;
        }
        .carecue-body { background: var(--cream); color: var(--ink); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .q-page { min-height: 100vh; }
        .shell { display: grid; grid-template-columns: 260px minmax(0, 1fr); min-height: 100vh; width: 100%; }
        .sidebar { background: #314c43; color: white; padding: 24px 18px; gap: 18px; }
        .brand { font-size: 28px; font-weight: 800; letter-spacing: 0; }
        .tagline { color: rgba(255,255,255,0.78); line-height: 1.4; }
        .nav-btn { width: 100%; justify-content: flex-start; border-radius: 8px; color: white; background: rgba(255,255,255,0.08); }
        .nav-btn.active { background: var(--sun); color: #24302f; font-weight: 700; }
        .main { min-width: 0; }
        .topbar { height: 72px; background: rgba(255,255,255,0.78); border-bottom: 1px solid var(--line); backdrop-filter: blur(14px); padding: 0 28px; align-items: center; justify-content: space-between; }
        .top-title { font-weight: 800; font-size: 18px; }
        .child-pill { background: var(--mint); color: #27483d; border-radius: 999px; padding: 8px 14px; font-weight: 700; }
        .content { width: 100%; max-width: 1180px; margin: 0 auto; padding: 28px; gap: 20px; }
        .page-title { font-size: 34px; font-weight: 850; letter-spacing: 0; }
        .section-head { width: 100%; justify-content: space-between; align-items: center; gap: 16px; }
        .muted { color: var(--muted); line-height: 1.45; }
        .dashboard-grid, .patterns-grid { width: 100%; gap: 16px; }
        .stat-card, .panel, .answer-panel, .pattern-card { border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 10px 24px rgba(49, 76, 67, 0.08); background: var(--paper); }
        .stat-card { min-height: 168px; padding: 18px; }
        .stat-icon { font-size: 28px; }
        .stat-title, .section-title { color: var(--muted); font-weight: 750; text-transform: uppercase; font-size: 12px; letter-spacing: .08em; }
        .stat-value { font-size: 25px; font-weight: 850; margin-top: 4px; overflow-wrap: anywhere; }
        .stat-subtitle { color: var(--muted); line-height: 1.35; overflow-wrap: anywhere; }
        .panel, .answer-panel { width: 100%; padding: 20px; }
        .form-panel { gap: 14px; }
        .primary-btn { background: var(--sage) !important; color: white !important; border-radius: 8px; font-weight: 750; }
        .secondary-btn { background: var(--mint) !important; color: #27483d !important; border-radius: 8px; font-weight: 750; }
        .quick-grid, .feedback-row { gap: 10px; flex-wrap: wrap; }
        .quick-btn, .feedback-btn { background: #fff7e8 !important; color: #35433f !important; border: 1px solid var(--line); border-radius: 8px; min-height: 42px; }
        .timeline-row { width: 100%; align-items: flex-start; gap: 12px; padding: 12px 0; border-bottom: 1px solid #f1e9de; }
        .timeline-emoji { font-size: 23px; width: 34px; }
        .timeline-title { font-weight: 800; }
        .timeline-detail { color: var(--muted); }
        .wide-field { width: 100%; }
        .form-row { width: 100%; gap: 14px; }
        .form-field { flex: 1; min-width: 220px; }
        .answer-text { line-height: 1.6; }
        .pattern-card { padding: 18px; min-height: 150px; }
        .pattern-type { color: var(--coral); font-weight: 850; }
        .pattern-summary { font-size: 17px; line-height: 1.4; }
        .pattern-confidence, .review-line { color: var(--muted); }
        .empty-state { min-height: 55vh; align-items: center; justify-content: center; text-align: center; gap: 12px; }
        .empty-title { font-size: 48px; font-weight: 900; }
        @media (max-width: 900px) {
            .shell { grid-template-columns: 1fr; }
            .sidebar { position: relative; }
            .dashboard-grid, .patterns-grid { grid-template-columns: 1fr !important; }
            .content { padding: 18px; }
            .page-title { font-size: 28px; }
        }
        </style>
        """
    )

    child = selected_child()
    with ui.element("div").classes("shell"):
        with ui.column().classes("sidebar"):
            ui.label("CareCue AI").classes("brand")
            ui.label("Personalized toddler mood and routine assistant.").classes("tagline")
            for page in ["Dashboard", "Child Profile", "Quick Log", "Ask AI", "Daily Summary", "Patterns", "Natural Language"]:
                button = ui.button(page, on_click=lambda p=page: (state.update(page=p), render_page.refresh()))
                button.classes("nav-btn active" if state["page"] == page else "nav-btn")
            ui.space()
            ui.button("Load Demo Data", on_click=load_demo).classes("secondary-btn")
        with ui.column().classes("main"):
            with ui.row().classes("topbar"):
                ui.label("CareCue AI").classes("top-title")
                ui.label(f"Selected: {child['name']}" if child else "No child selected").classes("child-pill")
            render_page()


setup()
render_shell()

ui.run(title="CareCue AI", reload=False)
