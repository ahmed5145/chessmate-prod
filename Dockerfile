FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV DJANGO_SETTINGS_MODULE=chess_mate.settings
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        stockfish \
        build-essential \
        libpq-dev \
        netcat-traditional \
        curl \
        gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project
COPY . /app/

# Build frontend (if present). We install Node 18 and run the build inside the image
RUN if [ -d "chess_mate/frontend" ] && [ -f "chess_mate/frontend/package.json" ]; then \
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
            apt-get update && apt-get install -y --no-install-recommends nodejs && \
            cd chess_mate/frontend && npm ci && npm run build && rm -rf node_modules; \
        else \
            echo "No frontend to build"; \
        fi

# Expose port
EXPOSE 8000

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Run entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
