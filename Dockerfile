# Use Python 3.11 as the base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ruby \
    ruby-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY api/requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# Set up Ruby and Bundler
RUN gem install bundler:2.6.7

# Build Jekyll site
WORKDIR /app/frontend/jekyll_site
RUN bundle install
RUN bundle exec jekyll build

# Set back to main directory
WORKDIR /app

# Add the current directory to PYTHONPATH
ENV PYTHONPATH=/app/api

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 