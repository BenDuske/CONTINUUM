#!/usr/bin/env python3
"""Load sample production data for THE LAST SIGNAL into ClickHouse.

Creates a realistic demo dataset that demonstrates CONTINUUM's agent pipeline:
- 47 scenes with characters, props, locations, and dependencies
- Shot lists with planned coverage
- Takes with ratings and metadata
- Props with states that create the demo continuity conflict
- Production events showing the timeline

Usage:
    python scripts/load_sample_data.py
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import clickhouse_connect
from continuum.config import config

PRODUCTION_ID = "tls-001"


def generate_uuid() -> str:
    return str(uuid.uuid4())[:12]


def main():
    print(f"Loading sample data for THE LAST SIGNAL into ClickHouse...")

    client = clickhouse_connect.get_client(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        username=config.clickhouse.user,
        password=config.clickhouse.password,
        secure=config.clickhouse.secure,
        database=config.clickhouse.database,
    )

    # Load production definition
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_production" / "the_last_signal.json"
    production = json.loads(data_path.read_text())

    # --- Scenes ---
    print("  Loading scenes...")
    scenes_data = [
        # Key scenes for the demo scenario
        ("scene-31", 31, "EXT. RADIO OBSERVATORY — DISH ARRAY — NIGHT",
         "EXT", "Radio Observatory — Dish Array", "NIGHT",
         "Sarah rushes to the array during the first signal event. In her panic she drops Camera P-14, cracking the lens and denting the body. The damaged camera becomes a recurring visual motif.",
         ["Sarah Chen"], ["Camera P-14", "Observatory Headphones", "Signal Notebook"],
         [], ["scene-28", "scene-29"]),

        ("scene-37", 37, "INT. SARAH'S APARTMENT — NIGHT",
         "INT", "Sarah's Apartment", "NIGHT",
         "Sarah reviews the signal data at home. The damaged camera sits on the counter — a reminder of the event.",
         ["Sarah Chen"], ["Camera P-14", "Signal Notebook"],
         [], ["scene-31", "scene-35"]),

        ("scene-42", 42, "INT. SARAH'S APARTMENT — NIGHT",
         "INT", "Sarah's Apartment", "NIGHT",
         "Sarah enters carrying the damaged camera. Her red jacket is soaked from the rain. She begins decoding the final segment of the signal.",
         ["Sarah Chen"], ["Camera P-14"],
         ["Red jacket — wet"], ["scene-37", "scene-41"]),

        ("scene-47", 47, "INT. RADIO OBSERVATORY — CONTROL ROOM — NIGHT",
         "INT", "Radio Observatory — Control Room", "NIGHT",
         "Sarah presents her decoded findings to Elena and David. The damaged camera photos are projected on screen as evidence.",
         ["Sarah Chen", "David Okafor", "Elena Vasquez"], ["Camera P-14", "Signal Notebook"],
         [], ["scene-42", "scene-45"]),
    ]

    # Add some additional scenes to flesh out the production
    for i in range(1, 48):
        scene_id = f"scene-{i}"
        if scene_id in [s[0] for s in scenes_data]:
            continue
        scenes_data.append((
            scene_id, i,
            f"Scene {i} placeholder",
            "INT" if i % 3 != 0 else "EXT",
            production["locations"][i % len(production["locations"])]["name"],
            "DAY" if i % 2 == 0 else "NIGHT",
            f"Scene {i} of THE LAST SIGNAL.",
            ["Sarah Chen"] if i % 2 == 0 else ["Sarah Chen", "David Okafor"],
            [], [], [],
        ))

    client.insert(
        "scenes",
        data=[
            [s[0], PRODUCTION_ID, s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10],
             1, "white", 1 if s[1] <= 35 else 0, 1 if s[1] <= 29 else 0,
             datetime.now()]
            for s in scenes_data
        ],
        column_names=[
            "scene_id", "production_id", "scene_number", "slug", "int_ext",
            "location_name", "time_of_day", "description", "characters", "props",
            "wardrobe_notes", "story_dependencies",
            "revision", "revision_color", "filmed", "wrapped", "updated_at",
        ],
    )
    print(f"  ✓ {len(scenes_data)} scenes loaded")

    # --- Props ---
    print("  Loading props...")
    props_data = [
        ("prop-camera", "Camera P-14", "damaged",
         ["scene-31", "scene-37", "scene-42", "scene-47"],
         "Sarah's personal camera. Dropped during first signal event (Scene 31). Cracked lens, dented body. Damage is visible and narratively important."),
        ("prop-notebook", "Signal Notebook", "intact",
         ["scene-31", "scene-37", "scene-42", "scene-47"],
         "Hand-written analysis notebook. Entries accumulate."),
        ("prop-headphones", "Observatory Headphones", "intact",
         ["scene-31"],
         "Vintage monitoring headphones."),
        ("prop-badge", "Security Badge", "active",
         ["scene-31", "scene-37", "scene-38"],
         "Facility access badge. Revoked in Scene 38."),
    ]

    client.insert(
        "props",
        data=[
            [p[0], PRODUCTION_ID, p[1], p[2], p[3], p[4], datetime.now()]
            for p in props_data
        ],
        column_names=[
            "prop_id", "production_id", "name", "state", "scenes", "notes", "updated_at",
        ],
    )
    print(f"  ✓ {len(props_data)} props loaded")

    # --- Shots for Scene 42 (the demo scene) ---
    print("  Loading shots for Scene 42...")
    shots_42 = [
        ("shot-42a", "42A", "Master wide — Sarah enters apartment", "WS", False),
        ("shot-42b", "42B", "Medium — Sarah sets camera on counter", "MS", False),
        ("shot-42c", "42C", "Close-up — damaged camera on counter", "CU", False),
        ("shot-42d", "42D", "Medium — Sarah removes wet jacket", "MS", False),
        ("shot-42e", "42E", "Over-shoulder — Sarah opens laptop", "OTS", False),
        ("shot-42f", "42F", "Insert — signal data on screen", "INSERT", False),
        ("shot-42g", "42G", "Close-up — Sarah's reaction", "CU", False),  # THIS ONE IS MISSING
        ("shot-42h", "42H", "Wide — room establishing (clean plate)", "WS", False),  # ALSO MISSING
    ]

    client.insert(
        "shots",
        data=[
            [s[0], "scene-42", PRODUCTION_ID, s[1], s[2], s[3],
             1 if s[1] not in ("42G", "42H") else 0, datetime.now()]
            for s in shots_42
        ],
        column_names=[
            "shot_id", "scene_id", "production_id", "shot_label", "description",
            "framing", "captured", "updated_at",
        ],
    )
    print(f"  ✓ {len(shots_42)} shots loaded for Scene 42")

    # --- Takes for Scene 42 ---
    print("  Loading takes...")
    base_time = datetime(2026, 8, 10, 10, 0, 0)
    takes_data = []
    for shot_idx, shot in enumerate(shots_42[:6]):  # Only first 6 shots have takes
        for take_num in range(1, 4):  # 3 takes each
            takes_data.append((
                f"take-{shot[1].lower()}-{take_num}",
                shot[0], "scene-42", PRODUCTION_ID,
                take_num, "A", "50mm",
                12.5 + take_num * 0.3,
                "select" if take_num == 2 else ("good" if take_num == 3 else "unrated"),
                "Good energy" if take_num == 2 else "",
                "Continuity OK" if take_num >= 2 else "",
                1 if take_num >= 2 else 0,  # audio_clean
                1 if take_num >= 2 else 0,  # continuity_verified
                base_time + timedelta(minutes=shot_idx * 15 + take_num * 3),
            ))

    client.insert(
        "takes",
        data=[list(t) + [datetime.now()] for t in takes_data],
        column_names=[
            "take_id", "shot_id", "scene_id", "production_id",
            "take_number", "camera", "lens", "duration_seconds", "rating",
            "director_notes", "script_supervisor_notes",
            "audio_clean", "continuity_verified", "captured_at", "inserted_at",
        ],
    )
    print(f"  ✓ {len(takes_data)} takes loaded")

    # --- Production Events ---
    print("  Loading production events...")
    events = [
        (generate_uuid(), base_time - timedelta(days=20), "SCRIPT_REVISION",
         "scene", "scene-31", {"revision": 1, "change": "Scene 31 added — first signal event"},
         "screenwriter"),
        (generate_uuid(), base_time - timedelta(days=15), "TAKE_CAPTURED",
         "take", "take-31a-1", {"scene": 31, "shot": "31A", "take": 1},
         "camera_dept"),
        (generate_uuid(), base_time - timedelta(days=15), "PROP_STATE_CHANGED",
         "prop", "prop-camera", {"from": "intact", "to": "damaged", "reason": "Scene 31 action — Sarah drops camera"},
         "props_dept"),
        (generate_uuid(), base_time - timedelta(hours=2), "SCENE_UPDATED",
         "scene", "scene-42", {"field": "description", "change": "Added damaged camera detail"},
         "script_supervisor"),
    ]

    client.insert(
        "production_events",
        data=[
            [e[0], PRODUCTION_ID, e[1], e[2], e[3], e[4],
             json.dumps(e[5]), e[6], "observed"]
            for e in events
        ],
        column_names=[
            "event_id", "production_id", "timestamp", "event_type",
            "entity_type", "entity_id", "data", "source", "epistemic",
        ],
    )
    print(f"  ✓ {len(events)} production events loaded")

    print(f"\n✅ Sample data loaded for '{production['title']}'")
    print(f"   Production ID: {PRODUCTION_ID}")
    print(f"   Scenes: {len(scenes_data)}")
    print(f"   Demo scenario: Scene 42 camera continuity conflict")


if __name__ == "__main__":
    main()
