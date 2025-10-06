# ────────── build image ──────────
# 1) Force amd64 so Azure Web App (x86_64) can run it
FROM python:3.11-slim AS base
WORKDIR /src

# Install system dependencies including browser dependencies for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY app/requirements.txt app/
RUN pip install --no-cache-dir -r app/requirements.txt

# Install Playwright browsers and dependencies (must be done as root)
RUN playwright install --with-deps chromium

# Copy the actual application code
COPY app/ app/

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /src

# Switch to appuser and install Playwright browsers for the user
USER appuser
RUN playwright install chromium

# Add /src to PYTHONPATH so 'from app.config' works
ENV PYTHONPATH=/src

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# gunicorn will listen on 8000 inside the container
EXPOSE 8000

# Use supervisor to manage multiple processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
