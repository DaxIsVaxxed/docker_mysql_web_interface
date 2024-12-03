# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files and buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt /app/

# Install the dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app/

# Expose port 5000 to allow traffic to the Flask app
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
