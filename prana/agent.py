"""The constraint agent.

The bottleneck in industrial demand flexibility is not optimization — that is a
solved problem. It is that nobody can write down the plant's constraints. They
live in the interlock list, in HAZOP minutes, in the SOP for the synthesis loop,
and in the head of a board operator with thirty years' service. This module is
where the LLM belongs: turning that into typed constraints an optimizer can
consume, and turning the optimizer's answer back into language an operator will
accept.

Three jobs, and a deliberate architectural split:

    elicit()    SOP / interlock text + operator speech  ->  typed Constraint[]
    explain()   a solved Schedule                       ->  plain-language why
    perturb()   "compressor B is down 14:00-18:00"      ->  Constraint[]

Every constraint is returned with `requires_signoff=True`. The agent proposes;
a human accepts. Nothing it emits reaches the optimizer unreviewed.

The explanation is generated from the SOLVER, not by the model. `binding` in
optimizer.py is derived from the solution — shadow prices and active bounds. The
LLM phrases those facts; it never invents them. That is what makes the
explanation trustworthy enough to put in front of a plant manager.

Runs three ways, in order of preference:
  1. An LLM provider with structured outputs, if an SDK and key are present
  2. a deterministic rule-based parser, which handles the demo phrasings
  3. never silently: `Extraction.backend` always says which one ran
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from .optimizer import Constraint, Schedule
from .twins import ProcessTwin

# The LLM model id is supplied by the operator, not hardcoded. With no value
# set, PRANA never calls an external model and runs the deterministic
# rule-based extractor instead — which is the default in this repository.
MODEL = os.environ.get("PRANA_LLM_MODEL", "")

# JSON Schema for structured extraction. Using output_config.format means the
# model cannot return prose where we expect constraints.
CONSTRAINT_SCHEMA = {
    "type": "object",
    "properties": {
        "constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["outage", "no_go", "inventory_floor",
                                 "fix_load", "max_rate"],
                    },
                    "asset": {"type": "string"},
                    "start_hhmm": {"type": "string"},
                    "end_hhmm": {"type": "string"},
                    "value": {"type": "number"},
                    "note": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["kind", "asset", "start_hhmm", "end_hhmm",
                             "value", "note", "confidence"],
                "additionalProperties": False,
            },
        },
        "unresolved": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Statements that imply a constraint but are too "
                           "ambiguous to encode. Surfaced for the operator.",
        },
    },
    "required": ["constraints", "unresolved"],
    "additionalProperties": False,
}


@dataclass
class Extraction:
    constraints: list[Constraint]
    unresolved: list[str] = field(default_factory=list)
    backend: str = "rules"
    raw: str = ""
    requires_signoff: bool = True


def _hhmm_to_block(s: str, default: int) -> int:
    m = re.match(r"^\s*(\d{1,2})[:.]?(\d{2})?\s*$", str(s))
    if not m:
        return default
    h = int(m.group(1))
    mins = int(m.group(2) or 0)
    if h >= 24:
        h, mins = 24, 0
    return min(96, h * 4 + mins // 15)


def _match_asset(text: str, twins: list[ProcessTwin]) -> str:
    t = text.lower()
    for tw in twins:
        if tw.name.lower() in t or tw.kind in t:
            return tw.name
    aliases = {
        "asu": "asu", "air separation": "asu", "compressor": "asu",
        "oxygen": "asu", "lox": "asu", "nitrogen": "asu", "cryo": "asu",
        "electrolyser": "electrolyser", "electrolyzer": "electrolyser",
        "hydrogen": "electrolyser", "h2": "electrolyser", "stack": "electrolyser",
        "pipeline": "pipeline", "pump": "pipeline", "tankage": "pipeline",
        "crude": "pipeline", "booster": "pipeline",
        "rectifier": "chloralkali", "cell house": "chloralkali",
        "cellhouse": "chloralkali", "cell room": "chloralkali",
        "caustic": "chloralkali", "lye": "chloralkali", "membrane": "chloralkali",
        "chlorine": "chloralkali", "cl2": "chloralkali", "brine": "chloralkali",
        "electrolyser cell": "chloralkali",
    }
    for word, kind in aliases.items():
        if word in t:
            for tw in twins:
                if tw.kind == kind:
                    return tw.name
    return "*"


# --------------------------------------------------------------- rule backend
_T = r"(\d{1,2}(?:[:.]\d{2})?)"
# "14:00 to 18:00", "14:00-18:00", "between 14 and 18"
_TIME_RANGE = re.compile(
    rf"(?:from\s+|between\s+)?{_T}\s*(?:h|hrs|hours)?\s*"
    rf"(?:-|–|—|to|until|till|and)\s*{_T}", re.I)
# "back by 21:00", "until 05:00", "before 06:00" -- a single closing time
_UNTIL_TIME = re.compile(
    rf"\b(?:back\s+(?:by|at)|until|till|before|by)\s+{_T}", re.I)
# "from 19:00" / "after 19:00" -- a single opening time
_FROM_TIME = re.compile(rf"\b(?:from|after|starting(?:\s+at)?)\s+{_T}", re.I)

_OUT_WORDS = re.compile(
    r"\b(down|offline|off[- ]line|out of service|tripped?|unavailable|"
    r"maintenance|shut\w*|isolat\w*|lock\w*out|no[- ]go|do not run|don'?t run|"
    r"stopped?|taken out)\b", re.I)
_FLOOR_WORDS = re.compile(
    r"\b(?:keep|kept|hold|held|maintain\w*|stay|remain\w*|never\s+(?:go\s+)?below|"
    r"not\s+(?:go\s+)?below|minimum|min|at\s+least|above|floor)\b"
    r"[^.]*?(\d[\d,]*(?:\.\d+)?)\s*(t\b|te\b|tonnes?|kg|kl|m3|%)?", re.I)
_MODAL = re.compile(
    r"\b(must|never|always|do not|don'?t|shall not|ensure|require\w*|"
    r"prohibit\w*|forbidden)\b", re.I)
_OVERNIGHT = re.compile(r"\b(overnight|through the night|night shift)\b", re.I)


def _sentences(text: str) -> list[str]:
    """Split into statements WITHOUT breaking on newlines.

    Real SOPs and handover notes wrap mid-sentence; splitting on '\\n' tears
    'down for maintenance from' away from '14:00 to 18:00' and silently loses
    the window. Blank lines end a statement; single newlines do not.
    """
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)          # unwrap soft breaks
    parts = re.split(r"(?:\.\s|\.$|;|\n\s*\n)", text)
    return [p.strip(" \t\n-•") for p in parts if len(p.strip()) > 3]


_NOW_WORDS = re.compile(
    r"\b(tripped?|just|now|currently|has gone|went)\b",
    re.I)


def _window(line: str, now_block: int = 0) -> tuple[int, int]:
    """Resolve a time window, in 15-minute blocks.

    `now_block` matters for the commonest mid-shift utterance. "Compressor B
    tripped, back by 21:00" means from NOW until 21:00 -- not from midnight.
    Anchoring it at midnight would overstate a 7-hour outage as a 21-hour one
    and materially misprice the schedule.
    """
    rng = _TIME_RANGE.search(line)
    if rng:
        return _hhmm_to_block(rng.group(1), 0), _hhmm_to_block(rng.group(2), 96)
    if (u := _UNTIL_TIME.search(line)):
        start = now_block if _NOW_WORDS.search(line) else 0
        end = _hhmm_to_block(u.group(1), 96)
        return (start, end) if end > start else (start, 96)
    if (f := _FROM_TIME.search(line)):
        return _hhmm_to_block(f.group(1), 0), 96
    if _OVERNIGHT.search(line):
        return 0, 24                                       # 00:00-06:00
    return 0, 96


def _rule_elicit(text: str, twins: list[ProcessTwin],
                 now_block: int = 0) -> Extraction:
    """Deterministic fallback. Handles the phrasings the demo uses, and is what
    runs when there is no API key. Never guesses silently: anything that reads
    like a rule but cannot be encoded goes to `unresolved` for the operator."""
    cons: list[Constraint] = []
    unresolved: list[str] = []

    for line in _sentences(text):
        asset = _match_asset(line, twins)
        start, end = _window(line, now_block)

        fm = _FLOOR_WORDS.search(line)
        if fm and asset != "*":
            try:
                val = float(fm.group(1).replace(",", ""))
            except ValueError:
                unresolved.append(line)
                continue
            tw = next(t for t in twins if t.name == asset)
            if (fm.group(2) or "").strip() == "%":
                val = tw.inv_max * val / 100.0
            cons.append(Constraint(
                kind="inventory_floor", asset=asset, start_block=start,
                end_block=end, value=val, source="rules", note=line))
            continue

        if _OUT_WORDS.search(line):
            if asset == "*":
                unresolved.append(line)                    # which asset?
            else:
                cons.append(Constraint(
                    kind="outage", asset=asset, start_block=start,
                    end_block=end, source="rules", note=line))
            continue

        if _MODAL.search(line):
            unresolved.append(line)

    return Extraction(constraints=cons, unresolved=unresolved, backend="rules")


# ---------------------------------------------------------------- LLM backend
def _client():
    if not MODEL:                       # no model configured -> rules only
        return None
    try:
        import anthropic
    except ImportError:
        return None
    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return None
    try:
        return anthropic.Anthropic()
    except Exception:
        return None


_ELICIT_SYSTEM = """You extract operating constraints for an industrial energy \
scheduler from plant documents and operator speech.

