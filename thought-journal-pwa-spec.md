# Thought Journal PWA

**Technical Specification & Implementation Plan**

Version 1.0 — December 2024

---

## 1. Executive Summary

A Progressive Web Application for conversational thought journaling with LLM integration. The system combines personal knowledge management with AI augmentation, featuring autonomous maintenance, proactive prompting via push notifications, and self-modifying capabilities.

**Core Value Proposition:** Capture thoughts conversationally with an LLM, receive proactive prompts to expand ideas, and let the system autonomously maintain and improve both your journal and its own codebase.

### 1.1 Key Features

- Conversational journaling with Gemini integration
- Push notification prompts based on goals and recent entries
- Scheduled agentic cleanup with user approval
- Offline-first with intelligent sync and code-based diff resolution
- Self-modifying codebase via integration with agentic coding tools
- HTTPS transport security with Google OAuth authentication

### 1.2 Technical Stack

- **Frontend:** SvelteKit PWA with IndexedDB (Dexie.js), Tailwind CSS v4, Skeleton UI v4
- **Backend:** FastAPI on Ubuntu with nginx reverse proxy
- **Database:** DuckDB
- **LLM:** Gemini API (primary), self-hosted Ollama (confidential data)
- **Hosting:** server.epicrunze.com

---

## 2. System Architecture

### 2.1 High-Level Overview

The system follows a client-server architecture with offline-first design. The PWA client handles local storage and user interactions, while the server manages LLM integrations, scheduled jobs, and acts as the source of truth when online.

#### 2.1.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                              PWA CLIENT                             │
├─────────────────────────────────────────────────────────────────────┤
│  Views: Journal | Chat | Proposals | Archive | Goals | Code Specs  │
│  IndexedDB: entries, pendingChanges, goals, settings               │
│  Service Worker: offline caching, push handling, background sync   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ HTTPS (encrypted)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    server.epicrunze.com                             │
│                    nginx → FastAPI → DuckDB                         │
├─────────────────────────────────────────────────────────────────────┤
│  API: /sync, /chat, /entries, /goals, /proposals, /code-specs      │
│  Jobs: notification generation, cleanup, auto-archive              │
│  LLM Router: Gemini API | Ollama (localhost:11434)                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Security Architecture

Security is handled through HTTPS for transport encryption and Google OAuth for authentication. This approach minimizes custom security code while leveraging battle-tested infrastructure.

#### 2.2.1 Security Layers

- **Transport:** TLS 1.3 via nginx (HTTPS) — encrypts all client-server communication
- **Authentication:** Google OAuth 2.0 — no passwords stored, Google handles identity
- **Authorization:** JWT tokens issued by your server after OAuth verification
- **Access Control:** Single-user mode — only your Google email is allowed

#### 2.2.2 Why This Approach

- HTTPS is sufficient for personal server where you control the infrastructure
- Google OAuth eliminates password storage, reset flows, and brute force concerns
- Custom encryption would be bypassed anyway since LLM needs plaintext
- Simpler = fewer bugs = more secure in practice

#### 2.2.3 Authentication Flow

1. User clicks 'Sign in with Google' in PWA
2. Redirect to Google's OAuth consent screen
3. User authenticates with Google (including 2FA if enabled)
4. Google redirects back with authorization code
5. Server exchanges code for user info (email, name, picture)
6. Server verifies email matches allowed user
7. Server issues JWT token for subsequent API calls
8. JWT stored in HttpOnly cookie (secure, not accessible to JS)

#### 2.2.4 Security Configuration

- **Allowed Email:** Only your Google email can authenticate
- **JWT Expiry:** 24 hours, with refresh capability
- **Cookie Settings:** HttpOnly, Secure, SameSite=Strict
- **CORS:** Restricted to your frontend domain only

---

## 3. Data Models

### 3.1 Entry

The core data unit representing a day's journaling activity.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| date | DATE | Entry date (YYYY-MM-DD) |
| conversations | JSON | Array of Conversation objects |
| refined_output | TEXT | LLM-generated daily summary (markdown) |
| relevance_score | FLOAT | Calculated priority (0.0-1.0+) |
| last_interacted_at | TIMESTAMP | Last view/edit/reference time |
| interaction_count | INTEGER | Total access count |
| status | ENUM | 'active' \| 'archived' |
| version | INTEGER | Increments on each edit (for sync) |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last modification timestamp |

#### 3.1.1 Conversation (JSON structure within Entry)

```json
{
  "id": "uuid",
  "started_at": "ISO timestamp",
  "messages": [
    { "role": "user | assistant", "content": "string", "timestamp": "ISO" }
  ],
  "prompt_source": "user | notification | continuation",
  "notification_id": "uuid | null"
}
```

