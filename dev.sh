#!/bin/bash

# ==============================================================================
# PetLeo Unified Development Script (dev.sh)
# Optimized for macOS
# ==============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base Directories
BACKEND_DIR="/Users/PraveenWorks/Anil Works/Petleo-Backend"
FRONTEND_DIR="/Users/PraveenWorks/Anil Works/PetLeo-frontend"

# PID file to track started processes
PID_FILE="$BACKEND_DIR/.dev_pids"

# Function to print section headers
print_header() {
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE}   🚀 $1   ${NC}"
    echo -e "${BLUE}===============================================${NC}"
}

# Function to start a service in the background
start_background() {
    local dir=$1
    local cmd=$2
    local name=$3
    local log_file=$4
    local venv_path=$5

    echo -ne "Starting ${YELLOW}$name${NC}... "
    cd "$dir" || return
    
    if [ -n "$venv_path" ] && [ -d "$venv_path" ]; then
        nohup "$venv_path/bin/python3" $cmd > "$log_file" 2>&1 &
    else
        nohup python3 $cmd > "$log_file" 2>&1 &
    fi
    
    echo $! >> "$PID_FILE"
    echo -e "${GREEN}DONE (PID: $!)${NC}"
}

# Function to start infrastructure
start_infra() {
    print_header "Starting Infrastructure (Docker)"
    cd "$BACKEND_DIR" || exit
    if [ -f "start_infra.sh" ]; then
        ./start_infra.sh
    else
        docker-compose up -d
    fi
    echo -e "${GREEN}Infrastructure is up!${NC}"
}

# Function to start all backend services
start_backend() {
    print_header "Starting Backend Services"
    
    # Format: start_background "dir" "cmd" "name" "log_file" "venv"
    
    start_background "$BACKEND_DIR/Auth_Service" "auth_service/manage.py runserver 0.0.0.0:8000" "Auth Service (8000)" "auth_server.log" "temp_kafka_venv"
    start_background "$BACKEND_DIR/service_provider_service" "manage.py runserver 8002" "SP Service (8002)" "sp_server.log" "venv"
    start_background "$BACKEND_DIR/super_admin_service" "manage.py runserver 8003" "SA Service (8003)" "sa_server.log" "venv"
    start_background "$BACKEND_DIR/veterinary_service" "manage.py runserver 8004" "Vet Service (8004)" "vet_server.log" "venv"
    start_background "$BACKEND_DIR/customer_service" "manage.py runserver 8005" "Customer Service (8005)" "customer_server.log" "venv"
    start_background "$BACKEND_DIR/booking_service" "manage.py runserver 8006" "Booking Service (8006)" "booking_server.log" "venv"
}

# Function to start all kafka consumers
start_consumers() {
    print_header "Starting Kafka Consumers"
    
    start_background "$BACKEND_DIR/Auth_Service" "auth_service/kafka_consumer.py" "Auth Consumer" "auth_consumer.log" "temp_kafka_venv"
    start_background "$BACKEND_DIR/service_provider_service" "kafka_consumer.py" "SP Consumer" "sp_consumer.log" "venv"
    start_background "$BACKEND_DIR/super_admin_service" "kafka_consumer.py" "SA Consumer" "sa_consumer.log" "venv"
    start_background "$BACKEND_DIR/veterinary_service" "kafka_consumer.py" "Vet Consumer" "vet_consumer.log" "venv"
    start_background "$BACKEND_DIR/customer_service" "kafka_consumer.py" "Customer Consumer" "customer_consumer.log" "venv"
}

# Function to start frontend
start_frontend() {
    print_header "Starting Frontend"
    echo -ne "Starting ${YELLOW}PetLeo Frontend${NC}... "
    cd "$FRONTEND_DIR" || return
    nohup pnpm run dev > frontend.log 2>&1 &
    echo $! >> "$PID_FILE"
    echo -e "${GREEN}DONE (PID: $!)${NC}"
}

# Function to stop all services
stop_all() {
    print_header "Stopping All Services"
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if ps -p "$pid" > /dev/null; then
                echo -e "Stopping PID ${RED}$pid${NC}..."
                kill "$pid" 2>/dev/null
            fi
        done < "$PID_FILE"
        rm "$PID_FILE"
        echo -e "${GREEN}All local processes stopped.${NC}"
    else
        echo -e "${YELLOW}No PID file found. Nothing to stop.${NC}"
    fi
    
    # Also stop docker infra if requested or just provide reminder
    echo -e "\n${YELLOW}Tip: Run ./stop_infra.sh to stop Docker containers if needed.${NC}"
}

# Function to show status
status() {
    print_header "Service Status"
    if [ -f "$PID_FILE" ]; then
        echo -e "Monitoring PIDs from $PID_FILE:"
        while read pid; do
            if ps -p "$pid" > /dev/null; then
                echo -e "PID ${GREEN}$pid${NC} is running."
            else
                echo -e "PID ${RED}$pid${NC} is NOT running."
            fi
        done < "$PID_FILE"
    else
        echo -e "${YELLOW}No services are currently tracked as running.${NC}"
    fi
}

# Main Logic
case "$1" in
    start)
        touch "$PID_FILE"
        start_infra
        start_backend
        start_consumers
        start_frontend
        echo -e "\n${GREEN}🚀 All services started!${NC}"
        echo -e "Check logs (*.log) in respective service directories for details."
        ;;
    stop)
        stop_all
        ;;
    status)
        status
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac


# 
# ./dev.sh start
# ./dev.sh stop
    