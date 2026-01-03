# Cognito Test Improvements

Issues identified from comprehensive test suite review (Jan 2, 2026).

---

## 🔴 Critical Priority: Offline-First Testing

### FE-001: Add offline sync behavior tests
**File:** `frontend/tests/lib/sync.test.ts`

- [ ] Test queuing changes when `navigator.onLine` is false
- [ ] Test sync trigger when `online` event fires
- [ ] Test pending queue persistence across page reload
- [ ] Test sync API timeout handling
- [ ] Test accurate pending count during offline periods

### FE-002: Add storage/persistence tests
**File:** `frontend/tests/lib/db.test.ts`

- [ ] Test storage quota exceeded error handling
- [ ] Test behavior when IndexedDB is unavailable
- [ ] Test data persistence across browser restart

### BE-001: Add extended offline sync tests
**File:** `backend/tests/test_sync.py`

- [ ] Test client reconnection after extended offline period
- [ ] Test stale data reconciliation
- [ ] Test processing large pending change queues (100+ changes)

---

## 🟠 High Priority

### BE-002: Add user-defined category validation tests
**File:** `backend/tests/test_goals.py`

- [ ] Test any user-defined category string is accepted
- [ ] Test special characters in category (sanitization)
- [ ] Test max length enforcement for category names
- [ ] Test empty category handling

### FE-003: Add offline status store tests
**File:** `frontend/tests/lib/stores.test.ts`

- [ ] Test offline status indication accuracy
- [ ] Test pending change count updates
- [ ] Test store state sync with network status

---

## 🟡 Medium Priority

### BE-003: Add LLM timeout tests
**File:** `backend/tests/test_llm.py`

- [ ] Test request timeout handling
- [ ] Test behavior when network is slow/unavailable

### BE-004: Prepare version restore tests (future feature)
**File:** `backend/tests/test_entry_versions.py`

- [ ] Test restore entry content from version snapshot
- [ ] Test restore creates new version (doesn't overwrite history)
- [ ] Test conversations properly restored from snapshot

---

## 🟢 Low Priority

### BE-005: Add CSRF state parameter validation
**File:** `backend/tests/test_auth.py`

- [ ] Test state parameter in OAuth flow
- [ ] Test rejection of mismatched state

### BE-006: Add config validation tests
**File:** `backend/tests/test_config.py`

- [ ] Test invalid environment values (non-integer for `JWT_EXPIRY_HOURS`)
- [ ] Test missing required fields behavior

---

## Summary

| Priority | Count | Area |
|----------|-------|------|
| 🔴 Critical | 3 | Offline-first |
| 🟠 High | 2 | Category validation, stores |
| 🟡 Medium | 2 | LLM timeout, version restore |
| 🟢 Low | 2 | Auth CSRF, config validation |
