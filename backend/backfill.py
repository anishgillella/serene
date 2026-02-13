"""
Backfill script — seeds calendar data and sample conflicts for Adrian & Elara,
then triggers LLM-powered analysis + repair plan generation for each conflict.

Usage:
    cd backend
    python backfill.py

Requires the backend server to be running at API_BASE (default http://localhost:8000).
"""
import requests
import uuid
import time
import sys

API_BASE = "http://localhost:8000"
RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"

# ── Login as Adrian to get a token (for any auth-protected endpoints) ──────
def get_token():
    r = requests.post(f"{API_BASE}/api/auth/login", json={
        "email": "adrian@serene.app",
        "password": "adrian123",
    })
    if r.status_code != 200:
        print(f"Login failed: {r.text}")
        sys.exit(1)
    return r.json()["token"]


def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
    }


# ── 1. Seed memorable dates ────────────────────────────────────────────────
def seed_memorable_dates():
    print("\n📅 Seeding memorable dates...")
    dates = [
        {
            "title": "Our Anniversary",
            "event_date": "2023-03-15",
            "event_type": "anniversary",
            "description": "The day we officially started dating",
            "is_recurring": True,
            "reminder_days": 7,
            "color_tag": "#f59e0b",
        },
        {
            "title": "Adrian's Birthday",
            "event_date": "1997-08-22",
            "event_type": "birthday",
            "description": "Adrian Malhotra's birthday",
            "is_recurring": True,
            "reminder_days": 14,
            "color_tag": "#3b82f6",
            "partner_id": "partner_a",
        },
        {
            "title": "Elara's Birthday",
            "event_date": "1999-04-10",
            "event_type": "birthday",
            "description": "Elara Voss's birthday",
            "is_recurring": True,
            "reminder_days": 14,
            "color_tag": "#ec4899",
            "partner_id": "partner_b",
        },
        {
            "title": "First Date",
            "event_date": "2023-02-14",
            "event_type": "first_date",
            "description": "Valentine's Day dinner at that Italian place in the West Village",
            "is_recurring": True,
            "reminder_days": 7,
            "color_tag": "#ef4444",
        },
        {
            "title": "Moved In Together",
            "event_date": "2025-01-20",
            "event_type": "milestone",
            "description": "Started living together in Brooklyn",
            "is_recurring": True,
            "reminder_days": 7,
            "color_tag": "#10b981",
        },
    ]
    for d in dates:
        r = requests.post(f"{API_BASE}/api/calendar/memorable-dates", json=d)
        status = "OK" if r.status_code == 200 else f"FAIL ({r.status_code})"
        print(f"  {status}: {d['title']}")


# ── 2. Seed cycle events for Elara ─────────────────────────────────────────
def seed_cycle_events():
    print("\n🩸 Seeding cycle events for Elara...")
    events = [
        {"partner_id": "partner_b", "event_type": "period_start", "event_date": "2025-12-18"},
        {"partner_id": "partner_b", "event_type": "period_end", "event_date": "2025-12-23"},
        {"partner_id": "partner_b", "event_type": "period_start", "event_date": "2026-01-15"},
        {"partner_id": "partner_b", "event_type": "period_end", "event_date": "2026-01-20"},
        {"partner_id": "partner_b", "event_type": "period_start", "event_date": "2026-02-12"},
        {"partner_id": "partner_b", "event_type": "period_end", "event_date": "2026-02-17"},
    ]
    for e in events:
        r = requests.post(f"{API_BASE}/api/calendar/cycle-events", json=e)
        status = "OK" if r.status_code == 200 else f"FAIL ({r.status_code})"
        print(f"  {status}: {e['event_type']} on {e['event_date']}")


