# ✅ SPRINT 3 ACTION CHECKLIST

**Start Date:** [Today]
**Target Completion:** Viernes Semana 7
**Status:** READY TO KICKOFF

---

## 🎯 PRE-SPRINT SETUP (Today - 1 hour)

### System Check
- [ ] Verify Sprint 2 (Tier 2) is merged to main
  ```bash
  git log --oneline main | grep -i "sprint 2\|tier 2"
  ```

- [ ] All Tier 1 & 2 modules exist
  ```bash
  ls -la apps/ | grep -E "identity|pos|invoicing|inventory|sales|accounting|finance|hr|e_invoicing"
  ```

- [ ] Database is clean and migrated
  ```bash
  # Check migrations are up to date
  alembic current
  ```

- [ ] Tests pass for Tier 1 & 2
  ```bash
  pytest apps/identity apps/pos -v --tb=short
  ```

### Create Sprint 3 Branch
- [ ] Create feature branch
  ```bash
  git checkout -b sprint-3-tier3
  git pull origin main
  ```

- [ ] Create module directories
  ```bash
  mkdir -p apps/backend/app/modules/webhooks/{domain,application,interface/http,infrastructure/{,channels}}
  mkdir -p apps/notifications/{domain,application,interface/http,infrastructure}
  mkdir -p apps/reconciliation/{domain,application,interface/http,infrastructure}
  mkdir -p apps/reports/{domain,application,interface/http,infrastructure}
  ```

### Setup Environment
- [ ] Install Redis locally
  ```bash
  # Windows: choco install redis-64
  # Or: docker run -d -p 6379:6379 redis:latest
  ```

- [ ] Test Redis connection
  ```bash
  redis-cli ping
  # Should return: PONG
  ```

- [ ] Add env variables
  ```env
  SENDGRID_API_KEY=sg-...
  REDIS_URL=redis://localhost:6379/0
  WEBHOOK_SECRET_KEY=your-secret-key
  NOTIFICATION_FROM_EMAIL=noreply@gestiqcloud.com
  ```

- [ ] Install dependencies
  ```bash
  pip install redis celery sendgrid openpyxl reportlab
  ```

---

## 📦 SEMANA 6: WEBHOOKS MODULE (Monday-Friday)

### LUNES: Webhooks Domain & Schemas

**Tasks:**
- [ ] Create `apps/backend/app/modules/webhooks/domain/models.py`
  - [ ] WebhookSubscription model
  - [ ] WebhookDelivery model
  - [ ] EventType enum (20+ event types)
  - [ ] Add database migrations

- [ ] Create `apps/backend/app/modules/webhooks/domain/events.py`
  - [ ] WebhookEvent base class
  - [ ] Specific event classes (InvoiceCreated, etc.)

- [ ] Create `apps/backend/app/modules/webhooks/domain/exceptions.py`
  - [ ] Custom exceptions

- [ ] Create `apps/backend/app/modules/webhooks/application/schemas.py`
  - [ ] CreateWebhookRequest
  - [ ] WebhookResponse
  - [ ] DeliveryResponse

**Checklist:**
- [ ] All models have proper docstrings
- [ ] Type hints 100%
- [ ] Enum covers all event types
- [ ] Migrations created
- [ ] Database tables created

**Testing:**
```bash
# Verify models
python -c "from app.modules.webhooks.domain.models import WebhookSubscription; print('OK')"

# Run migrations
alembic upgrade head
```

---

### MARTES: Webhooks Use Cases & Endpoints

**Tasks:**
- [ ] Create `apps/backend/app/modules/webhooks/application/use_cases.py` (8 use cases)
  - [ ] CreateWebhookSubscriptionUseCase
  - [ ] UpdateWebhookSubscriptionUseCase
  - [ ] DeleteWebhookSubscriptionUseCase
  - [ ] ListWebhooksUseCase
  - [ ] TriggerWebhookEventUseCase
  - [ ] GetWebhookDeliveryHistoryUseCase
  - [ ] RetryFailedDeliveryUseCase
  - [ ] TestWebhookSubscriptionUseCase

- [ ] Create `apps/backend/app/modules/webhooks/interface/http/tenant.py` (6 endpoints)
  - [ ] POST   /webhooks
  - [ ] GET    /webhooks
  - [ ] PUT    /webhooks/{id}
  - [ ] DELETE /webhooks/{id}
  - [ ] GET    /webhooks/{id}/history
  - [ ] POST   /webhooks/{id}/test

- [ ] Register router in `main.py`
  ```python
  from app.modules.webhooks.interface.http.tenant import router as webhooks_router
  app.include_router(webhooks_router)
  ```

**Checklist:**
- [ ] All use cases have docstrings
- [ ] All endpoints have examples
- [ ] Type hints 100%
- [ ] Endpoints accessible in Swagger
- [ ] Manual test with Postman

