FROM python:3.11-slim

# Establish working directory in /app
WORKDIR /app

# Environment variable for Poetry version
ENV POETRY_VERSION=1.7.1

# Update pip and install Poetry and its dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

# Copy Poetry project definition files
# Ensure 'poetry.lock' exists locally before building.
COPY pyproject.toml poetry.lock* ./


# Copy the application directory to the container in /app
COPY . .

# Install the current project (the application)
RUN poetry install --no-interaction --no-ansi

# Expose port 8000 for the FastAPI application to be accessed
EXPOSE 8000

# Make the script executable and run it
RUN chmod +x docker-entrypoint.sh
CMD ["./docker-entrypoint.sh"]