#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}   🚀 Starting PetLeo Kafka Consumers (Perm)   ${NC}"
echo -e "${BLUE}===============================================${NC}"

# Function to check if a process is running
check_process() {
    if pgrep -f "$1" > /dev/null; then
        echo -e "${GREEN}✅ $2 is already running.${NC}"
        return 0
    else
        echo -e "${RED}❌ $2 is NOT running. Starting...${NC}"
        return 1
    fi
}

# 1. Auth Service Consumer
echo -e "\n${BLUE}🔍 Checking Auth Service Consumer...${NC}"
if ! check_process "auth_service/kafka_consumer.py" "Auth Consumer"; then
    cd "/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service"
    # Use the temp_kafka_venv if available, or default python
    if [ -d "temp_kafka_venv" ]; then
        nohup ./temp_kafka_venv/bin/python3 auth_service/kafka_consumer.py > auth_consumer.log 2>&1 &
    else
        nohup python3 auth_service/kafka_consumer.py > auth_consumer.log 2>&1 &
    fi
    echo -e "${GREEN}   Started Auth Consumer (PID: $!). Logs: auth_consumer.log${NC}"
fi

# 2. Service Provider Consumer (Port 8002)
echo -e "\n${BLUE}🔍 Checking Service Provider Consumer (Port 8002)...${NC}"
if ! check_process "service_provider_service/kafka_consumer.py" "SP Consumer"; then
    cd "/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service"
    if [ -d "venv" ]; then
        nohup ./venv/bin/python3 kafka_consumer.py > consumer_port_8002.log 2>&1 &
    else
        nohup python3 kafka_consumer.py > consumer_port_8002.log 2>&1 &
    fi
    echo -e "${GREEN}   Started SP Consumer (PID: $!). Logs: consumer_port_8002.log${NC}"
fi

# 3. Super Admin Consumer (Port 8003)
echo -e "\n${BLUE}🔍 Checking Super Admin Consumer (Port 8003)...${NC}"
if ! check_process "super_admin_service/kafka_consumer.py" "SA Consumer"; then
    cd "/Users/PraveenWorks/Anil Works/PetLeo-Backend/super_admin_service"
    if [ -d "venv" ]; then
        nohup ./venv/bin/python3 kafka_consumer.py > consumer_port_8003.log 2>&1 &
    else
        nohup python3 kafka_consumer.py > consumer_port_8003.log 2>&1 &
    fi
    echo -e "${GREEN}   Started SA Consumer (PID: $!). Logs: consumer_port_8003.log${NC}"
fi

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${GREEN}   ✅ All Consumers Checked/Started   ${NC}"
echo -e "${BLUE}===============================================${NC}"
