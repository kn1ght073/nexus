"""Background workers: STT, LLM intent extraction, action engine.

Implements the plan's AI safety rule (§6.5): the LLM never touches the
filesystem or shell. Its output is parsed to a strict intent schema, the
action engine validates it against a permission registry, and only then does
a deterministic handler run (task creation in this skeleton).

Model backends are optional: when faster-whisper or Ollama are absent, mock
implementations keep the pipeline testable without model downloads (sandbox).
"""
