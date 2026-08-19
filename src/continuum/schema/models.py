"""Core domain models for the Living Film Graph.

Every production entity is temporal — CONTINUUM knows what was true and when.
Three epistemic layers: OBSERVED → INFERRED → CONFIRMED.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EpistemicState(str, Enum):
    """How confident CONTINUUM is about a fact."""
    OBSERVED = "observed"    # Detected from data
    INFERRED = "inferred"    # Agent believes this is true
    CONFIRMED = "confirmed"  # Human or authoritative system accepted


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class TimeOfDay(str, Enum):
    DAY = "DAY"
    NIGHT = "NIGHT"
    DAWN = "DAWN"
    DUSK = "DUSK"


class InteriorExterior(str, Enum):
    INT = "INT"
    EXT = "EXT"
    INT_EXT = "INT/EXT"


class TakeRating(str, Enum):
    GOOD = "good"
    SELECT = "select"
    NO_GOOD = "no_good"
    UNRATED = "unrated"


# ---------------------------------------------------------------------------
# Production Events (ClickHouse event stream)
# ---------------------------------------------------------------------------

class ProductionEvent(BaseModel):
    """A single production event — the atomic unit of CONTINUUM's memory.

    Every action during production becomes an event stored in ClickHouse.
    """
    event_id: str = Field(description="Unique event identifier (UUID)")
    production_id: str = Field(description="Which production this belongs to")
    timestamp: datetime = Field(description="When the event occurred")
    event_type: str = Field(description="e.g. SCRIPT_REVISION, TAKE_CAPTURED, PROP_STATE_CHANGED")
    entity_type: str = Field(description="e.g. scene, take, prop, character, location")
    entity_id: str = Field(description="ID of the affected entity")
    data: dict = Field(default_factory=dict, description="Event-specific payload")
    source: str = Field(default="system", description="Who/what created the event")
    epistemic: EpistemicState = Field(default=EpistemicState.OBSERVED)


# ---------------------------------------------------------------------------
# Scene & Script
# ---------------------------------------------------------------------------

class Scene(BaseModel):
    """A screenplay scene with its production dependencies."""
    scene_id: str
    production_id: str
    scene_number: int
    slug: str = Field(description="e.g. 'INT. SARAH'S APARTMENT — NIGHT'")
    int_ext: InteriorExterior = InteriorExterior.INT
    location_name: str = ""
    time_of_day: TimeOfDay = TimeOfDay.DAY
    description: str = ""
    characters: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    wardrobe_notes: list[str] = Field(default_factory=list)
    dialogue_snippets: list[str] = Field(default_factory=list)
    story_dependencies: list[str] = Field(
        default_factory=list,
        description="Scene IDs this scene depends on (narrative continuity)"
    )
    revision: int = 1
    revision_color: str = "white"  # white, blue, pink, yellow, green, goldenrod...
    filmed: bool = False
    wrapped: bool = False


# ---------------------------------------------------------------------------
# Takes & Footage
# ---------------------------------------------------------------------------

class Take(BaseModel):
    """A single take captured during production."""
    take_id: str
    scene_id: str
    shot_id: str
    take_number: int
    camera: str = Field(default="A", description="Camera designation")
    lens: str = ""
    duration_seconds: float = 0.0
    rating: TakeRating = TakeRating.UNRATED
    director_notes: str = ""
    script_supervisor_notes: str = ""
    audio_clean: bool = True
    continuity_verified: bool = False
    timestamp: Optional[datetime] = None


class Shot(BaseModel):
    """A planned shot in the shot list."""
    shot_id: str
    scene_id: str
    shot_label: str = Field(description="e.g. '42A', '42B-CU'")
    description: str = ""
    framing: str = ""  # CU, MCU, MS, WS, etc.
    captured: bool = False
    takes: list[Take] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Production Assets
# ---------------------------------------------------------------------------

class Prop(BaseModel):
    """A trackable production prop."""
    prop_id: str
    name: str
    state: str = Field(description="Current physical state, e.g. 'damaged', 'intact'")
    scenes: list[str] = Field(default_factory=list, description="Scene IDs where this prop appears")
    notes: str = ""


class WardrobeItem(BaseModel):
    """A wardrobe/costume item linked to a character."""
    wardrobe_id: str
    character: str
    description: str
    scenes: list[str] = Field(default_factory=list)
    state: str = ""  # clean, dirty, torn, wet, etc.


# ---------------------------------------------------------------------------
# Production Intelligence
# ---------------------------------------------------------------------------

class ContinuityIssue(BaseModel):
    """A detected continuity problem."""
    issue_id: str
    scene_id: str
    severity: Severity
    category: str = Field(description="e.g. 'prop', 'wardrobe', 'dialogue', 'timeline'")
    description: str
    evidence: list[str] = Field(default_factory=list)
    epistemic: EpistemicState = EpistemicState.INFERRED
    resolved: bool = False
    resolution: str = ""


class CoverageAssessment(BaseModel):
    """FINAL TAKE's assessment of whether a scene has enough coverage."""
    scene_id: str
    planned_shots: int
    captured_shots: int
    usable_takes: int
    audio_verified: int
    continuity_verified: int
    director_selects: int
    coverage_confidence: float = Field(ge=0.0, le=1.0, description="0-1 confidence score")
    missing: list[str] = Field(default_factory=list, description="Missing coverage items")
    issues: list[ContinuityIssue] = Field(default_factory=list)
    safe_to_wrap: bool = False
    recommendation: str = ""


class ChangeImpact(BaseModel):
    """CASCADE's analysis of what a script/production change breaks."""
    change_description: str
    scenes_affected: list[str] = Field(default_factory=list)
    shots_affected: list[str] = Field(default_factory=list)
    props_affected: list[str] = Field(default_factory=list)
    wardrobe_affected: list[str] = Field(default_factory=list)
    vfx_affected: list[str] = Field(default_factory=list)
    continuity_conflicts: list[ContinuityIssue] = Field(default_factory=list)
    risk_level: Severity = Severity.INFO
    recommended_resolutions: list[str] = Field(default_factory=list)
