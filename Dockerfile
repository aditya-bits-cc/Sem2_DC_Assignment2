# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# For security purposes we run the container as a non-root user to run the application
RUN useradd -m -u 1000 chatappuser

# Switch to non-root user
USER chatappuser

# We will mount our code from the host, so we don't need to COPY it.
# This file just ensures the container has Python and a working directory.