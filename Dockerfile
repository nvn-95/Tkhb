FROM python:3.9-slim

WORKDIR /app

# Install system dependencies required for OpenCV and MediaPipe AI
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them securely
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the existing project files
COPY . .

# Ensure the dataset folder exists inside the container
RUN mkdir -p dataset_videos

EXPOSE 5000

# Start the Flask Webserver
CMD ["python", "app.py"]
