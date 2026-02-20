# 4 SPRINTS - COMPLETE ARCHITECTURE

## Files Created (50+ Python modules)

### Domain Layer (Interfaces)
```
domain/
├── __init__.py
└── interfaces.py (DocType, ConfidenceLevel, ItemStatus, etc.)
```

### Application Layer (Core Business Logic)
```
application/
├── __init__.py
├── smart_router.py          (SPRINT 1) - Main orchestrator
├── adapters.py              (SPRINT 1) - Parser wrappers
├── ingest_service.py        (SPRINT 1) - Batch/item management
├── scoring_engine.py        (SPRINT 2) - Hybrid classifier
├── canonical_mapper.py      (SPRINT 2) - Field mapping
├── quality_gates.py         (SPRINT 2) - QA checks
├── observability.py         (SPRINT 2) - Metrics & rollback
└── learning_loop.py         (SPRINT 4) - Active learning
```

### Infrastructure Layer (External Services)
```
infrastructure/
├── __init__.py
├── country_packs.py         (SPRINT 3) - EC, ES, PE, MX, BR
├── validators.py            (SPRINT 3) - Doc type validators
└── learning_store.py        (SPRINT 4) - Correction tracking
```

### Configuration
```
config/
├── __init__.py
└── aliases.py               - Field aliases (ES, EN, PT)
```

### Routes (API Endpoints)
```
routes/
├── __init__.py
├── analysis.py              - Classification endpoints
├── country.py               - Country config endpoints
├── learning.py              - Learning endpoints
└── v2_batch_migration.py    - Legacy compatibility
```

### Scripts (Setup & Examples)
```
scripts/
├── __init__.py
├── sprint1_setup.py         - Router + parsers + validators
├── sprint2_setup.py         - Scoring + metrics + rollback
├── sprint3_setup.py         - Country registry + validators
└── sprint4_setup.py         - Learning pipeline
```

### API Integration
```
api_v2.py                     - FastAPI router aggregation
examples_sprints.py           - Usage examples
```

### Tests
```
tests/test_sprints_integration.py
├── TestSprint1Foundation
├── TestSprint2Scoring
├── TestSprint3CountryPacks
└── TestSprint4Learning
```

## SPRINT 1: Foundation (Stabilization)

### Goals
- Encapsulate parsers in common adapter interface
- Consolidate classification in smart_router
- Standardize doc_type and aliases
- Clear ingest (soft) vs promote (strict) flow

### Components
- **SmartRouter**: Central orchestrator
- **ParserAdapter**: Interface for all parsers
- **BatchStatus**: PENDING → INGESTED → CLASSIFIED → MAPPED → PROMOTED
- **ItemStatus**: PENDING → VALIDATED → NEEDS_REVIEW/PROMOTED/REJECTED

### Key Classes
```python
SmartRouter()
  .ingest(file_path, hinted_doc_type)     → ParseResult
  .classify(raw_data, parser_id)          → AnalyzeResult
  .map(raw_data, doc_type)                → MappingResult
  .validate(data, doc_type)               → List[errors]
  .promote(analyze, mapping)              → (bool, reason)

IngestService()
  .create_batch(tenant_id, source_type, origin)
  .ingest_parse_result(batch_id, parse_result) → item_ids
  .update_item_after_classify(item_id, result)
  .update_item_after_map(item_id, result)
  .set_item_needs_review(item_id, reason)
  .record_correction(item_id, field, old, new)
```

## SPRINT 2: Classification & Confidence (Detection)

### Goals
- Hybrid classifier (rules + signals + OCR)
- Formal confidence score
- Decision policy: high→auto, medium→confirm, low→review
- Structural fingerprinting for learning

### Components
- **ScoringEngine**: Rule-based + semantic scoring
- **ConfidenceLevel**: HIGH (>0.8), MEDIUM (0.5-0.8), LOW (<0.5)
- **QualityGate**: Precision/recall thresholds
- **MetricsCollector**: KPIs per doc_type
- **RollbackManager**: Version control

