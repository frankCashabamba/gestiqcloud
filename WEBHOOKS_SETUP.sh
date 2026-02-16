#!/bin/bash
# Webhooks Module - Setup and Verification Script

set -e  # Exit on error

echo "=========================================="
echo "GestiqCloud Webhooks Module Setup"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "apps/backend/app/modules/webhooks/README.md" ]; then
    echo -e "${RED}Error: webhooks module not found!${NC}"
    echo "Run this script from the gestiqcloud root directory"
    exit 1
fi

echo -e "${GREEN}✓ Webhooks module structure found${NC}"
echo ""

# Step 1: Check Python dependencies
echo "Step 1: Checking Python dependencies..."
python3 -c "import fastapi" && echo -e "${GREEN}✓ FastAPI installed${NC}" || echo -e "${RED}✗ FastAPI missing${NC}"
python3 -c "import sqlalchemy" && echo -e "${GREEN}✓ SQLAlchemy installed${NC}" || echo -e "${RED}✗ SQLAlchemy missing${NC}"
python3 -c "import pydantic" && echo -e "${GREEN}✓ Pydantic installed${NC}" || echo -e "${RED}✗ Pydantic missing${NC}"
python3 -c "import celery" 2>/dev/null && echo -e "${GREEN}✓ Celery installed${NC}" || echo -e "${YELLOW}⚠ Celery not installed (optional)${NC}"
python3 -c "import requests" && echo -e "${GREEN}✓ Requests installed${NC}" || echo -e "${RED}✗ Requests missing${NC}"
echo ""

# Step 2: Check database connection
echo "Step 2: Checking database configuration..."
if [ -n "$DATABASE_URL" ]; then
    echo -e "${GREEN}✓ DATABASE_URL configured${NC}"
else
    echo -e "${YELLOW}⚠ DATABASE_URL not set${NC}"
    echo "  Set with: export DATABASE_URL=postgresql://user:pass@localhost/db"
fi
echo ""

# Step 3: Run migration
echo "Step 3: Running Alembic migration..."
cd apps/backend
if alembic upgrade head; then
    echo -e "${GREEN}✓ Migration successful${NC}"
else
    echo -e "${RED}✗ Migration failed${NC}"
    echo "  Check DATABASE_URL and PostgreSQL connection"
    exit 1
fi
cd - > /dev/null
echo ""

# Step 4: Run tests
echo "Step 4: Running unit tests..."
if python3 -m pytest tests/test_webhooks.py -v --tb=short; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Some tests failed (check output above)${NC}"
fi
echo ""

# Step 5: Check file structure
echo "Step 5: Verifying file structure..."
files=(
    "apps/backend/app/modules/webhooks/__init__.py"
    "apps/backend/app/modules/webhooks/tasks.py"
    "apps/backend/app/modules/webhooks/utils.py"
    "apps/backend/app/modules/webhooks/domain/entities.py"
    "apps/backend/app/modules/webhooks/infrastructure/webhook_dispatcher.py"
    "apps/backend/app/modules/webhooks/interface/http/tenant.py"
    "apps/backend/tests/test_webhooks.py"
    "apps/backend/alembic/versions/012_webhook_subscriptions.py"
)

all_files_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file"
        all_files_exist=false
    fi
done

if $all_files_exist; then
    echo -e "${GREEN}✓ All files present${NC}"
else
    echo -e "${RED}✗ Some files missing${NC}"
    exit 1
fi
echo ""

# Step 6: Check imports
echo "Step 6: Checking Python imports..."
python3 << 'EOF'
try:
    from app.modules.webhooks import (
        WebhookEventType,
        WebhookStatus,
        DeliveryStatus,
        WebhookDispatcher,
        WebhookSignature,
        WebhookValidator,
        WebhookFormatter,
    )
    print("\033[0;32m✓\033[0m All imports successful")
except ImportError as e:
    print(f"\033[0;31m✗\033[0m Import error: {e}")
    exit(1)
EOF
echo ""

# Step 7: Check router registration
echo "Step 7: Checking router registration..."
if grep -q "webhooks.interface.http.tenant" apps/backend/app/platform/http/router.py; then
    echo -e "${GREEN}✓ Router registered in main router${NC}"
else
    echo -e "${RED}✗ Router not registered${NC}"
    exit 1
fi
echo ""

# Step 8: Configuration check
echo "Step 8: Checking configuration..."
if [ -n "$WEBHOOK_TIMEOUT_SECONDS" ]; then
    echo -e "${GREEN}✓ WEBHOOK_TIMEOUT_SECONDS=$WEBHOOK_TIMEOUT_SECONDS${NC}"
else
    echo -e "${YELLOW}⚠ WEBHOOK_TIMEOUT_SECONDS not set (default: 10s)${NC}"
fi

if [ -n "$WEBHOOK_MAX_RETRIES" ]; then
    echo -e "${GREEN}✓ WEBHOOK_MAX_RETRIES=$WEBHOOK_MAX_RETRIES${NC}"
else
    echo -e "${YELLOW}⚠ WEBHOOK_MAX_RETRIES not set (default: 3)${NC}"
fi

if [ -n "$CELERY_BROKER_URL" ]; then
    echo -e "${GREEN}✓ CELERY_BROKER_URL configured${NC}"
else
    echo -e "${YELLOW}⚠ CELERY_BROKER_URL not set (Celery optional)${NC}"
fi
echo ""

# Step 9: Summary
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start the backend server:"
echo "   cd apps/backend"
echo "   uvicorn app.main:app --reload"
echo ""
echo "2. (Optional) Start Celery worker:"
echo "   celery -A apps.backend.celery_app worker -l info"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8000/api/v1/tenant/webhooks/subscriptions \\"
echo "     -H 'Authorization: Bearer YOUR_TOKEN'"
echo ""
echo "4. Read the documentation:"
echo "   - README.md: API documentation"
echo "   - INTEGRATION.md: Integration guide"
echo "   - WEBHOOKS_FAQ.md: Troubleshooting"
echo ""

# Optional: Start backend automatically
read -p "Start backend server now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd apps/backend
    echo -e "${GREEN}Starting backend...${NC}"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