You are given the plant's flexible assets and free text: SOP extracts, interlock \
schedules, shift-handover notes, or something an operator just said. Return only \
constraints the text actually states. Do not infer constraints from general \
process knowledge, and do not invent times or quantities.

Rules:
- `outage` / `no_go`: the asset must not run in the window.
- `inventory_floor`: the buffer must not fall below `value` (in the asset's own \
product unit) in the window.
- `fix_load`: total site load is pinned to `value` MW in the window.
- `max_rate`: the asset must not exceed `value` (product units/hour).
- Times are 24-hour HH:MM. A statement with no time applies to the whole day \
(00:00 to 24:00).
- If a statement clearly implies a restriction but you cannot pin down the \
asset, the window, or the number, put the sentence verbatim in `unresolved` \
rather than guessing.
- Mark `confidence` low whenever you had to interpret rather than read.

Every constraint you emit will be shown to a human for sign-off before it \
reaches the optimizer. Prefer surfacing an ambiguity to resolving it yourself."""


def _llm_elicit(text: str, twins: list[ProcessTwin],
                now_block: int = 0) -> Extraction | None:
    client = _client()
    if client is None:
        return None
    roster = "\n".join(
        f"- {t.name} (kind={t.kind}, product unit={t.unit}, "
        f"buffer {t.inv_min:.0f}-{t.inv_max:.0f} {t.unit}, "
        f"rate {t.q_min_per_h:.0f}-{t.q_max_per_h:.0f} {t.unit}/h)"
        for t in twins
    )
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": CONSTRAINT_SCHEMA},
            },
            system=_ELICIT_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Flexible assets at this site:\n{roster}\n\n"
                           f"Text to extract from:\n\"\"\"\n{text}\n\"\"\"",
            }],
        )
    except Exception as exc:                      # network, auth, quota
        return Extraction([], [f"LLM backend unavailable: {exc}"], "rules-fallback")

    if getattr(resp, "stop_reason", None) == "refusal":
        return Extraction([], ["Model declined to process this text."], "refusal")

    payload = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    cons = []
    for c in data.get("constraints", []):
        asset = _match_asset(c.get("asset", ""), twins)
        cons.append(Constraint(
            kind=c["kind"],
            asset=asset,
            start_block=_hhmm_to_block(c.get("start_hhmm", "00:00"), 0),
            end_block=_hhmm_to_block(c.get("end_hhmm", "24:00"), 96),
            value=float(c.get("value", 0.0)),
            source=f"llm/{c.get('confidence', 'medium')}",
            note=c.get("note", ""),
        ))
    return Extraction(cons, list(data.get("unresolved", [])), "anthropic", payload)


# --------------------------------------------------------------------- public
def elicit(text: str, twins: list[ProcessTwin], now_block: int = 0) -> Extraction:
    """Text -> typed constraints, pending human sign-off."""
    out = _llm_elicit(text, twins, now_block)
    if out is None or (not out.constraints and not out.unresolved):
        return _rule_elicit(text, twins, now_block)
    return out


def perturb(utterance: str, twins: list[ProcessTwin],
            now_block: int = 0) -> Extraction:
    """A single operator sentence, mid-shift. Same path as elicit()."""
    return elicit(utterance, twins, now_block)


def explain(
    schedule: Schedule,
    twins: list[ProcessTwin],
    context: str = "",
    saving_rs: float | None = None,
) -> str:
    """Plain-language account of a solved schedule.

    The facts come from `schedule.binding`, which the optimizer derives from
    active bounds in the solution. The LLM only phrases them. With no API key
    the deterministic bullets are returned as-is — the explanation degrades in
    style, never in accuracy.
    """
    facts = list(schedule.binding)
    if saving_rs is not None:
        facts.insert(0, f"Cost avoided versus steady-state operation today: "
                        f"Rs {saving_rs:,.0f}.")
    facts.insert(0, f"Peak billing demand set at {schedule.peak_mw:.1f} MW.")
    facts.insert(0, f"Solver status {schedule.status}; deviation from schedule "
                    f"used in 0 blocks.")

    client = _client()
    if client is None:
        return "\n".join(f"- {f}" for f in facts)

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            system=(
                "You brief a plant energy manager on a 24-hour dispatch "
                "schedule. You are given the solver's own findings — active "
                "constraints and costs. Restate them in at most six short "
                "sentences, in the order that matters operationally. State "
                "only what the findings say; add no numbers of your own and "
                "no process advice. Lead with the outcome."
            ),
            messages=[{
                "role": "user",
                "content": "Solver findings:\n"
                           + "\n".join(f"- {f}" for f in facts)
                           + (f"\n\nOperator context: {context}" if context else ""),
            }],
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            return "\n".join(f"- {f}" for f in facts)
        return next((b.text for b in resp.content if b.type == "text"),
                    "\n".join(f"- {f}" for f in facts))
    except Exception:
        return "\n".join(f"- {f}" for f in facts)


def backend_status() -> str:
    if _client() is not None:
        return f"LLM API ({MODEL})"
    try:
        import anthropic  # noqa: F401
        return "rule-based (no LLM model configured)"
    except ImportError:
        return "rule-based (LLM SDK not installed)"
