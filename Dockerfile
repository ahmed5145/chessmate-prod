FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    DJANGO_SETTINGS_MODULE=chess_mate.settings_prod

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    stockfish \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 chessmate

# Create necessary directories with correct permissions
RUN mkdir -p /app/chess_mate/staticfiles /app/chess_mate/media /app/chess_mate/logs \
    && chown -R chessmate:chessmate /app \
    && chmod -R 755 /app/chess_mate/staticfiles \
    && chmod -R 755 /app/chess_mate/media \
    && chmod -R 755 /app/chess_mate/logs

# Copy the Django project first
COPY chess_mate /app/chess_mate/

# Copy the rest of the application code
COPY . .

# Set permissions for copied files
RUN chown -R chessmate:chessmate /app

# Switch to non-root user
USER chessmate

# Add the Django project root to PYTHONPATH
ENV PYTHONPATH=/app/chess_mate:$PYTHONPATH

# Command to run
CMD ["gunicorn", "chess_mate.wsgi:application", "--bind", "0.0.0.0:8000"] 