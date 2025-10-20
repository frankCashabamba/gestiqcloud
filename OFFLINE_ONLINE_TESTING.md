# Offline/Online Testing Guide

This guide explains how to test the ElectricSQL offline/online functionality in GESTIQCLOUD.

## Overview

The offline/online system allows the PWA to work without internet connection and automatically sync when connectivity is restored. It includes:

- **Local Database**: PGlite stores data locally in the browser
- **Sync Engine**: ElectricSQL handles bidirectional sync with conflict resolution
- **Conflict Resolution**: Automatic resolution with manual intervention when needed
- **Audit Trail**: All sync operations and conflicts are logged

## Test Structure

### Backend Tests
- **Unit Tests**: `apps/backend/app/tests/test_electric_conflicts.py`
  - Conflict resolution logic
  - Different strategies per entity type
  - Edge cases and error handling

### Frontend Tests
- **Unit Tests**: `apps/tenant/src/lib/__tests__/electric.test.ts`
  - ElectricSQL initialization
  - Online/offline event handling
  - Conflict callback system

- **Integration Tests**: `apps/tenant/src/__tests__/offline-online.integration.test.ts`
  - Full offline/online workflows
  - POS operations offline
  - Sync on reconnection
  - Conflict UI interaction

### Manual Testing Script
- **Automated Tests**: `scripts/test_offline_online.py`
  - Backend endpoint validation
  - Conflict resolution simulation
  - Database table verification

## Running Tests

### Prerequisites
1. **Backend running**: `docker compose up`
2. **Frontend dependencies**: `cd apps/tenant && npm install`
3. **Database migrated**: ElectricSQL tables should exist

### Backend Tests
```bash
# Unit tests
python -m pytest apps/backend/app/tests/test_electric_conflicts.py -v

# With coverage
python -m pytest apps/backend/app/tests/test_electric_conflicts.py --cov=app.modules.electric_conflicts
```

### Frontend Tests
```bash
cd apps/tenant

# Unit tests
npm test src/lib/__tests__/electric.test.ts

# Integration tests
npm test src/__tests__/offline-online.integration.test.ts

# All ElectricSQL tests
npm test -- --testPathPattern="electric|offline-online"
```

### Manual Testing Script
```bash
# Run all automated tests
python scripts/test_offline_online.py

# Or run individual components
python -c "from scripts.test_offline_online import OfflineOnlineTester; t = OfflineOnlineTester(); t.test_shapes_endpoint()"
```

## Manual Testing Scenarios

### 1. Basic Offline/Online Flow
1. **Open the PWA** in browser with DevTools open
2. **Go offline**: Network tab → Offline checkbox
3. **Make changes**: Create products, receipts, etc.
4. **Check local storage**: Application tab → IndexedDB
5. **Go online**: Uncheck Offline in Network tab
6. **Verify sync**: Check network requests to `/api/v1/electric/sync-status`

### 2. Conflict Simulation
1. **Setup two browser windows** (or devices)
2. **Modify same data** in both while offline
3. **Connect both online**
4. **Check conflict resolution** in network logs
5. **Verify UI** shows conflict modal if manual resolution needed

### 3. POS Offline Operation
1. **Go offline** in POS interface
2. **Create receipts** (should work offline)
3. **Check outbox indicator** shows pending sync
4. **Go online** and verify receipts sync to server

## Testing Conflict Scenarios

### Automatic Resolution
- **Stock changes**: Last Write Wins
- **Receipt conflicts**: Duplicate creation
- **Safe product changes**: Merge

### Manual Resolution Required
- **Price conflicts**: User chooses local/remote/merge
- **Critical data conflicts**: Admin intervention

## Debugging

### Common Issues
1. **ElectricSQL not initializing**: Check browser IndexedDB support
2. **Sync failing**: Verify backend Electric shapes endpoint
3. **Conflicts not resolving**: Check conflict resolver logic
4. **UI not showing conflicts**: Verify ConflictResolver component mounting

### Debug Tools
- **Browser DevTools**: Network tab for sync requests
- **Application Tab**: IndexedDB for local data
- **Console Logs**: ElectricSQL initialization messages
- **Backend Logs**: Conflict resolution details

### Logs to Check
```bash
# Backend logs
docker logs backend | grep -i electric

# Frontend console
# Look for "ElectricSQL initialized" messages
```

## Performance Testing

### Sync Performance
- **Large datasets**: Test with 1000+ records
- **Slow connections**: Use Network tab throttling
- **Memory usage**: Monitor browser memory during sync

### Conflict Resolution Scale
- **Multiple conflicts**: Test with 10+ simultaneous conflicts
- **Complex conflicts**: Nested foreign key relationships

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# In GitHub Actions
- name: Run ElectricSQL tests
  run: |
    python scripts/test_offline_online.py
    cd apps/tenant && npm test -- --testPathPattern="electric"
```

## Monitoring

### Key Metrics
- **Sync success rate**: % of sync operations that complete
- **Conflict rate**: % of syncs with conflicts
- **Resolution time**: Time to resolve conflicts
- **Data consistency**: Verification of data integrity post-sync

### Alerts
- High conflict rate (>5%)
- Sync failures (>1%)
- Manual conflicts pending (>0 for extended periods)

## Troubleshooting

### Backend Issues
- **Shapes endpoint 404**: Check router registration
- **Conflict resolution errors**: Verify ConflictResolver logic
- **Database locks**: Check transaction handling

### Frontend Issues
- **Electric init fails**: Check PGlite WASM loading
- **Sync not triggering**: Verify online/offline event listeners
- **Conflict UI not showing**: Check React component mounting

## Future Enhancements

### Planned Tests
- **Multi-device sync**: Test with multiple browser tabs
- **Network interruption**: Simulate connection drops during sync
- **Large dataset sync**: Performance with 10k+ records
- **Real-time collaboration**: Multiple users editing same data

### Monitoring Improvements
- **Sync analytics**: Track sync performance metrics
- **Conflict analytics**: Analyze conflict patterns
- **User experience**: Measure time to sync completion