**Testing:**
```bash
curl -X GET http://localhost:8000/webhooks \
  -H "Authorization: Bearer <token>"

curl -X POST http://localhost:8000/webhooks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "invoice.created",
    "target_url": "https://example.com/webhook",
    "secret": "test-secret-123"
  }'
```

---

### MIÉRCOLES-JUEVES: Webhooks Infrastructure & Delivery

**Tasks:**
- [ ] Create `apps/backend/app/modules/webhooks/infrastructure/delivery.py`
  - [ ] WebhookDeliveryService class
  - [ ] HMAC-SHA256 signing
  - [ ] Exponential backoff retry logic
  - [ ] Async HTTP delivery with httpx

- [ ] Create `apps/backend/app/modules/webhooks/infrastructure/event_queue.py`
  - [ ] WebhookEventQueue class (Redis)
  - [ ] enqueue() method
  - [ ] dequeue() method
  - [ ] queue_size() method

- [ ] Create `apps/backend/app/modules/webhooks/infrastructure/repository.py`
  - [ ] WebhookRepository class
  - [ ] CRUD methods for subscriptions
  - [ ] Query by event_type
  - [ ] Delivery history queries

- [ ] Create `apps/backend/app/modules/webhooks/infrastructure/providers.py`
  - [ ] Dependency injection providers
  - [ ] Service instances

- [ ] Create __init__.py files
  - [ ] `apps/backend/app/modules/webhooks/__init__.py`
  - [ ] `apps/backend/app/modules/webhooks/domain/__init__.py`
  - [ ] `apps/backend/app/modules/webhooks/application/__init__.py`
  - [ ] `apps/backend/app/modules/webhooks/interface/__init__.py`
  - [ ] `apps/backend/app/modules/webhooks/interface/http/__init__.py`
  - [ ] `apps/backend/app/modules/webhooks/infrastructure/__init__.py`

**Checklist:**
- [ ] HMAC signing tested with known values
- [ ] Retry schedule correct (1s, 2s, 4s, 8s, 16s)
- [ ] Redis integration working
- [ ] All database queries working
- [ ] Type hints 100%

**Testing:**
```bash
# Test HMAC signing
python -c "
from app.modules.webhooks.infrastructure.delivery import WebhookDeliveryService
svc = WebhookDeliveryService()
sig = svc._sign_payload({'test': 'data'}, 'secret')
print(f'Signature: {sig}')
"

# Test Redis
python -c "
from app.modules.webhooks.infrastructure.event_queue import WebhookEventQueue
q = WebhookEventQueue()
size = q.queue_size()
print(f'Queue size: {size}')
"
```

---

### VIERNES: Webhooks Testing & Integration

**Tasks:**
- [ ] Create comprehensive tests
  ```
  tests/webhooks/
  ├─ test_models.py
  ├─ test_use_cases.py
  ├─ test_endpoints.py
  ├─ test_delivery.py
  └─ test_integration.py
  ```

- [ ] Manual testing scenarios
  - [ ] Create webhook subscription
  - [ ] Trigger event
  - [ ] Verify delivery received
  - [ ] Test HMAC signature verification
  - [ ] Test retry logic
  - [ ] Test history endpoint

- [ ] Integration with other modules
  - [ ] Add event trigger to invoice creation
  - [ ] Add event trigger to receipt creation
  - [ ] Add event trigger to payment received
  - [ ] Test end-to-end flow

- [ ] Code cleanup
  ```bash
  black apps/backend/app/modules/webhooks
  ruff check apps/backend/app/modules/webhooks --fix
  mypy apps/backend/app/modules/webhooks --ignore-missing-imports
  ```

- [ ] Commit and push
  ```bash
  git add apps/backend/app/modules/webhooks
  git commit -m "feat(webhooks): Full webhook system with HMAC + retry logic"
  git push origin sprint-3-tier3
  ```

**Checklist:**
- [ ] All tests pass
  ```bash
  pytest apps/backend/tests/test_webhooks.py -v --cov=app.modules.webhooks
  ```
- [ ] Code quality
  ```bash
  ruff check apps/backend/app/modules/webhooks
  black --check apps/backend/app/modules/webhooks
  ```
- [ ] Type checking
  ```bash
  mypy apps/backend/app/modules/webhooks
  ```
- [ ] Swagger docs complete
- [ ] Manual testing recorded in TESTING_LOG.md

---

## 📦 SEMANA 6 NEXT: NOTIFICATIONS MODULE (Wed-Fri of Week 6)

*[Same pattern as webhooks]*

**Quick Timeline:**
- [ ] MIÉRCOLES: Domain + Schemas + Use Cases
- [ ] JUEVES: Endpoints + Infrastructure
- [ ] VIERNES: Testing + Integration + Cleanup

---

## 📊 SEMANA 7: RECONCILIATION + REPORTS

*[Follow same checklist pattern]*

