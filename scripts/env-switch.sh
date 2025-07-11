#!/bin/bash

# Environment switching script for AI Receptionist
# Usage: ./scripts/env-switch.sh [dev|prod]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

switch_to_dev() {
    print_status "Switching to development environment..."
    
    if [ ! -f ".env" ]; then
        print_warning "No .env file found. Creating from template..."
        cp env.example .env
        print_success "Created .env from template. Please edit it with your development values."
    else
        print_success "Using existing .env file for development."
    fi
    
    print_status "Current environment: DEVELOPMENT"
    print_status "Environment file: .env"
}

switch_to_prod() {
    print_status "Switching to production environment..."
    
    if [ ! -f ".env.prod" ]; then
        print_error "No .env.prod file found. Please create it first."
        exit 1
    fi
    
    # Backup current .env if it exists
    if [ -f ".env" ]; then
        cp .env .env.backup
        print_status "Backed up current .env to .env.backup"
    fi
    
    # Copy production env to .env
    cp .env.prod .env
    print_success "Switched to production environment."
    
    print_status "Current environment: PRODUCTION"
    print_status "Environment file: .env (copied from .env.prod)"
    print_warning "Remember to switch back to development when done!"
}

show_current() {
    if [ -f ".env" ]; then
        print_status "Current environment file: .env"
        print_status "Environment type: $(grep -q "DEBUG=False" .env && echo "PRODUCTION" || echo "DEVELOPMENT")"
    else
        print_error "No .env file found."
    fi
}

# Main script logic
case "${1:-help}" in
    "dev")
        switch_to_dev
        ;;
    "prod")
        switch_to_prod
        ;;
    "current"|"status")
        show_current
        ;;
    "help"|*)
        echo "Usage: ./scripts/env-switch.sh [command]"
        echo ""
        echo "Commands:"
        echo "  dev      Switch to development environment"
        echo "  prod     Switch to production environment"
        echo "  current  Show current environment status"
        echo "  help     Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./scripts/env-switch.sh dev   # Use development settings"
        echo "  ./scripts/env-switch.sh prod  # Use production settings"
        ;;
esac 