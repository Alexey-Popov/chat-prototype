FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies (app/ must exist before setuptools builds the package)
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir -e .

# Copy remaining application files (migrations, tests, etc.)
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
