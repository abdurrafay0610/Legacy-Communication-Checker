# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

# Keep Python lean and output unbuffered in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install OS deps: tini for proper PID 1 signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 10001 appuser

WORKDIR /app

# -------------------------------------------------------------------
# Copy code files
# -------------------------------------------------------------------
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r packet_sender_web3/requirements.txt

# Create the data directories the app writes to at runtime
RUN mkdir -p packet_sender_web3/data/logs \
             "Packets Definition" && \
    chown -R appuser:appuser /app

# Drop privileges
USER appuser

# The web app runs on port 7860
EXPOSE 7860
ENV PORT=7860

# Use tini as PID 1 so signals (Ctrl-C, docker stop) are handled correctly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run the Flask app from inside the web3 folder so relative paths
# (templates/, static/, data/) resolve correctly
CMD ["python", "packet_sender_web3/app.py"]