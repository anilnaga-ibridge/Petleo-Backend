# Use Python base image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from current directory into container
COPY . /app

# Ensure Django finds the project
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=veterinary_service.settings

# Expose the Django port
EXPOSE 8000

# Start the Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