# ── 3. Sample conflict transcripts ─────────────────────────────────────────
CONFLICTS = [
    {
        "title": "The Dishes Argument",
        "transcript": [
            "Elara Voss: Adrian, the sink is full again. I asked you to do the dishes before I got home.",
            "Adrian Malhotra: I was going to do them after I finished this work thing. Can you just give me a sec?",
            "Elara Voss: You always say that. 'After this' or 'in a minute.' It never happens.",
            "Adrian Malhotra: That's not fair. I did them two days ago. You're acting like I never help.",
            "Elara Voss: Two days ago! And since then the sink has been piling up. I feel like I'm the only one who notices.",
            "Adrian Malhotra: I notice, I just don't drop everything the second I see a dish. That doesn't mean I don't care.",
            "Elara Voss: But it feels like you don't care. When I come home to a mess, it feels like my comfort doesn't matter to you.",
            "Adrian Malhotra: Your comfort matters. But I also need you to not blow up at me the second you walk through the door. I need a little processing time.",
            "Elara Voss: I'm not blowing up! I'm expressing how I feel. And when you shut down like that, I feel completely alone.",
            "Adrian Malhotra: I'm not shutting down, I'm trying to stay calm so this doesn't escalate.",
            "Elara Voss: See, you're doing it right now. That flat voice. It makes me feel like you don't even care about this conversation.",
            "Adrian Malhotra: I care. I just handle things differently than you. Can we talk about a system instead of attacking each other?",
            "Elara Voss: I'm not attacking you. I just want to feel like we're a team. Like you see the mess and think 'I should handle this' without me having to ask.",
            "Adrian Malhotra: Okay. I hear that. Maybe we can make a schedule or something. I just need you to not come at me heated when I'm in the middle of something.",
            "Elara Voss: Fine. But I need you to actually follow through. Not just agree and forget.",
        ],
    },
    {
        "title": "The Silent Treatment Fight",
        "transcript": [
            "Elara Voss: Can we please talk about what happened at dinner with your friends?",
            "Adrian Malhotra: What about it?",
            "Elara Voss: You barely talked to me the entire time. I was sitting right there and you were just on your phone or talking to Dev.",
            "Adrian Malhotra: I wasn't ignoring you. I just hadn't seen Dev in months. I was catching up.",
            "Elara Voss: For two hours? You didn't look at me once. I felt invisible.",
            "Adrian Malhotra: That's a bit dramatic. You were talking to Priya the whole time too.",
            "Elara Voss: Don't call me dramatic. That's so dismissive. I'm telling you how I felt and you're minimizing it.",
            "Adrian Malhotra: I'm not minimizing. I'm saying you were also engaged in conversation. It's not like you were sitting alone.",
            "Elara Voss: It's not about being alone, it's about feeling connected to YOU. A touch, a look, including me in your conversation. Anything.",
            "Adrian Malhotra: I didn't realize I needed to check in every five minutes. I thought we were both having a good time.",
            "Elara Voss: That's the problem. You didn't realize. Because you don't think about how I'm feeling unless I spell it out.",
            "Adrian Malhotra: That's not true. I think about you all the time. I just don't perform it the way you want me to.",
            "Elara Voss: Perform? Is showing me affection in public a performance to you?",
            "Adrian Malhotra: No, that came out wrong. I mean... I show love differently. And I'm sorry you felt ignored. That wasn't my intention.",
            "Elara Voss: I know it wasn't your intention. But intention and impact are different things. I just want to feel like your priority, even when your friends are around.",
            "Adrian Malhotra: You are my priority. I'll be more aware next time. I mean that.",
        ],
    },
    {
        "title": "Money and Priorities",
        "transcript": [
            "Adrian Malhotra: Elara, did you see the credit card statement? There's a 400 dollar charge from that vintage store.",
            "Elara Voss: Yeah, I found this incredible mid-century lamp and some frames for my studio. They're for work, basically.",
            "Adrian Malhotra: Four hundred dollars on a lamp and frames? We talked about saving for the apartment deposit.",
            "Elara Voss: We are saving. I put money in the savings account last month. This was from my freelance check.",
            "Adrian Malhotra: But it's still our shared finances. We agreed on a budget.",
            "Elara Voss: You agreed on a budget. You made a spreadsheet and told me to follow it. I didn't really get a say.",
            "Adrian Malhotra: That's not what happened. I asked for your input and you said 'whatever you think is fine.'",
            "Elara Voss: Because you'd already decided! You came in with the whole plan laid out. What was I supposed to say?",
            "Adrian Malhotra: You could have said 'I disagree' instead of agreeing and then doing whatever you want anyway.",
            "Elara Voss: I'm not doing 'whatever I want.' I'm investing in my career. That lamp is for client shoots.",
            "Adrian Malhotra: A vintage lamp is an investment now? I'm trying to build a future for us and it feels like I'm the only one taking it seriously.",
            "Elara Voss: That's so unfair. Just because I don't show it with spreadsheets doesn't mean I don't care about our future. I care about living too, not just saving.",
            "Adrian Malhotra: I'm not saying don't live. I'm saying communicate before big purchases. That's all.",
            "Elara Voss: Fine. But then you need to stop treating every purchase I make like it's irresponsible. It makes me feel controlled.",
            "Adrian Malhotra: I don't want to control you. I want us to be on the same page. Let's... can we revisit the budget together? Actually together this time.",
            "Elara Voss: Yes. But I need you to listen to what matters to me too, not just what makes sense on paper.",
        ],
    },
]


