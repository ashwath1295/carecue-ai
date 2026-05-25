# CareCue AI

CareCue AI is a polished hackathon MVP for parents of children aged 0-5. It tracks wake time, sleep, naps, food, activities, screen time, mood, notes, potty/diaper, and medicine, then uses child-specific history to explain mood changes and recommend the next best action.

## Differentiator

CareCue AI is not another baby tracker. Existing apps help parents log sleep, food, and diapers. CareCue AI builds a personalized care memory for each child and uses it to explain mood changes, predict crankiness, and recommend the next best action.

## Tech Stack

- Python
- NiceGUI for the frontend
- SQLite for local storage
- Google Gemini API via `google-generativeai`
- Mock AI fallback when no Gemini key is configured

## Setup

```bash
cd carecue-ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Open the local URL shown in the terminal, usually `http://127.0.0.1:8080`.

## Deploy on Render

1. Push this repo to GitHub.
2. Go to https://render.com and sign in with GitHub.
3. Click **New +** and choose **Blueprint**.
4. Select this repository.
5. Render will read `render.yaml`.
6. Add the secret environment variable when prompted:

```bash
GOOGLE_API_KEY=your_google_gemini_api_key_here
```

Render will automatically run:

```bash
pip install -r requirements.txt
python main.py
```

The app binds to Render's `PORT` automatically.

## Gemini API Key

1. Go to Google AI Studio: https://aistudio.google.com/
2. Create an API key.
3. Add it to `.env`:

```bash
GOOGLE_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```

The app still works without a key by returning useful demo responses.

## Demo Flow

1. Start the app with `python main.py`.
2. Click **Load Demo Data**.
3. Review Aarav's dashboard with meal, nap, mood, awake duration, and timeline cards.
4. Open **Ask AI** and ask: `Why is he cranky now?`
5. Leave feedback such as `Actually tired`.
6. Open **Patterns** and click **Update Child Patterns**.
7. Generate a **Daily Summary** for a babysitter handoff.
8. Try **Natural Language** with: `He woke up at 7, ate banana at 8, played outside, skipped nap, and now he is cranky.`

## Main Features

- Child profile with routine, triggers, comfort actions, food preferences, and notes
- Quick event logging across wake, food, nap, sleep, activity, screen time, mood, potty/diaper, medicine, and notes
- Modern card-based dashboard with today's timeline
- Gemini-powered mood analysis using profile, logs, history, patterns, and parent question
- Parent feedback loop saved into SQLite
- Personalized child memory with generated routine patterns
- Daily summary for parent recap and caregiver handoff
- Natural language log parser with confirmation before saving
- Safe medical boundary: CareCue does not diagnose and recommends pediatrician or emergency care for red flags

## Hackathon Pitch

CareCue AI is not another baby tracker. Existing apps help parents log sleep, food, and diapers. CareCue AI builds a personalized care memory for each child and uses it to explain mood changes, predict crankiness, and recommend the next best action.

Parents do not just need a timeline. They need help answering the anxious, everyday question: "What does my child need right now?" CareCue turns routine logs and parent feedback into child-specific context, then gives calm, practical guidance that gets better over time.
