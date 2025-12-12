#!/bin/bash

# Define the path to Docker executable if not in PATH
DOCKER_CMD="/Applications/Docker.app/Contents/Resources/bin/docker"

# Check if docker is in PATH, if so use it, otherwise use the hardcoded path
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
fi

echo "🧹 Cleaning Infrastructure Services..."

# Stop and remove containers, networks, and orphan volumes
$DOCKER_CMD compose down --remove-orphans

echo "✅ All services stopped and cleaned."
