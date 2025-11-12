# Use Python base image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy everything from current directory into container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Django finds the project
ENV PYTHONPATH=/app/auth_service
ENV DJANGO_SETTINGS_MODULE=auth_service.settings

# Expose the Django port
EXPOSE 8000

# Start the Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
