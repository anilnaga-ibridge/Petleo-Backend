#!/bin/bash

# Define the path to Docker executable if not in PATH
DOCKER_CMD="/Applications/Docker.app/Contents/Resources/bin/docker"

# Check if docker is in PATH, if so use it, otherwise use the hardcoded path
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
fi

echo "Starting Infrastructure Services (Zookeeper, Kafka, Kafka UI, Redis, Redis Insight)..."

# Ensure a clean slate
./clean_infra.sh

$DOCKER_CMD compose up -d zookeeper kafka kafka-ui redis redis-insight

echo "Services started!"
echo "Kafka UI: http://localhost:8085"
echo "Redis Insight: http://localhost:5540"



# ./stop_infra.sh

# ./start_infra.sh