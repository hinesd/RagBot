FROM python:3.14-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync

# Copy application code
COPY . .

EXPOSE 8000

# Command is defined in docker-compose.yml
CMD ["uv", "run", "fastapi", "dev", "main.py"]
