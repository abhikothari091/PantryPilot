# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED True
ENV APP_HOME /app
ENV PORT 8080
WORKDIR $APP_HOME

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the function source code into the container
COPY main.py .

# Set the command to run the Functions Framework server
# This will start a web server that listens for HTTP requests and invokes the function
CMD ["functions-framework", "--target=dpo_training_handler", "--port=8080"]
