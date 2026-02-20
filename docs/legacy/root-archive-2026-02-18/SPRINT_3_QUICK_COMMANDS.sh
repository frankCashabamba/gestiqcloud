#!/bin/bash

# SPRINT 3: QUICK COMMAND REFERENCE
# Use these commands to get started immediately

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║           SPRINT 3: QUICK START COMMANDS                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Read documentation
echo "STEP 1: READ DOCUMENTATION"
echo "→ cat SPRINT_3_START_HERE.md"
echo ""

# Step 2: Navigate to backend
echo "STEP 2: NAVIGATE TO BACKEND"
echo "→ cd apps/backend"
echo ""

# Step 3: Apply database migrations
echo "STEP 3: APPLY DATABASE MIGRATIONS"
echo "→ alembic upgrade head"
echo ""

# Step 4: Start the server
echo "STEP 4: START SERVER (in new terminal)"
echo "→ uvicorn app.main:app --reload"
echo ""

# Step 5: Test webhooks endpoint (in another terminal)
echo "STEP 5: TEST WEBHOOKS ENDPOINT"
echo ""
echo "List webhooks:"
echo "  curl -X GET http://localhost:8000/api/v1/tenant/webhooks \\"
echo "    -H \"Authorization: Bearer YOUR_TOKEN\""
echo ""
echo "Create webhook:"
echo "  curl -X POST http://localhost:8000/api/v1/tenant/webhooks \\"
echo "    -H \"Authorization: Bearer YOUR_TOKEN\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{"
echo "      \"event_type\": \"invoice.created\","
echo "      \"target_url\": \"https://example.com/webhook\","
echo "      \"secret\": \"my-secret-key\""
echo "    }'"
echo ""

# Step 6: Code quality checks
echo "STEP 6: CODE QUALITY (run before committing)"
echo ""
echo "Format code:"
echo "  black apps/backend/app/modules/webhooks"
echo ""
echo "Check linting:"
echo "  ruff check apps/backend/app/modules/webhooks --fix"
echo ""
echo "Type checking:"
echo "  mypy apps/backend/app/modules/webhooks --ignore-missing-imports"
echo ""

# Step 7: Run tests
echo "STEP 7: RUN TESTS (optional)"
echo "→ pytest tests/webhooks/ -v --tb=short"
echo ""

# Step 8: Git workflow
echo "STEP 8: GIT WORKFLOW"
echo ""
echo "Create/switch to sprint branch:"
echo "  git checkout -b sprint-3-tier3"
echo ""
echo "After implementing webhooks:"
echo "  git add apps/backend/app/modules/webhooks"
echo "  git commit -m \"feat(webhooks): complete webhooks module\""
echo "  git push origin sprint-3-tier3"
echo ""
echo "After all modules done:"
echo "  git checkout main"
echo "  git pull origin main"
echo "  git merge sprint-3-tier3"
echo "  git push origin main"
echo ""

# Step 9: Implementation pattern for other modules
echo "STEP 9: IMPLEMENT OTHER MODULES (Notifications, Reconciliation, Reports)"
echo ""
echo "Follow the Webhooks pattern:"
echo "  1. Copy structure from apps/backend/app/modules/webhooks/"
echo "  2. Create domain layer (models, events, exceptions)"
echo "  3. Create application layer (schemas, use_cases)"
echo "  4. Create interface layer (interface/http/tenant.py)"
echo "  5. Create infrastructure layer (services, repository)"
echo "  6. Create database migration"
echo "  7. Register router in platform/http/router.py"
echo "  8. Test with Postman"
echo ""

# Step 10: Verification
echo "STEP 10: VERIFY EVERYTHING WORKS"
echo ""
echo "Check webhooks module loads:"
echo "  python -c \"from app.modules.webhooks.domain.models import WebhookSubscription; print('✅ Webhooks module ready')\""
echo ""
echo "Check all imports:"
echo "  python -c \"from app.modules.webhooks.interface.http.tenant import router; print('✅ All imports working')\""
echo ""

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                         YOU'RE READY TO GO!                               ║"
echo "║                                                                            ║"
echo "║  Next: Read SPRINT_3_START_HERE.md                                        ║"
echo "║  Then:  Run alembic upgrade head                                          ║"
echo "║  Then:  Test webhooks with Postman                                        ║"
echo "║  Then:  Build Notifications module (follow same pattern)                  ║"
echo "║                                                                            ║"
echo "║  Timeline: All 4 modules complete by Friday Semana 7                      ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
