# NEXUS Core API control plane - production image.
# Build context: services/core-api/
FROM python:3.12-slim

# Prevent bytecode writing and ensure unbuffered output for clean logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NEXUS_HOST=0.0.0.0

WORKDIR /app

# Create non-root user (F15)
RUN useradd -m -u 10001 appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY nexus_core/ ./nexus_core/

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Healthcheck probe (F15)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start uvicorn with proxy headers enabled (F8)
CMD ["python", "-m", "uvicorn", "nexus_core.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
