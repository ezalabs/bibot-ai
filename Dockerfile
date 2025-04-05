# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy project files needed for installation
COPY pyproject.toml ./
COPY poetry.lock* ./
COPY README.md ./
COPY app ./app

# Configure Poetry to not create a virtual environment inside the container
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the application (config files, etc.)
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["poetry", "run", "python", "app/main.py"] 