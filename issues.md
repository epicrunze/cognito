## 🔴 Critical Priority: LLM Sync Processing

### BE-007: Move pending message processing to background task
**Files:** `backend/app/routers/sync.py`, `backend/app/services/sync.py`, `backend/app/services/llm.py`

**Problem:** The sync endpoint waits for ALL pending LLM messages to be processed before returning. This causes:
- Client requests to block for 20-50+ seconds if multiple messages are queued
- HTTP timeout risks with many pending messages
- App appears frozen to users during sync
- 429 rate limit errors cascade since failed messages retry every sync

**Root Cause:**
- `process_pending_messages()` is called with `await` in the sync handler (line 117 in sync.py)
- Failed LLM calls keep `pending_response: true`, causing retries on every sync
- No rate limiting between LLM calls
- No max limit on messages processed per sync

**Proposed Solution (Background Task):**
- [ ] Move `process_pending_messages()` to a FastAPI `BackgroundTask`
- [ ] Sync endpoint returns immediately, pending messages processed async
- [ ] Add rate limiting: 200ms delay between LLM calls
- [ ] Add max messages per batch: 5 messages, then yield
- [ ] Add retry count tracking: mark as `failed` after 3 attempts
- [ ] Add exponential backoff to `GeminiClient` for 429 errors
- [ ] Add separate endpoint `/api/chat/pending-status` to check processing status
- [ ] Frontend polls for status or receives update via server changes on next sync

**Alternative Quick Fix (Cap per sync):**
- [ ] Limit to 2-3 messages per sync cycle
- [ ] Return remaining count in response for frontend awareness

### ✅ BE-008: Unify sync pending message processing with chat module
**Status:** COMPLETE (2026-01-04)

**Files Changed:**
- `backend/app/services/chat.py` (new) - Unified ChatService with retry logic
- `backend/app/models/entry.py` - Added `pending_refine`, `refine_status`, `refine_error` fields
- `backend/app/database.py` - Added columns to entries table
- `backend/app/repositories/entry_repo.py` - Added refine helper functions
- `backend/app/services/sync.py` - Delegates to ChatService, added `process_pending_refines()`
- `backend/app/routers/chat.py` - Delegates to ChatService, added queue/status endpoints

**New API Endpoints:**
- `POST /api/chat/refine/queue` - Queue entry for background refinement
- `GET /api/chat/refine/status?entry_id=...` - Poll refine status

**Completed:**
- [x] Extract shared chat processing logic into `ChatService` class
- [x] Move `process_pending_messages()` to use `ChatService`
- [x] Chat router delegates to `ChatService` for consistency
- [x] Add `pending_refine` support for offline refine operations
- [x] Add refine queue/status endpoints
- [x] All 162 backend tests passing

**Follow-up:** See FE-004 for frontend integration

### BE-009: Add LLM request logging service
**Files:** `backend/app/models/llm_log.py` (new), `backend/app/repositories/llm_log_repo.py` (new), `backend/app/services/llm.py`, `backend/app/routers/llm_logs.py` (new), `frontend/src/routes/llm-logs/+page.svelte` (new)

**Problem:** No visibility into LLM API usage per user. Cannot track:
- How many requests each user makes
- Which operations (chat vs refine) consume most tokens
- Error rates and latency patterns
- Potential abuse or runaway requests

**Proposed Solution:**

**Backend:**
- [ ] Create `llm_logs` table (user_id, provider, model, operation_type, latency_ms, status, error_message, created_at)
- [ ] Create Pydantic models: `LLMLog`, `LLMLogCreate`, `LLMLogStats`
- [ ] Create `llm_log_repo` with CRUD and stats aggregation
- [ ] Modify `LLMRouter.generate()` to accept optional `user_id`/`conn` for auto-logging
- [ ] Add REST endpoints: `GET /llm-logs`, `GET /llm-logs/stats`
- [ ] Add unit tests for logging functionality

**Frontend:**
- [ ] Create API client for `/llm-logs` endpoints
- [ ] Create LLM logs store
- [ ] Create `/llm-logs` dashboard page with stats cards and log table
- [ ] Add filtering by provider, operation type, date range

**Benefits:**
- Monitor per-user LLM usage
- Identify unnecessary/duplicate requests
- Debug LLM errors with full context
- Potential for usage quotas or alerts

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

### FE-004: Add ability to delete entries
**Files:** `frontend/src/routes/(app)/entries/[id]/+page.svelte`, `backend/app/api/entries.py`

- [ ] Add delete button to entry detail page
- [ ] Add confirmation dialog before deletion
- [ ] Implement frontend delete API call
- [ ] Add backend DELETE `/api/entries/{id}` endpoint
- [ ] Handle offline deletion (queue for sync)
- [ ] Add cascade delete for entry versions and conversations
- [ ] Add tests for delete functionality

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

## Frontend Issues

### FE-004: Integrate refine status polling with frontend
**Files:** `frontend/src/lib/api/chat.ts`, `frontend/src/lib/stores/entries.ts`, `frontend/src/routes/entry/[id]/+page.svelte`

**Depends on:** BE-008 (complete)

**Problem:** Backend now supports queued refine operations with status tracking, but frontend doesn't utilize this feature.

**New Backend Endpoints (from BE-008):**
- `POST /api/chat/refine/queue` - Queue entry for refinement
- `GET /api/chat/refine/status?entry_id=...` - Returns `{pending_refine, refine_status, refine_error}`

**Proposed Solution:**
- [ ] Add API client functions for queue and status endpoints
- [ ] Add refine status to entry store
- [ ] Show refine status indicator in entry view (pending/processing/completed/failed)
- [ ] Add "Queue for Refine" button when offline
- [ ] Poll status while `refine_status === 'processing'`
- [ ] Display error message if `refine_status === 'failed'`

**Benefits:**
- Users can queue refines offline and see progress
- Better UX with status feedback
- Prevents accidental double-refinement

---

### FE-005: Journal entries not syncing from other devices
**Files:** `frontend/src/lib/stores/entries.ts`, `frontend/src/lib/api/entries.ts`, `frontend/src/lib/sync/`

**Problem:** After reopening the app, journal entries created on another device do not appear in the entries list. Goals sync correctly, indicating the sync mechanism works but entries are not being pulled/merged properly.

**Observed Behavior:**
- Entries created on Device A are visible on backend
- Goals sync correctly between devices
- After reopening app on Device B, new entries from Device A don't appear

**Investigation Areas:**
- [ ] Verify entries sync endpoint returns all user entries (not just local)
- [ ] Check if entries store merges server data correctly on app init
- [ ] Confirm `lastSyncTimestamp` for entries is being used correctly
- [ ] Compare entries sync logic vs goals sync logic for differences
- [ ] Check if entries are filtered incorrectly (e.g., by `device_id` or `local_id`)

**Potential Fixes:**
- [ ] Ensure full entries fetch on app startup (not delta-only)
- [ ] Fix merge logic to add server-only entries to local store
- [ ] Add logging to debug sync flow for entries

---

## Summary

| Priority | Count | Area | Status |
|----------|-------|------|--------|
| 🔴 Critical | 4+3 | Offline-first, LLM sync, chat unification, LLM logging | ✅ 4 Complete, 3 Open |
| 🟠 High | 3 | Category validation, stores, delete entries | |
| 🟡 Medium | 2 | LLM timeout, version restore | |
| 🟢 Low | 2 | Auth CSRF, config validation | |
| 🔵 Frontend | 1 | FE-004 refine status | New |