### LUNES-MARTES: Reconciliation
- [ ] Models
- [ ] Schemas
- [ ] Use cases (7)
- [ ] Endpoints (5)
- [ ] Matching algorithm
- [ ] Tests

### MIÉRCOLES-VIERNES: Reports
- [ ] Models
- [ ] Generators (6 report types)
- [ ] Exporters (Excel, PDF, CSV)
- [ ] Use cases (6)
- [ ] Endpoints (7)
- [ ] Tests

---

## 🧪 DAILY COMMIT PATTERN

```
# Lunes AM: Domain + Schemas
git commit -m "feat(webhooks): domain models and schemas"

# Lunes PM: Use cases
git commit -m "feat(webhooks): business logic use cases"

# Martes AM: Endpoints
git commit -m "feat(webhooks): FastAPI endpoints"

# Martes PM: Infrastructure
git commit -m "feat(webhooks): delivery service + Redis queue"

# Miércoles AM: Tests
git commit -m "test(webhooks): comprehensive test suite"

# Miércoles PM: Integration + Cleanup
git commit -m "feat(webhooks): integrate with other modules + cleanup"

# Viernes: Ready for PR
git commit -m "doc(webhooks): complete documentation"
```

---

## 🎯 SPRINT 3 COMPLETION CRITERIA

When all below are ✓, SPRINT 3 is COMPLETE:

### Code Quality
- [ ] Black formatting: 100%
- [ ] Ruff: 0 errors
- [ ] Mypy: 0 errors
- [ ] Type hints: 100%
- [ ] Docstrings: 100% (Google style)

### Functionality
- [ ] 4 modules implemented (Webhooks, Notifications, Reconciliation, Reports)
- [ ] All endpoints working
- [ ] All use cases tested
- [ ] Integration tests pass
- [ ] Manual E2E testing complete

### Database
- [ ] Migrations created and tested
- [ ] Models verified
- [ ] Queries optimized
- [ ] No N+1 queries

### Documentation
- [ ] README for each module
- [ ] API endpoint examples
- [ ] Postman collection updated
- [ ] Architecture diagrams
- [ ] Troubleshooting guide

### Integration
- [ ] Event triggers added to Tier 1 modules
- [ ] Webhooks triggering correctly
- [ ] Notifications sending correctly
- [ ] Reports generating correctly
- [ ] Reconciliation matching working

### Testing
- [ ] Unit tests: >80% coverage
- [ ] Integration tests: 100% scenarios
- [ ] E2E tests: 10+ flows
- [ ] Manual testing: All pass

### Deployment
- [ ] All merges to staging branch
- [ ] Staging environment verified
- [ ] Performance acceptable
- [ ] Monitoring configured
- [ ] Ready for SPRINT 4

---

## 📋 DAILY STATUS LOG

### SEMANA 6

**LUNES:**
- [ ] Webhooks domain models created
- [ ] Database migrations done
- [ ] Endpoints skeleton ready
- Status: ░░░░░░░░░░

**MARTES:**
- [ ] Use cases implemented (8)
- [ ] Endpoints working (6)
- [ ] Manual Postman testing done
- Status: ██░░░░░░░░

**MIÉRCOLES:**
- [ ] Infrastructure layer complete
- [ ] Delivery service + retry logic
- [ ] Redis queue integrated
- Status: ████░░░░░░

**JUEVES:**
- [ ] Tests passing
- [ ] Code quality clean
- [ ] Integration complete
- Status: ██████░░░░

**VIERNES:**
- [ ] Notifications module started
- [ ] Merged to staging
- [ ] Ready for next week
- Status: ████████░░

### SEMANA 7

**LUNES-MARTES:**
- [ ] Reconciliation complete
- [ ] Matching algorithm working
- Status: ██████████

**MIÉRCOLES-VIERNES:**
- [ ] Reports complete
- [ ] All exports working
- [ ] System ready for SPRINT 4
- Status: ██████████

---

## 🚀 END OF SPRINT 3

Final checklist before moving to SPRINT 4:

- [ ] All 4 modules merged to main
- [ ] Staging environment verified
- [ ] Performance benchmarks met
- [ ] No critical bugs
- [ ] Documentation complete
- [ ] Team ready for SPRINT 4
- [ ] Commit message: "SPRINT 3 COMPLETE: All Tier 3 modules"

```bash
# Final merge
git checkout main
git pull origin main
git merge --no-ff sprint-3-tier3
git push origin main
```

---

**You've got this!** 🔥 Execute this checklist methodically and SPRINT 3 will be DONE.

Questions? Check the specific guides:
- Webhooks: SPRINT_3_WEBHOOKS_GUIDE.md
- Notifications: SPRINT_3_NOTIFICATIONS_GUIDE.md (create next)
- Reconciliation: SPRINT_3_RECONCILIATION_GUIDE.md (create next)
- Reports: SPRINT_3_REPORTS_GUIDE.md (create next)
