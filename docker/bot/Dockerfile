FROM python:3.11-slim

WORKDIR /bot

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install discord.py asyncpg sqlalchemy alembic pydantic pydantic_settings asyncio fastapi uvicorn
RUN pip install aiosqlite3 pytest pytest-cov pytest-asyncio aiosqlite
CMD ["python", "main.py"]