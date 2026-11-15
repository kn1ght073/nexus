"""LLM intent extraction via Ollama, with strict JSON-Schema validation.

The LLM's ONLY job is to emit a structured intent object. It never receives
tools, never sees file paths, and its output is rejected unless it matches
the intent schema exactly (plan §6.5: "no LLM-generated shell commands,
ever").
"""
import json
import re
from typing import Any

# The single shape an LLM response may take:
INTENT_SCHEMA = {
    "type": "object",
    "required": ["action", "title"],
    "properties": {
        "action": {"enum": ["create_task", "create_note"]},
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "description": {"type": "string", "maxLength": 2000},
        "priority": {"enum": ["low", "normal", "high"]},
    },
    "additionalProperties": False,
}


class IntentValidationError(ValueError):
    pass


def validate_intent(candidate: Any) -> dict:
    """Validate an LLM-produced object against INTENT_SCHEMA (subset check)."""
    if not isinstance(candidate, dict):
        raise IntentValidationError("intent must be a JSON object")
    for key in ("action", "title"):
        if key not in candidate:
            raise IntentValidationError(f"missing required field: {key}")
    action = candidate["action"]
    if action not in ("create_task", "create_note"):
        raise IntentValidationError(f"action must be create_task|create_note, got {action!r}")
    title = candidate["title"]
    if not isinstance(title, str) or not (1 <= len(title) <= 200):
        raise IntentValidationError("title must be a 1-200 char string")
    if "description" in candidate:
        desc = candidate["description"]
        if not isinstance(desc, str) or len(desc) > 2000:
            raise IntentValidationError("description must be a <=2000 char string")
    if "priority" in candidate and candidate["priority"] not in ("low", "normal", "high"):
        raise IntentValidationError("priority must be low|normal|high")
    allowed = set(INTENT_SCHEMA["properties"].keys())
    unknown = set(candidate.keys()) - allowed
    if unknown:
        raise IntentValidationError(f"unknown fields rejected: {sorted(unknown)}")
    return candidate


def _extract_json(raw: str) -> Any:
    """Pull the first JSON object out of an LLM response (models add prose)."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise IntentValidationError("no JSON object found in LLM output")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise IntentValidationError(f"malformed JSON: {e}") from e


# --- backends ---------------------------------------------------------------

def extract_intent_via_ollama(transcript: str, model: str = "llama3.2") -> dict:
    """Call a local Ollama server with a constrained prompt; validate output."""
    import urllib.request

    prompt = (
        "You convert a voice-note transcript into exactly one JSON object. "
        'Respond ONLY with JSON like {"action": "create_task", "title": "...", '
        '"description": "...", "priority": "normal"}. No prose, no code fences. '
        f"Transcript: {transcript[:1000]}"
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    return validate_intent(_extract_json(body.get("response", "")))


def extract_intent_mock(transcript: str) -> dict:
    """Deterministic rule-based 'LLM' for tests/sandbox: first sentence → task."""
    sentence = re.split(r"[.!?\n]", transcript.strip(), maxsplit=1)[0].strip()
    title = sentence[:200] if sentence else "Untitled voice note"
    return validate_intent(
        {
            "action": "create_task",
            "title": title,
            "description": transcript[:2000] or None,
            "priority": "normal",
        }
    )


def extract_intent(transcript: str, backend: str = "auto") -> dict:
    """Dispatch: auto tries Ollama, falls back to the mock backend."""
    if backend == "ollama":
        return extract_intent_via_ollama(transcript)
    if backend == "mock":
        return extract_intent_mock(transcript)
    try:
        return extract_intent_via_ollama(transcript)
    except Exception:
        # Ollama down/absent: deterministic fallback keeps the pipeline running
        return extract_intent_mock(transcript)
