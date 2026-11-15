# Compatibility shim: the Core now lives in the nexus_core package.
# Both entry points work:
#   uvicorn main:app            (legacy)
#   uvicorn nexus_core.main:app (canonical)
from nexus_core.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("nexus_core.main:app", host="127.0.0.1", port=8000)
