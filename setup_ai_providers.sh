#!/bin/bash

###############################################################################
# Setup AI Providers: Ollama (Development) + OVHCloud (Production)
#
# Usage:
#   bash setup_ai_providers.sh [dev|prod]
#
# Example:
#   bash setup_ai_providers.sh dev      # Configure Ollama locally
#   bash setup_ai_providers.sh prod     # Configure OVHCloud
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if environment parameter provided
if [ -z "$1" ]; then
    print_error "Missing environment parameter"
    echo "Usage: bash setup_ai_providers.sh [dev|prod]"
    echo ""
    echo "Examples:"
    echo "  bash setup_ai_providers.sh dev       # Setup Ollama for development"
    echo "  bash setup_ai_providers.sh prod      # Setup OVHCloud for production"
    exit 1
fi

ENVIRONMENT=$1

###############################################################################
# DEVELOPMENT: Ollama Setup
###############################################################################
setup_ollama() {
    print_header "🤖 Setting up Ollama for Development"

    # Check OS
    OS=$(uname -s)

    if [[ "$OS" == "Darwin" ]]; then
        print_info "Detected macOS"
        print_info "Installing Ollama..."

        if ! command -v ollama &> /dev/null; then
            curl https://ollama.ai/install.sh | sh
            print_success "Ollama installed"
        else
            print_info "Ollama already installed"
            ollama --version
        fi

    elif [[ "$OS" == "Linux" ]]; then
        print_info "Detected Linux"

        if ! command -v ollama &> /dev/null; then
            curl https://ollama.ai/install.sh | sh
            print_success "Ollama installed"
        else
            print_info "Ollama already installed"
            ollama --version
        fi

    elif [[ "$OS" == "MINGW64_NT" ]] || [[ "$OS" == "MSYS_NT" ]] || [[ "$OS" == "CYGWIN_NT" ]]; then
        print_warning "Windows detected"
        echo "Please install Ollama manually from: https://ollama.ai/download"
        echo "Then run this script again."
        exit 1
    else
        print_error "Unknown operating system: $OS"
        exit 1
    fi

    # Download model
    print_info "Downloading llama3.1:8b model (this may take a few minutes)..."
    ollama pull llama3.1:8b
    print_success "Model downloaded"

    # Create .env file
    print_info "Creating .env file..."

    cat > .env << 'EOF'
# =========================================
# DEVELOPMENT: Ollama Local
# =========================================

# AI Provider
AI_PROVIDER=ollama

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=30

# Cache settings
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=86400

# Confidence threshold
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7

# Telemetry
IMPORT_AI_LOG_TELEMETRY=true

# Database (adjust as needed)
DATABASE_URL=postgresql://user:password@localhost:5432/gestiqcloud
EOF

    print_success ".env file created"

    # Instructions
    print_header "✅ Ollama Setup Complete"
    echo "Next steps:"
    echo ""
    echo "1. Start Ollama in a new terminal:"
    echo "   ${BLUE}ollama serve${NC}"
    echo ""
    echo "2. Verify installation:"
    echo "   ${BLUE}curl http://localhost:11434/api/tags${NC}"
    echo ""
    echo "3. Start your backend:"
    echo "   ${BLUE}cd apps/backend && uvicorn main:app --reload${NC}"
    echo ""
    echo "4. Test classification:"
    echo "   ${BLUE}curl -X POST http://localhost:8000/api/v1/imports/uploads/analyze${NC}"
    echo ""
}

