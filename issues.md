# Cognito Test Improvements

Issues identified from comprehensive test suite review (Jan 2, 2026).

---

## 🔴 Critical Priority: Offline-First Testing ✅

> Completed Jan 3, 2026

### FE-001: Add offline sync behavior tests ✅
**File:** `frontend/tests/lib/sync.test.ts`

- [x] Test queuing changes when `navigator.onLine` is false
- [x] Test sync trigger when `online` event fires
- [x] Test pending queue persistence across page reload
- [x] Test sync API timeout handling
- [x] Test accurate pending count during offline periods

### FE-002: Add storage/persistence tests ✅
**File:** `frontend/tests/lib/db.test.ts`

- [x] Test storage quota exceeded error handling
- [x] Test behavior when IndexedDB is unavailable
- [x] Test data persistence across browser restart

### BE-001: Add extended offline sync tests ✅
**File:** `backend/tests/test_sync.py`

- [x] Test client reconnection after extended offline period
- [x] Test stale data reconciliation
- [x] Test processing large pending change queues (100+ changes)

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

| Priority | Count | Area | Status |
|----------|-------|------|--------|
| 🔴 Critical | 3 | Offline-first | ✅ Complete |
| 🟠 High | 2 | Category validation, stores | |
| 🟡 Medium | 2 | LLM timeout, version restore | |
| 🟢 Low | 2 | Auth CSRF, config validation | |