#### 3.1.2 Relevance Score Calculation

```
relevance = exp(-days_since_interaction / 30) * (1 + log(interaction_count + 1))
```

Half-life of approximately 30 days, boosted by interaction frequency.

### 3.2 Entry Version

Historical snapshots for conflict resolution.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| entry_id | UUID (FK) | Reference to parent entry |
| version | INTEGER | Version number at snapshot time |
| content_snapshot | TEXT | Full refined_output at this version |
| created_at | TIMESTAMP | When this version was created |

### 3.3 Goal

User-defined objectives that guide notification generation.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| category | VARCHAR | 'health' \| 'productivity' \| 'skills' \| custom |
| description | TEXT | Goal description (e.g., 'Learn piano') |
| active | BOOLEAN | Whether goal is currently active |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last modification timestamp |

### 3.4 Proposal

Pending changes from cleanup or code modification suggestions.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| type | ENUM | 'cleanup' \| 'question' \| 'goal_update' \| 'code_change' |
| target_entry_id | UUID (FK) | Affected entry (nullable for code changes) |
| description | TEXT | Human-readable summary of change |
| diff_before | TEXT | Original content (for content changes) |
| diff_after | TEXT | Proposed new content |
| status | ENUM | 'pending' \| 'approved' \| 'rejected' |
| created_at | TIMESTAMP | Creation timestamp |
| reviewed_at | TIMESTAMP | When approved/rejected (nullable) |

### 3.5 Code Spec

Specifications for self-modifying code changes.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| title | VARCHAR | Short title (e.g., 'Add full-text search') |
| problem | TEXT | Why this change is needed |
| requirements | JSON | Array of specific requirements |
| suggested_approach | TEXT | Technical direction |
| affected_areas | JSON | Array of affected code areas |
| acceptance_criteria | JSON | How to verify completion |
| priority | ENUM | 'low' \| 'medium' \| 'high' |
| status | ENUM | 'proposed' \| 'approved' \| 'in_progress' \| 'completed' |
| github_pr_url | VARCHAR | PR URL after implementation (nullable) |
| created_at | TIMESTAMP | Creation timestamp |
| approved_at | TIMESTAMP | Approval timestamp (nullable) |
| completed_at | TIMESTAMP | Completion timestamp (nullable) |

### 3.6 Scheduled Notification

Pre-generated prompts queued for delivery.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| prompt | TEXT | The notification content |
| related_entry_ids | JSON | Array of inspiring entry IDs |
| related_goal_ids | JSON | Array of related goal IDs |
| scheduled_for | TIMESTAMP | When to send |
| expires_at | TIMESTAMP | Don't send if past this time |
| status | ENUM | 'pending' \| 'sent' \| 'expired' \| 'dismissed' |
| sent_at | TIMESTAMP | Actual send time (nullable) |
| interacted_at | TIMESTAMP | When user responded (nullable) |

### 3.7 Notification Config

User preferences for notification delivery.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key (singleton) |
| prompts_per_day | INTEGER | Default: 1, max: 5 |
| quiet_hours_start | TIME | e.g., '22:00' |
| quiet_hours_end | TIME | e.g., '08:00' |
| preferred_times | JSON | Array of preferred times ['09:00', '14:00'] |
| timezone | VARCHAR | IANA timezone (e.g., 'America/New_York') |

### 3.8 Push Subscription

Web Push subscription data for notifications.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| endpoint | TEXT | Push service endpoint URL |
| p256dh_key | TEXT | Client public key |
| auth_key | TEXT | Auth secret |
| created_at | TIMESTAMP | Subscription creation time |

---

## 4. API Specification

### 4.1 Authentication Endpoints (Google OAuth)

#### GET /api/auth/login

Initiates Google OAuth flow. Redirects user to Google's consent screen.

**Response:** 302 Redirect to accounts.google.com

#### GET /api/auth/callback

OAuth callback handler. Google redirects here after user authenticates.

**Query params:** `code` (authorization code from Google)

**Response:** 302 Redirect to frontend with JWT set in HttpOnly cookie

**Error:** 403 if email not in allowed list

#### GET /api/auth/me

Get current authenticated user info.

**Response:** `{ "email": "string", "name": "string", "picture": "url" }`

#### POST /api/auth/logout

Clear authentication cookie.

**Response:** `{ "success": true }`

### 4.2 Sync Endpoints

#### POST /api/sync

Synchronize local changes with server.

**Request:** `{ "last_synced_at": "ISO timestamp", "pending_changes": [PendingChange], "base_versions": { "entry_id": version } }`