# ── 4. Create conflicts + store transcripts + trigger LLM generation ───────
def seed_conflicts(token):
    print("\n💥 Seeding conflicts and triggering LLM analysis...")

    for conflict_data in CONFLICTS:
        title = conflict_data["title"]
        transcript = conflict_data["transcript"]
        print(f"\n  ── {title} ──")

        # Create conflict
        r = requests.post(f"{API_BASE}/api/conflicts/create", headers=headers(token))
        if r.status_code != 200:
            print(f"  FAIL creating conflict: {r.text}")
            continue
        conflict_id = r.json()["conflict_id"]
        print(f"  Created conflict: {conflict_id}")

        # Store transcript (this also triggers background title generation)
        r = requests.post(
            f"{API_BASE}/api/post-fight/conflicts/{conflict_id}/store-transcript",
            json={
                "transcript": transcript,
                "relationship_id": RELATIONSHIP_ID,
                "partner_a_id": "partner_a",
                "partner_b_id": "partner_b",
                "duration": 300.0,
                "speaker_labels": {"0": "Adrian Malhotra", "1": "Elara Voss"},
            },
            headers=headers(token),
        )
        if r.status_code != 200:
            print(f"  FAIL storing transcript: {r.text}")
            continue
        print(f"  Stored transcript ({len(transcript)} lines)")

        # Wait a moment for the background title generation to kick off
        time.sleep(1)

        # Trigger analysis + repair plans (this calls LLM for analysis + 2 repair plans in parallel)
        print(f"  Generating analysis + repair plans via LLM...")
        r = requests.post(
            f"{API_BASE}/api/post-fight/conflicts/{conflict_id}/generate-all",
            json={
                "relationship_id": RELATIONSHIP_ID,
                "partner_a_id": "partner_a",
                "partner_b_id": "partner_b",
            },
            headers=headers(token),
            timeout=120,
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  Analysis: {data.get('analysis', {}).get('fight_summary', 'generated')[:80]}...")
            print(f"  Boyfriend repair plan: {len(data.get('repair_plan_boyfriend', {}).get('steps', []))} steps")
            print(f"  Girlfriend repair plan: {len(data.get('repair_plan_girlfriend', {}).get('steps', []))} steps")
        else:
            print(f"  LLM generation status: {r.status_code} (may be running in background)")


# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌿 Serene Backfill Script")
    print("=" * 50)

    # Check server is up
    try:
        r = requests.get(f"{API_BASE}/", timeout=5)
        print(f"Server: {r.json().get('message', 'OK')}")
    except Exception as e:
        print(f"Cannot reach server at {API_BASE}: {e}")
        print("Make sure the backend is running first.")
        sys.exit(1)

    token = get_token()
    print(f"Authenticated as Adrian")

    seed_memorable_dates()
    seed_cycle_events()
    seed_conflicts(token)

    print("\n" + "=" * 50)
    print("✅ Backfill complete!")
    print("   - 5 memorable dates seeded")
    print("   - 6 cycle events seeded (3 periods for Elara)")
    print(f"   - {len(CONFLICTS)} conflicts created with LLM analysis + repair plans")
    print("\nLogin as Adrian (adrian@serene.app / adrian123) or Elara (elara@serene.app / ellara123) to see everything.")