### Key Classes
```python
ScoringEngine()
  .register_rule(doc_type, func)
  .register_semantic_signal(doc_type, keywords, weight)
  .classify(raw_data)                     → AnalyzeResult
  .score_with_explanation(raw_data)      → dict

CanonicalMapper()
  .register_field_mapping(doc_type, mapping)
  .register_validator(doc_type, validator)
  .map_fields(raw_data, doc_type)        → MappingResult

QualityGate(min_precision, min_recall)
  .evaluate(metrics)                      → (bool, message)
  .record_metrics(metrics)
  .get_trend()

MetricsCollector()
  .record_classification(doc_type, confidence, time, success, error)
  .get_metrics_summary()                  → dict
  .export_metrics()                       → List[Metric]

RollbackManager()
  .save_version(name, classifier, timestamp)
  .set_active_version(name)
  .rollback_to_version(name)
  .get_available_versions()
```

## SPRINT 3: Country Packs (Fiscal Rules)

### Goals
- Country-specific validators (tax_id, date, currency)
- Pluggable field aliases per language
- Tenant-level country configuration
- No hardcoded rules in core

### Components
- **CountryPackRegistry**: EC, ES, PE, MX, BR
- **BaseCountryPack**: Interface for country rules
- **StrictValidator**: Multi-level validation chain
- **FIELD_ALIASES**: ES/EN/PT dictionary

### Country Packs Available
- **EC** (Ecuador): RUC (10-13 digits), USD, DD/MM/YYYY
- **ES** (Spain): CIF/NIF, EUR, DD/MM/YYYY
- **PE** (Peru): RUC (11 digits), PEN, DD/MM/YYYY
- **MX** (Mexico): RFC, MXN, DD/MM/YYYY
- **BR** (Brazil): CPF/CNPJ, BRL, DD/MM/YYYY

### Key Classes
```python
CountryPackRegistry()
  .register(pack)
  .get(country_code)                      → CountryPack
  .list_all()                             → List[country_codes]

EcuadorPack/SpainPack/etc()
  .get_country_code()
  .get_currency()
  .validate_tax_id(tax_id)                → (bool, error?)
  .validate_date_format(date_str)         → (bool, error?)
  .validate_fiscal_fields(data)           → List[errors]
  .get_field_aliases()

StrictValidator(country_pack)
  .register_required_fields(doc_type, fields)
  .register_field_types(doc_type, types)
  .validate(data, doc_type)               → List[errors]
```

## SPRINT 4: Learning & Quality (Continuous Improvement)

### Goals
- Active learning from user corrections
- Automated benchmarking with regression dataset
- Quality gates in CI
- Metrics dashboard & rollback capability

### Components
- **ActiveLearning**: Correction tracking + retraining
- **IncrementalTrainer**: Weekly improvement tracking
- **CIQualityCheck**: Pre-merge validation
- **InMemoryLearningStore**: In-memory correction history
- **JsonFilelearningStore**: Persistent learning data

### Key Classes
```python
ActiveLearning(learning_store, classifier)
  .add_training_sample(data, correct_type, original_type, confidence)
  .should_retrain(min_samples)            → bool
  .retrain()                              → dict
  .get_training_stats()                   → dict
  .get_improvement_rate()                 → float

IncrementalTrainer()
  .schedule_training(frequency)
  .record_weekly_improvement(metric, value)
  .get_improvement_trend()                → dict
  .generate_training_report()             → dict

CIQualityCheck()
  .check_before_merge(classifier, dataset) → dict

InMemoryLearningStore()/JsonFilelearningStore(file_path)
  .record_correction(batch_id, item_idx, original, corrected, confidence)
  .get_misclassification_stats()          → dict
  .get_fingerprint_dataset()              → List[dict]
  .record_fingerprint(fingerprint, doc_type, raw_data)
```

## API Endpoints (Routes)