###############################################################################
# PRODUCTION: OVHCloud Setup
###############################################################################
setup_ovhcloud() {
    print_header "☁️  Setting up OVHCloud for Production"

    # Prompt for credentials
    echo "Please provide OVHCloud API credentials:"
    echo ""

    read -p "OVHCloud API Key: " OVHCLOUD_API_KEY
    if [ -z "$OVHCLOUD_API_KEY" ]; then
        print_error "API Key is required"
        exit 1
    fi

    read -s -p "OVHCloud API Secret: " OVHCLOUD_API_SECRET
    if [ -z "$OVHCLOUD_API_SECRET" ]; then
        print_error "API Secret is required"
        exit 1
    fi
    echo ""

    read -p "OVHCloud Model [gpt-4o]: " OVHCLOUD_MODEL
    OVHCLOUD_MODEL=${OVHCLOUD_MODEL:-gpt-4o}

    # Validate credentials
    print_info "Validating OVHCloud credentials..."

    HEALTH_CHECK=$(curl -s -X GET \
        "https://manager.eu.ovhcloud.com/api/v2/ai/health" \
        -H "Authorization: Bearer $OVHCLOUD_API_KEY" \
        -H "X-OVH-Secret: $OVHCLOUD_API_SECRET" \
        -H "Content-Type: application/json" \
        -w "%{http_code}" \
        -o /dev/null)

    if [ "$HEALTH_CHECK" != "200" ]; then
        print_error "OVHCloud API health check failed (HTTP $HEALTH_CHECK)"
        print_info "Please verify your API credentials"
        exit 1
    fi

    print_success "OVHCloud credentials validated"

    # Create .env.production file
    print_info "Creating .env.production file..."

    cat > .env.production << EOF
# =========================================
# PRODUCTION: OVHCloud
# =========================================

# AI Provider
AI_PROVIDER=ovhcloud

# OVHCloud Configuration
OVHCLOUD_API_KEY=$OVHCLOUD_API_KEY
OVHCLOUD_API_SECRET=$OVHCLOUD_API_SECRET
OVHCLOUD_BASE_URL=https://manager.eu.ovhcloud.com/api/v2
OVHCLOUD_MODEL=$OVHCLOUD_MODEL
OVHCLOUD_TIMEOUT=60

# Cache settings (aggressive in production)
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=604800

# Confidence threshold
IMPORT_AI_CONFIDENCE_THRESHOLD=0.75

# Telemetry
IMPORT_AI_LOG_TELEMETRY=true

# Rate limiting
IMPORT_AI_MAX_REQUESTS_PER_MINUTE=100

# Database (adjust as needed)
DATABASE_URL=postgresql://prod_user:prod_password@prod-db:5432/gestiqcloud_prod
EOF

    print_success ".env.production file created"

    # Instructions
    print_header "✅ OVHCloud Setup Complete"
    echo "Next steps:"
    echo ""
    echo "1. Deploy to production server"
    echo "   ${BLUE}export AI_PROVIDER=ovhcloud${NC}"
    echo "   ${BLUE}export OVHCLOUD_API_KEY=$OVHCLOUD_API_KEY${NC}"
    echo "   ${BLUE}export OVHCLOUD_API_SECRET=$OVHCLOUD_API_SECRET${NC}"
    echo ""
    echo "2. Restart backend:"
    echo "   ${BLUE}systemctl restart gestiqcloud-backend${NC}"
    echo "   ${BLUE}# or${NC}"
    echo "   ${BLUE}docker restart gestiqcloud-backend${NC}"
    echo ""
    echo "3. Verify health:"
    echo "   ${BLUE}curl http://localhost:8000/api/v1/imports/ai/health${NC}"
    echo ""
    echo "4. Check metrics:"
    echo "   ${BLUE}curl http://localhost:8000/api/v1/imports/ai/telemetry${NC}"
    echo ""

    # Save credentials info
    print_info "Credentials saved in .env.production (KEEP SECURE!)"
    print_warning "Never commit .env.production to git!"

}

###############################################################################
# Main Logic
###############################################################################

case $ENVIRONMENT in
    dev)
        setup_ollama
        ;;
    prod)
        setup_ovhcloud
        ;;
    *)
        print_error "Unknown environment: $ENVIRONMENT"
        echo "Valid options: dev, prod"
        exit 1
        ;;
esac

print_header "✨ Setup Complete!"
