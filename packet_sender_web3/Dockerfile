# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

# Keep Python lean & chatty in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install minimal OS deps (none needed now, but keep basics handy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 10001 appuser

WORKDIR /app

# Copy source
# (If you later add requirements.txt, copy & pip install before copying source for better caching)
COPY file_writter.py packet.py packet_authentication_functions.py app.py README.md ./

# Ensure the runtime folder exists (name has a space)
RUN mkdir -p "Packets Definition" && chown -R appuser:appuser /app

# Drop privileges
USER appuser

# Use Tini as PID 1 for proper signal handling in interactive mode
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command launches your interactive menu app
CMD ["python", "app.py"]