### Analysis Routes (/imports/analyze)
```
POST   /analyze                           - Analyze file + confidence
POST   /batch/{id}/classify               - Classify all items in batch
POST   /batch/{id}/map                    - Map fields for all items
POST   /batch/{id}/promote                - Promote items to target tables
```

### Country Routes (/country-rules)
```
GET    /available                         - List available countries
GET    /{country_code}                    - Get country rules
POST   /{country_code}/validate-tax-id    - Validate tax ID
POST   /{country_code}/validate-date      - Validate date format
POST   /{country_code}/validate-fiscal    - Full fiscal validation
POST   /{tenant_id}/configure/{country}   - Set country for tenant
```

### Learning Routes (/learning)
```
POST   /correction/{batch_id}/{item_idx}  - Record user correction
GET    /stats/misclassifications          - Get error stats
GET    /dataset/fingerprints              - Get training fingerprints
GET    /corrections/{batch_id}            - Get corrections for batch
POST   /fingerprint                       - Record fingerprint
```

### V2 Batch Routes (/api/v2/imports)
```
GET    /health                            - Health check
POST   /ingest/batch                      - Create new batch
GET    /batch/{id}/status                 - Get batch status
POST   /batch/{id}/ingest                 - Ingest file to batch
POST   /batch/{id}/process                - Process (classify + map)
GET    /stats                             - Global statistics
```

## Integration Steps

### 1. Register with FastAPI
```python
from app.modules.imports.api_v2 import router
app.include_router(router)
```

### 2. Initialize on Startup
```python
from app.modules.imports.scripts import sprint1_setup, sprint2_setup, sprint3_setup, sprint4_setup

router = sprint1_setup.setup_smart_router()
scoring = sprint2_setup.setup_scoring_engine_v2()
countries = sprint3_setup.setup_country_registry()
learning = sprint4_setup.setup_learning_pipeline(scoring)
```

### 3. Wrap Legacy Parsers
```python
from app.modules.imports.application.adapters import ExcelParserAdapter
from app.modules.imports.parsers.xlsx_invoices import parse_xlsx_invoices

adapter = ExcelParserAdapter("xlsx_invoices", DocType.INVOICE, parse_xlsx_invoices)
router.register_parser("xlsx_invoices", adapter)
```

### 4. Add Database Models
- `ImportBatch` table: id, tenant_id, source_type, status, created_at, etc.
- `ImportItem` table: id, batch_id, status, raw, normalized, errors, etc.
- `CorrectionLog` table: id, item_id, field, old_value, new_value, timestamp

## Status Flow Diagram

```
File Upload
    ↓
SmartRouter.ingest() → ParseResult
    ↓
IngestService.ingest_parse_result()
    ↓ Batch: PENDING → INGESTED
    ↓ Items: PENDING
    ↓
SmartRouter.classify() → AnalyzeResult
    ↓ Items: PENDING → VALIDATED
    ↓ Record: classification_confidence, classified_doc_type
    ↓
SmartRouter.map() → MappingResult
    ↓ Items: VALIDATED
    ↓ Record: normalized_data, mapped_fields, validation_errors
    ↓
[Decision Point]
    ├─ confidence=HIGH → AutoPromote
    ├─ confidence=MEDIUM → Confirm (NEEDS_REVIEW)
    └─ confidence=LOW → NEEDS_REVIEW
    ↓
SmartRouter.promote() → (bool, reason)
    ├─ Success → Items: PROMOTED
    └─ Fail → Items: NEEDS_REVIEW
    ↓
[User Review] → record_correction()
    ↓ ActiveLearning.add_training_sample()
    ↓ LearningStore.record_correction()
    ↓ (triggers retraining if > N samples)
```

## Performance Notes

- SmartRouter: O(1) parser lookup
- ScoringEngine: O(n) field scan + O(m) rules
- CountryPackRegistry: O(1) lookup
- Learning: Incremental updates, no blocking
- Metrics: Bucketed by doc_type

## Dependencies

- pydantic: Data validation
- fastapi: API framework
- (all existing importation deps)

No new external dependencies required.