**Response:** `{ "applied": [entry_id], "conflicts": [ConflictResult], "new_server_changes": [Entry] }`

#### POST /api/sync/resolve

Resolve a sync conflict after user decision.

**Request:** `{ "entry_id": "uuid", "resolution": "local" | "server" | "merged", "merged_content": "string (if resolution=merged)" }`

**Response:** `{ "success": true, "entry": Entry }`

### 4.3 Entry Endpoints

#### GET /api/entries

Fetch entries with optional filtering.

**Query params:** status, after_date, before_date, limit, offset, order_by

**Response:** `{ "entries": [Entry], "total": number }`

#### GET /api/entries/{id}

Fetch a single entry with full conversation history.

**Response:** Entry

#### POST /api/entries

Create a new entry.

**Request:** `{ "date": "YYYY-MM-DD", "conversations": [], "refined_output": "string" }`

**Response:** Entry

#### PUT /api/entries/{id}

Update an existing entry.

**Request:** Partial<Entry>

**Response:** Entry

#### GET /api/entries/{id}/versions

Get version history for conflict resolution.

**Response:** `{ "versions": [EntryVersion] }`

### 4.4 Chat Endpoints

#### POST /api/chat

Send a message and receive LLM response.

**Request:** `{ "entry_id": "uuid", "conversation_id": "uuid", "message": "string", "use_local_model": boolean }`

**Response:** `{ "response": "string", "conversation_id": "uuid" }`

#### POST /api/chat/refine

Generate refined output from conversation history.

**Request:** `{ "entry_id": "uuid" }`

**Response:** `{ "refined_output": "string" }`

### 4.5 Goal Endpoints

#### GET /api/goals

**Response:** `{ "goals": [Goal] }`

#### POST /api/goals

**Request:** `{ "category": "string", "description": "string" }`

**Response:** Goal

#### PUT /api/goals/{id}

**Request:** Partial<Goal>

**Response:** Goal

#### DELETE /api/goals/{id}

**Response:** `{ "success": true }`

### 4.6 Proposal Endpoints

#### GET /api/proposals

**Query params:** status, type

**Response:** `{ "proposals": [Proposal] }`

#### POST /api/proposals/{id}/approve

**Response:** `{ "success": true, "applied_to": "entry_id or null" }`

#### POST /api/proposals/{id}/reject

**Response:** `{ "success": true }`

#### POST /api/cleanup/trigger

Manually trigger cleanup analysis (for testing).

**Response:** `{ "proposals_created": number }`

### 4.7 Code Spec Endpoints

#### GET /api/code-specs

**Query params:** status, priority

**Response:** `{ "specs": [CodeSpec] }`

#### POST /api/code-specs

**Request:** CodeSpec (without id, timestamps)

**Response:** CodeSpec

#### PUT /api/code-specs/{id}

**Request:** Partial<CodeSpec>

**Response:** CodeSpec

### 4.8 Notification Endpoints

#### POST /api/push/subscribe

Register a push subscription.

**Request:** `{ "endpoint": "url", "keys": { "p256dh": "base64", "auth": "base64" } }`

**Response:** `{ "success": true }`

#### GET /api/notifications

**Query params:** status, limit

**Response:** `{ "notifications": [ScheduledNotification] }`

#### GET /api/notifications/config

**Response:** NotificationConfig

#### PUT /api/notifications/config

**Request:** Partial<NotificationConfig>

**Response:** NotificationConfig

---

## 5. Sync System Design

### 5.1 Offline-First Principles

- Client operates fully offline using IndexedDB
- All changes queued locally with timestamps
- Server is source of truth when online
- Sync occurs on reconnect and periodically when online

### 5.2 Diff Calculation (Code-Based)

Diffs are calculated using Python's difflib with the Myers algorithm, not LLM calls.

#### 5.2.1 Implementation

```python
from difflib import SequenceMatcher, unified_diff

def calculate_diff(old: str, new: str) -> dict:
    matcher = SequenceMatcher(None, old, new)
    changes = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op != 'equal':
            changes.append({
                'operation': op,
                'old_text': old[i1:i2] if op in ('replace','delete') else None,
                'new_text': new[j1:j2] if op in ('replace','insert') else None,
                'old_range': (i1, i2),
                'new_range': (j1, j2)
            })
    return {
        'changes': changes,
        'similarity': matcher.ratio(),
        'unified': list(unified_diff(old.splitlines(), new.splitlines()))
    }
```

### 5.3 Sync Flow

