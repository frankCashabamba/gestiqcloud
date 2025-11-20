# Migration: 2025-11-19_903_add_parser_fields

## Description
Adds parser configuration fields to `import_batches` table:
- `parser_id` (VARCHAR): ID of the parser used
- `parser_choice_confidence` (NUMERIC): Confidence score for parser selection
- `suggested_parser` (VARCHAR): Suggested parser name
- `classification_confidence` (NUMERIC): Confidence score for classification
- `ai_enhanced` (BOOLEAN): Whether AI enhancement was used
- `ai_provider` (VARCHAR): AI provider name (OpenAI, Anthropic, etc.)
- `updated_at` (TIMESTAMPTZ): Last update timestamp

## Tables Modified
- `import_batches`: Added 7 new columns

## Backward Compatibility
- All new columns are nullable except `ai_enhanced` (default FALSE)
- Existing data will continue to work

## Testing
```sql
SELECT COUNT(*) FROM import_batches WHERE parser_id IS NOT NULL;
```
