# NEXUS Core API control plane - production image.
# Build context: services/core-api/
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY nexus_core/ ./nexus_core/

# On Render this image runs with:
#   NEXUS_CONTROL_PLANE_MODE=true
#   NEXUS_JWT_SECRET=<pinned random secret>
#   NEXUS_DATABASE_URL=<Neon/Supabase Postgres URL>
# On your own machine (the node) you run the same code directly with
# `uvicorn nexus_core.main:app` and a local SQLite file - no Docker needed.
ENV NEXUS_HOST=0.0.0.0
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "nexus_core.main:app", "--host", "0.0.0.0", "--port", "8000"]