1. Client collects pending changes with timestamps and base versions
2. Client sends sync request to server
3. Server processes each pending change:
   - If entry.version == expected base version: apply change, increment version
   - If entry.version != base version: mark as conflict
4. For conflicts, server calculates code-based diff between versions
5. Server checks if changes overlap using character ranges
6. Non-overlapping changes: auto-merge both sets
7. Overlapping changes: return conflict for user resolution
8. Server returns: applied changes, conflicts, new server changes
9. Client updates local state, shows conflict UI if needed

### 5.4 Conflict Detection

```python
def regions_overlap(a: list[tuple], b: list[tuple]) -> bool:
    for (a1, a2) in a:
        for (b1, b2) in b:
            if a1 < b2 and b1 < a2:  # Standard overlap check
                return True
    return False
```

### 5.5 Conflict Resolution Options

1. **Keep Local:** Discard server changes, apply user's version
2. **Keep Server:** Discard local changes, accept server's version
3. **Manual Merge:** Show side-by-side diff, user edits final result

#### 5.5.1 Optional LLM Assistance

For complex conflicts, an optional 'Explain Conflict' button can call the LLM to describe in plain English what each side changed. This is not in the critical path—just a helper.

---

## 6. Agentic Systems

### 6.1 Cleanup System

Daily automated analysis of journal entries to propose improvements.

#### 6.1.1 Cleanup Prompt (Initial - Formatting Only)

Stored in configuration, editable over time:

```
You are reviewing a thought journal entry. Your task is to propose
improvements.

CURRENT CAPABILITIES (only do these):
- Fix spelling and grammar errors
- Improve formatting (consistent headers, bullet points)
- Fix markdown syntax issues

DO NOT:
- Change the meaning or tone
- Add new ideas or content
- Remove any information

For each change, output JSON:
{
  "proposals": [{
    "description": "human readable summary",
    "before": "original text",
    "after": "corrected text"
  }]
}
```

#### 6.1.2 Future Capabilities (Progressive)

- Phase 2: Generate reflective questions based on content
- Phase 3: Suggest goal updates based on patterns
- Phase 4: Identify connections between entries
- Phase 5: Create summaries and insights

### 6.2 Notification Generation

Server-side job that creates prompts based on goals and recent entries.

#### 6.2.1 Generation Schedule

