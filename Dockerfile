# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Create non-root user
RUN groupadd -r clowdbot && useradd -r -g clowdbot -m clowdbot

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY clowdbot/ ./clowdbot/
COPY main.py .

# Create data directory
RUN mkdir -p /app/data && chown -R clowdbot:clowdbot /app

# Switch to non-root user
USER clowdbot

# Expose API port
EXPOSE 8080

# Volume for persistent data
VOLUME ["/app/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Graceful shutdown signal
STOPSIGNAL SIGTERM

# Proper signal handling with exec form
ENTRYPOINT ["python", "-u", "main.py"]
