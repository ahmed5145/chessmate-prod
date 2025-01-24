FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        stockfish \
        netcat-traditional \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r chessmate && useradd -r -g chessmate chessmate

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories first
RUN mkdir -p /app/chess_mate \
    && mkdir -p /app/chess_mate/logs \
    && mkdir -p /app/chess_mate/media \
    && mkdir -p /app/chess_mate/staticfiles \
    && touch /app/chess_mate/logs/django.log \
    && chown -R chessmate:chessmate /app \
    && chmod -R 755 /app \
    && chmod -R 777 /app/chess_mate/logs \
    && chmod 666 /app/chess_mate/logs/django.log

# Copy project files
COPY chess_mate/ /app/chess_mate/
COPY scripts/entrypoint.sh /app/entrypoint.sh

# Set permissions again after copying files
RUN chown -R chessmate:chessmate /app \
    && chmod -R 755 /app/chess_mate \
    && chmod -R 777 /app/chess_mate/logs \
    && chmod -R 777 /app/chess_mate/media \
    && chmod -R 777 /app/chess_mate/staticfiles \
    && chmod 666 /app/chess_mate/logs/django.log \
    && chmod +x /app/entrypoint.sh

# Set Python path
ENV PYTHONPATH=/app/chess_mate

# Switch to non-root user
USER chessmate

# Expose port
EXPOSE 8000

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 