- Runs nightly (e.g., 3 AM user's timezone)
- Generates prompts_per_day notifications
- Assigns times based on preferred_times config
- Respects quiet hours

#### 6.2.2 Generation Prompt

```
Generate {n} thought-provoking prompts for a thought journal.

User's active goals: {goals}
Recent high-relevance entries (summarized): {entries}
Already scheduled prompts (avoid repetition): {existing}

Requirements:
- Connect to goals or recent entries
- Vary types: reflective, action-oriented, challenging
- Keep concise (1-2 sentences)
- Be specific, not generic
```

#### 6.2.3 Delivery

- Cron job checks every 15 minutes for due notifications
- Sends via Web Push API
- Marks as 'sent' or 'expired' if past expiry time

### 6.3 Self-Modifying Code System

The system can propose changes to its own codebase.

#### 6.3.1 Code Spec Generation

Triggered by: user request, pattern detection in journal, or system identifying improvement opportunities.

#### 6.3.2 Spec Output Format

```json
{
  "title": "Add full-text search",
  "problem": "Users cannot find old entries quickly",
  "requirements": [
    "Search across all entry content",
    "Support fuzzy matching",
    "Work offline using IndexedDB indexes"
  ],
  "suggested_approach": "Use Dexie.js full-text search addon...",
  "affected_areas": ["frontend/search", "lib/db"],
  "acceptance_criteria": [
    "Can search by keyword and find matching entries",
    "Results show highlighted matches",
    "Works without network connection"
  ]
}
```

#### 6.3.3 Implementation Workflow

1. Spec created (by user or system)
2. User reviews and approves spec
3. Spec marked 'approved' with timestamp
4. User opens Antigravity/Cursor with project
5. User provides spec to coding agent
6. Agent implements, creates branch, pushes to GitHub
7. User updates spec with PR URL
8. After merge, spec marked 'completed'

#### 6.3.4 Daily Improvement Tracking

System tracks days since last code change and surfaces suggestions to maintain daily improvement cadence.

---

## 7. Implementation Phases

### 7.1 Phase 1: Core Journaling (MVP)

**Duration:** 2-3 weeks

1. FastAPI backend skeleton with DuckDB
   - **Tests:** Database connection, schema creation, config loading

2. Google OAuth authentication
   - **Tests:** OAuth flow (mocked), email restriction, callback handling

3. JWT session management with HttpOnly cookies
   - **Tests:** Token generation/validation, expiry handling, cookie security

4. Entry CRUD endpoints
   - **Tests:** All CRUD operations, filtering, pagination, version snapshots

5. SvelteKit PWA shell with offline support
   - **Tests:** Dexie operations (mock IndexedDB), store reactivity

6. IndexedDB setup with Dexie.js
   - **Tests:** Schema creation, CRUD operations, pending changes queue

7. Journal list view
   - **Tests:** List rendering, empty state, offline data display

8. Chat interface for conversations
   - **Tests:** Message sending, streaming display, LLM integration (mocked)

9. Gemini integration via server proxy
   - **Tests:** API client, error handling, streaming responses (mocked)

10. Basic sync (last-write-wins with warning)
    - **Tests:** Change queuing, sync flow, last-write-wins resolution

11. Goals CRUD
    - **Tests:** All CRUD operations, ownership validation

**Deliverable:** Working app where you can journal conversationally, online or offline

### 7.2 Phase 2: Intelligence Layer

**Duration:** 2 weeks

1. Code-based diff calculation
   - **Tests:** Diff accuracy, overlap detection, edge cases (empty, identical)

2. Entry version history storage
   - **Tests:** Version snapshot creation, retrieval, integrity

3. Full sync with auto-merge for non-overlapping changes
   - **Tests:** Auto-merge scenarios, version conflict detection

4. Conflict resolution UI
   - **Tests:** Diff rendering, resolution actions, merged content editing

5. Manual cleanup trigger
   - **Tests:** LLM analysis (mocked), proposal generation

6. Proposal review interface
   - **Tests:** Proposal CRUD, approval/rejection flows, diff application

7. Relevance scoring implementation
   - **Tests:** Score calculation accuracy, decay function, interaction tracking

8. Archive functionality
   - **Tests:** Archive/unarchive operations, filtering, suggestions

**Deliverable:** Robust sync system, basic cleanup proposals

### 7.3 Phase 3: Proactive Features

**Duration:** 2 weeks

1. Push notification service (VAPID setup)
   - **Tests:** Subscription storage, push sending (mocked), expiry handling

2. Notification generation job
   - **Tests:** Prompt generation (mocked LLM), scheduling, deduplication

3. Notification timing configuration UI
   - **Tests:** Config CRUD, quiet hours validation, timezone handling

4. Scheduled cleanup runs
   - **Tests:** Job scheduling, execution, error handling

5. Auto-archive with user notification
   - **Tests:** Archive criteria, notification triggers, batch operations

6. Ollama integration for local LLM
   - **Tests:** Client connection, routing logic, fallback behavior

**Deliverable:** Proactive prompting, automated maintenance

### 7.4 Phase 4: Self-Evolution

**Duration:** 1-2 weeks

1. Code spec data model and endpoints
   - **Tests:** Spec CRUD, status transitions, validation

2. Code spec management UI
   - **Tests:** List/filter rendering, create/edit forms, status actions

3. System-generated improvement suggestions
   - **Tests:** Pattern detection, suggestion generation, deduplication

4. GitHub integration for tracking PRs
   - **Tests:** PR URL storage, status updates

5. Daily improvement tracking
   - **Tests:** Days-since calculation, dashboard display, reminder logic

**Deliverable:** Self-improving system with clear spec handoff

---

## 8. User Flows & Edge Cases

### 8.1 Authentication Flow (Google OAuth)

#### 8.1.1 Login

**Happy Path:** User clicks 'Sign in with Google' → Redirected to Google → Authenticates → Redirected back → JWT cookie set → Enters app

**Edge Cases:**

- User cancels Google consent → Redirect to login page with message
- Email not in allowed list → Show 'not authorized' message
- Google service unavailable → Show error, suggest retry
- Popup blocked → Fallback to redirect flow (default)
- Already logged in → Skip OAuth, redirect to app

#### 8.1.2 Session Management

**Happy Path:** User returns to app → JWT cookie validated → Session continues

**Edge Cases:**

- JWT expired → Redirect to login
- Cookie cleared/missing → Redirect to login
- Invalid JWT signature → Clear cookie, redirect to login

#### 8.1.3 Logout

**Happy Path:** User clicks logout → Cookie cleared → Redirect to login

### 8.2 Journaling Flow

#### 8.2.1 Creating New Entry

**Happy Path:** User opens app → Taps 'New Entry' → Chat interface opens → User types message → LLM responds → Conversation continues → Entry auto-saved

**Edge Cases:**

- Entry for today already exists → Open existing entry, start new conversation within it
- Offline when starting → Create locally, queue for sync
- LLM timeout → Show error, allow retry, save user message locally
- LLM returns error → Show message, offer to continue without AI
- Very long message → Warn if over token limit, truncate context if needed
- User closes mid-conversation → Auto-save state, resume on return

#### 8.2.2 Continuing Previous Entry

**Happy Path:** User selects entry from list → Views refined output → Taps 'Continue' → New conversation starts with context from previous

**Edge Cases:**

- Entry is archived → Show 'Unarchive to continue' prompt
- Entry was modified on server since last sync → Trigger sync first, show any conflicts
- Multiple devices editing same entry → Conflict detected on sync

#### 8.2.3 Responding to Push Notification

**Happy Path:** User receives notification → Taps → App opens to chat with prompt pre-filled → User responds → New conversation on today's entry

**Edge Cases:**

- Notification tapped while offline → Open app, show prompt, queue response
- Entry for today doesn't exist → Create new entry with this conversation
- User dismisses notification → Mark as 'dismissed' in database
- Notification expired before tap → Don't show stale prompt, open normal view

### 8.3 Sync Flow

#### 8.3.1 Normal Sync

**Happy Path:** App reconnects → Detects pending changes → Sends to server → Server applies → Returns new server changes → Client updates

**Edge Cases:**

- No pending changes, no server changes → No-op, update last_synced_at
- Only local changes → Apply all, return success
- Only server changes → Pull all, update local
- Large number of changes (>100) → Paginate sync requests

#### 8.3.2 Conflict - Non-Overlapping

**Scenario:** User edited paragraph 1 offline, server cleanup fixed typos in paragraph 3

**Resolution:** Auto-merge both changes, no user intervention needed

**Edge Cases:**

- Changes are adjacent but not overlapping → Still auto-merge
- One side deleted content the other edited → Treat as overlapping, require user decision

#### 8.3.3 Conflict - Overlapping

**Scenario:** User rewrote paragraph 2 offline, server cleanup also modified paragraph 2

**Resolution:** Show conflict UI with both versions and diff

**Edge Cases:**

- User chooses 'Keep Local' → Server version discarded, local version becomes truth
- User chooses 'Keep Server' → Local changes discarded
- User chooses 'Manual Merge' → Show editor with both versions, user creates final
- User closes app without resolving → Conflict persists, shown on next open
- Multiple entries have conflicts → Show list, resolve one at a time

### 8.4 Cleanup Flow

#### 8.4.1 Scheduled Cleanup

**Happy Path:** Cron triggers at 4 AM → System analyzes recent entries → Proposals created → User sees badge on next open → Reviews and approves/rejects

**Edge Cases:**

- No entries to clean → Job completes with 0 proposals
- LLM error during analysis → Log error, skip entry, continue with others
- All proposals rejected → System learns (future: adjust prompts)
- User approves partial → Apply approved, leave others pending

#### 8.4.2 Manual Cleanup Trigger

**Happy Path:** User taps 'Run Cleanup Now' → System analyzes → Proposals shown immediately

**Edge Cases:**

- Already running → Show 'cleanup in progress'
- No entries → Show 'nothing to clean'
- Timeout → Show partial results if any, error for rest

### 8.5 Code Spec Flow

#### 8.5.1 User-Initiated Spec

**Happy Path:** User describes desired feature → System generates detailed spec → User reviews and edits → Approves → Opens Antigravity → Implements → Updates spec with PR URL

**Edge Cases:**

- Vague request → System asks clarifying questions before generating spec
- Spec too large → Suggest breaking into smaller specs
- Implementation fails → Mark spec as 'blocked', add notes

#### 8.5.2 System-Suggested Spec

**Happy Path:** System notices pattern (e.g., user searches a lot) → Proposes 'Add search feature' → User approves/rejects

**Edge Cases:**

- Suggestion already exists → Don't duplicate
- User rejects → Record rejection, don't suggest similar soon

### 8.6 Error States

#### 8.6.1 Network Errors

- Offline detected → Show indicator, continue in offline mode
- Reconnected → Trigger background sync
- Partial sync failure → Retry failed items, show which succeeded

#### 8.6.2 Data Errors

- Corrupt local data → Attempt recovery from server, worst case: prompt fresh sync
- Invalid server response → Log, show error, allow retry
- Version mismatch → Force full sync

#### 8.6.3 LLM Errors

- Rate limited → Back off, show 'try again in X minutes'
- Content filtered → Show generic message, allow retry with different wording
- Service unavailable → Offer local model if configured

---

## 9. Testing Strategy

### 9.1 Unit Tests

#### 9.1.1 Backend (Python/pytest)

- Diff calculation: verify changes detected correctly
- Overlap detection: various overlap scenarios
- Auto-merge: non-overlapping changes combine correctly
- Relevance scoring: decay and boost calculations
- JWT generation and validation
- OAuth callback processing

#### 9.1.2 Frontend (Vitest)

- Dexie.js operations: CRUD, querying
- Sync state management: pending changes, conflict queue
- Auth state management: login status, token handling
- Date/time utilities: timezone handling

### 9.2 Integration Tests

#### 9.2.1 API Tests (pytest + httpx)

- Full auth flow: login via OAuth → access protected routes → logout
- Entry lifecycle: create → read → update → delete
- Sync scenarios: no conflict, auto-merge, overlapping conflict
- Proposal flow: generate → approve/reject → verify applied

#### 9.2.2 Database Tests

- DuckDB queries perform correctly
- Transactions: rollback on error
- Concurrent access: no corruption

### 9.3 End-to-End Tests (Playwright)

#### 9.3.1 Critical Paths

- User can login via Google OAuth and access app
- User can have multi-turn conversation with LLM
- Offline changes sync correctly when reconnected
- Conflict resolution UI works for overlapping changes
- Push notification opens correct entry
- Cleanup proposals can be reviewed and approved

#### 9.3.2 Edge Case Tests

- Simulate network disconnection mid-sync
- Simulate LLM timeout
- Test with large conversation history
- Test conflict with many overlapping regions

### 9.4 Performance Tests

- Sync with 1000+ entries
- Diff calculation on large documents (10k+ characters)
- IndexedDB query performance with year of data
- Concurrent API requests

### 9.5 Security Tests

- OAuth flow: verify only allowed email can authenticate
- JWT validation: verify protected endpoints reject invalid/expired tokens
- Cookie security: verify HttpOnly, Secure, SameSite flags
- Input validation: SQL injection, XSS attempts
- CORS: verify only allowed origins can make requests

---

## 10. Project Structure

### 10.1 Backend (FastAPI)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, CORS, middleware
│   ├── config.py               # Settings, environment variables
│   ├── database.py             # DuckDB connection, setup
│   ├── models/
│   │   ├── entry.py
│   │   ├── goal.py
│   │   ├── proposal.py
│   │   ├── code_spec.py
│   │   └── notification.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── entries.py
│   │   ├── sync.py
│   │   ├── chat.py
│   │   ├── goals.py
│   │   ├── proposals.py
│   │   ├── code_specs.py
│   │   └── notifications.py
│   ├── services/
│   │   ├── diff.py              # Code-based diff calculation
│   │   ├── sync.py              # Sync logic, conflict detection
│   │   ├── llm.py               # LLM router (Gemini/Ollama)
│   │   ├── cleanup.py           # Cleanup analysis
│   │   └── notifications.py     # Generation and sending
│   ├── jobs/
│   │   ├── scheduler.py         # APScheduler setup
│   │   ├── cleanup_job.py
│   │   ├── notification_job.py
│   │   └── archive_job.py
│   └── auth/
│       ├── oauth.py             # Google OAuth setup
│       ├── jwt.py               # JWT utilities
│       └── dependencies.py      # Auth dependencies for routes
├── tests/
├── alembic/                     # Migrations (if needed)
├── requirements.txt
└── Dockerfile
```

### 10.2 Frontend (SvelteKit)

```
frontend/
├── src/
│   ├── routes/
│   │   ├── +layout.svelte
│   │   ├── +page.svelte         # Journal list
│   │   ├── login/+page.svelte
│   │   ├── entry/
│   │   │   ├── [id]/+page.svelte # Entry detail/chat
│   │   │   └── new/+page.svelte
│   │   ├── goals/+page.svelte
│   │   ├── proposals/+page.svelte
│   │   ├── archive/+page.svelte
│   │   ├── code-specs/+page.svelte
│   │   └── settings/+page.svelte
│   ├── lib/
│   │   ├── db/
│   │   │   ├── index.ts          # Dexie.js setup
│   │   │   ├── entries.ts
│   │   │   ├── goals.ts
│   │   │   └── sync.ts
│   │   ├── api/
│   │   │   ├── client.ts         # API client with auth
│   │   │   ├── auth.ts
│   │   │   └── sync.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   ├── entries.ts
│   │   │   ├── sync.ts
│   │   │   └── ui.ts
│   │   └── utils/
│   │       ├── date.ts
│   │       └── diff.ts           # Client-side diff display
│   ├── components/
│   │   ├── Chat.svelte
│   │   ├── EntryCard.svelte
│   │   ├── ConflictResolver.svelte
│   │   ├── ProposalCard.svelte
│   │   └── ...
│   └── service-worker.ts
├── static/
│   └── manifest.json
├── tests/
├── svelte.config.js
├── vite.config.ts
└── package.json
```

---

## 11. Appendix

### 11.1 Environment Variables

#### Backend

```bash
DATABASE_URL=duckdb:///./data/journal.duckdb
JWT_SECRET=<random-256-bit-key>
JWT_EXPIRY_HOURS=24
GOOGLE_CLIENT_ID=<from-google-console>
GOOGLE_CLIENT_SECRET=<from-google-console>
ALLOWED_EMAIL=your.email@gmail.com
FRONTEND_URL=https://your-frontend-domain.com
GEMINI_API_KEY=<your-key>
OLLAMA_URL=http://localhost:11434
VAPID_PRIVATE_KEY=<vapid-private>
VAPID_PUBLIC_KEY=<vapid-public>
CLEANUP_CRON=0 4 * * *
NOTIFICATION_CRON=*/15 * * * *
```

#### Frontend

```bash
PUBLIC_API_URL=https://server.epicrunze.com/api
PUBLIC_VAPID_KEY=<vapid-public>
```

### 11.2 DuckDB Schema

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR UNIQUE NOT NULL,
  name VARCHAR,
  picture VARCHAR,
  created_at TIMESTAMP DEFAULT now(),
  last_login_at TIMESTAMP
);

CREATE TABLE entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  date DATE NOT NULL,
  conversations JSON DEFAULT '[]',
  refined_output TEXT DEFAULT '',
  relevance_score FLOAT DEFAULT 1.0,
  last_interacted_at TIMESTAMP DEFAULT now(),
  interaction_count INTEGER DEFAULT 0,
  status VARCHAR DEFAULT 'active',
  version INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE entry_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id UUID REFERENCES entries(id),
  version INTEGER NOT NULL,
  content_snapshot TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  category VARCHAR NOT NULL,
  description TEXT NOT NULL,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  type VARCHAR NOT NULL,
  target_entry_id UUID REFERENCES entries(id),
  description TEXT NOT NULL,
  diff_before TEXT,
  diff_after TEXT,
  status VARCHAR DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT now(),
  reviewed_at TIMESTAMP
);

CREATE TABLE code_specs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  title VARCHAR NOT NULL,
  problem TEXT NOT NULL,
  requirements JSON DEFAULT '[]',
  suggested_approach TEXT,
  affected_areas JSON DEFAULT '[]',
  acceptance_criteria JSON DEFAULT '[]',
  priority VARCHAR DEFAULT 'medium',
  status VARCHAR DEFAULT 'proposed',
  github_pr_url VARCHAR,
  created_at TIMESTAMP DEFAULT now(),
  approved_at TIMESTAMP,
  completed_at TIMESTAMP
);

CREATE TABLE scheduled_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  prompt TEXT NOT NULL,
  related_entry_ids JSON DEFAULT '[]',
  related_goal_ids JSON DEFAULT '[]',
  scheduled_for TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  status VARCHAR DEFAULT 'pending',
  sent_at TIMESTAMP,
  interacted_at TIMESTAMP
);

CREATE TABLE notification_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) UNIQUE,
  prompts_per_day INTEGER DEFAULT 1,
  quiet_hours_start TIME DEFAULT '22:00',
  quiet_hours_end TIME DEFAULT '08:00',
  preferred_times JSON DEFAULT '["09:00", "14:00", "19:00"]',
  timezone VARCHAR DEFAULT 'UTC'
);

CREATE TABLE push_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  endpoint TEXT NOT NULL,
  p256dh_key TEXT NOT NULL,
  auth_key TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
```

### 11.3 Deployment Checklist

- [ ] Set up SSL certificate for server.epicrunze.com
- [ ] Configure nginx reverse proxy to FastAPI
- [ ] Create Google Cloud project and OAuth credentials
- [ ] Set authorized redirect URI in Google Console
- [ ] Set all environment variables (including GOOGLE_CLIENT_ID/SECRET)
- [ ] Initialize DuckDB with schema
- [ ] Generate VAPID keys for push notifications
- [ ] Build SvelteKit for production
- [ ] Configure systemd service for FastAPI
- [ ] Set up cron or APScheduler for jobs
- [ ] Test full flow: Google login → journal → sync

### 11.4 Future Considerations

- Multi-user support (if needed)
- Export functionality (markdown, JSON)
- Import from other journaling apps
- Voice input for entries
- Image attachments
- Mobile app (Capacitor wrapper)
- Collaborative features
