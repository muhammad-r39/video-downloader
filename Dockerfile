# Use a lightweight Python image
FROM python:3.10-slim

# Install system dependencies and FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Set the working directory
WORKDIR /app

# Copy app files to the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U yt-dlp

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Command to run the app
CMD ["python", "app.py"]
