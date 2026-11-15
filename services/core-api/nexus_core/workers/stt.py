"""Speech-to-text worker.

Uses faster-whisper when installed; otherwise a deterministic mock so the
inbox pipeline stays testable without model weights (sandbox/dev).
"""
from dataclasses import dataclass


@dataclass
class Transcript:
    text: str
    backend: str  # "faster-whisper" | "mock"


def transcribe(audio_path: str) -> Transcript:
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(audio_path)
        text = " ".join(s.text.strip() for s in segments).strip()
        return Transcript(text=text, backend="faster-whisper")
    except ImportError:
        # Mock backend: derive a deterministic pseudo-transcript from the file
        # so the pipeline shape (audio -> text -> intent -> task) is testable.
        import hashlib
        from pathlib import Path

        size = Path(audio_path).stat().st_size if Path(audio_path).exists() else 0
        digest = hashlib.sha256(Path(audio_path).read_bytes()[:4096]).hexdigest()[:8] if size else ""
        return Transcript(
            text=f"[mock transcript of {Path(audio_path).name} ({size} bytes, {digest})]",
            backend="mock",
        )
