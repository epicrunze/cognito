# Cognito PWA - Coding Agent Prompts

> **Plan for implementing Cognito PWA via sequential Antigravity prompts**
> 
> Each prompt covers a logical unit of work, includes relevant testing, and builds on previous prompts.

---

## Overview

| Phase | Prompts | Estimated Effort |
|-------|---------|------------------|
| Phase 1: Core Journaling (MVP) | 1-8 | 2-3 weeks |
| Phase 2: Intelligence Layer | 9-12 | 2 weeks |
| Phase 3: Proactive Features | 13-16 | 2 weeks |
| Phase 4: Self-Evolution | 17-18 | 1-2 weeks |

---

## Phase 1: Core Journaling (MVP)

### Prompt 1: Backend Foundation

**Goal:** Set up FastAPI backend skeleton with DuckDB and project structure

**Context to provide:**
- Project structure from spec Section 10.1
- DuckDB schema from Section 11.2
- Environment variables from Section 11.1

**Prompt:**
```
Create a FastAPI backend for Cognito PWA with the following requirements:

1. Project Structure:
   - Create the folder structure as specified in the spec (backend/app/...)
   - Set up pyproject.toml with dependencies: fastapi, uvicorn, duckdb, pydantic, python-jose[cryptography], httpx, python-multipart, apscheduler
   - Use uv as the package manager (uv init, uv add)

2. Configuration:
   - Create config.py using pydantic-settings for environment variables
   - Support: DATABASE_URL, JWT_SECRET, JWT_EXPIRY_HOURS, ALLOWED_EMAIL, FRONTEND_URL, GEMINI_API_KEY, OLLAMA_URL

3. Database:
   - Create database.py with DuckDB connection management
   - Implement the full schema (users, entries, entry_versions, goals, proposals, code_specs, scheduled_notifications, notification_config, push_subscriptions)
   - Create a schema initialization function

4. Main App:
   - Create main.py with FastAPI app, CORS middleware (configurable origins), health check endpoint
   - Set up lifespan for database initialization

5. Testing:
   - Write pytest tests for database connection and schema creation
   - Test configuration loading with environment variables
   - Use a separate test database

Include a README with setup instructions using uv:
- uv sync to install dependencies
- uv run uvicorn app.main:app --reload to start dev server
- uv run pytest to run tests
```

**Tests expected:**
- `tests/test_database.py` - Schema creation, connection handling
- `tests/test_config.py` - Environment variable loading

**Documentation:** Update README with setup instructions, project structure overview, and environment variable reference.

---

### Prompt 2: Authentication - Google OAuth

**Goal:** Implement Google OAuth 2.0 authentication flow

**Context to provide:**
- Section 2.2 (Security Architecture)
- Section 4.1 (Authentication Endpoints)
- Section 8.1 (Authentication Flow edge cases)

**Prompt:**
```
Implement Google OAuth 2.0 authentication for the Cognito backend. Build on the existing FastAPI skeleton.

1. OAuth Setup (app/auth/oauth.py):
   - Configure Google OAuth using httpx for token exchange
   - Environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
   - Redirect URI: {FRONTEND_URL}/auth/callback

2. JWT Utilities (app/auth/jwt.py):
   - Generate JWT tokens with user email, name, picture
   - Validate and decode tokens
   - Token expiry from JWT_EXPIRY_HOURS config

3. Auth Dependencies (app/auth/dependencies.py):
   - Create `get_current_user` dependency that validates JWT from HttpOnly cookie
   - Raise 401 for invalid/expired tokens
   - Return user info (email, name, picture)

4. Auth Router (app/routers/auth.py):
   - GET /api/auth/login - Redirect to Google OAuth consent screen
   - GET /api/auth/callback - Handle OAuth callback, verify email against ALLOWED_EMAIL, set JWT cookie
   - GET /api/auth/me - Return current user info
   - POST /api/auth/logout - Clear auth cookie

5. Cookie Settings:
   - HttpOnly=True, Secure=True (configurable for dev), SameSite=Strict
   - Max-Age from JWT_EXPIRY_HOURS

6. Edge Cases:
   - User cancels OAuth → Return error redirect
   - Email not allowed → 403 Forbidden
   - Invalid callback code → 400 Bad Request

7. Testing:
   - Mock Google OAuth responses for testing
   - Test JWT generation and validation
   - Test protected route access with valid/invalid/expired tokens
   - Test allowed email restriction

Create a users model (app/models/user.py) with Pydantic models for User and UserInDB.
```

**Tests expected:**
- `tests/test_auth.py` - OAuth flow, JWT handling, email restriction
- `tests/test_jwt.py` - Token generation, validation, expiry

**Documentation:** Update README with authentication setup (Google OAuth configuration), login flow, and security notes.

---

### Prompt 3: Entry CRUD Endpoints

**Goal:** Implement Entry data model and CRUD API endpoints

**Context to provide:**
- Section 3.1 (Entry data model)
- Section 4.3 (Entry Endpoints)
- Section 8.2.1-8.2.2 (Journaling flows)

**Prompt:**
```
Implement Entry CRUD operations for Cognito. Build on existing auth.

1. Entry Model (app/models/entry.py):
   - Pydantic models: Entry, EntryCreate, EntryUpdate, EntryInDB
   - Fields: id, date, conversations (JSON), refined_output, relevance_score, last_interacted_at, interaction_count, status, version, created_at, updated_at
   - Conversation JSON structure with id, started_at, messages, prompt_source, notification_id

2. Entry Router (app/routers/entries.py):
   - All routes require authentication (use get_current_user dependency)
   - GET /api/entries - List entries with filters (status, after_date, before_date, limit, offset, order_by)
   - GET /api/entries/{id} - Get single entry with full conversation history
   - POST /api/entries - Create new entry (auto-generate id, set defaults)
   - PUT /api/entries/{id} - Update entry (increment version, update updated_at)
   - GET /api/entries/{id}/versions - Get version history

3. Database Operations:
   - Create entry_repo functions for CRUD operations
   - On update, create entry_version snapshot of previous state
   - Update last_interacted_at on read

4. Edge Cases:
   - Entry for date already exists → Return existing entry on create
   - Entry not found → 404
   - Entry belongs to different user → 403

5. Testing:
   - Test all CRUD operations
   - Test filtering and pagination
   - Test version history creation on update
   - Test date uniqueness constraint

Use DuckDB's JSON functions for querying conversations.
```

**Tests expected:**
- `tests/test_entries.py` - CRUD operations, filtering, pagination
- `tests/test_entry_versions.py` - Version snapshot creation

**Documentation:** Update README with Entry API endpoints and usage examples.

---

### Prompt 4: Goals CRUD Endpoints

**Goal:** Implement Goal data model and CRUD API endpoints

**Context to provide:**
- Section 3.3 (Goal data model)
- Section 4.5 (Goal Endpoints)

**Prompt:**
```
Implement Goal CRUD operations for Cognito. Build on existing structure.

1. Goal Model (app/models/goal.py):
   - Pydantic models: Goal, GoalCreate, GoalUpdate, GoalInDB
   - Fields: id, category, description, active, created_at, updated_at
   - Category examples: 'health', 'productivity', 'skills', or custom strings

2. Goal Router (app/routers/goals.py):
   - All routes require authentication
   - GET /api/goals - List all goals (optionally filter by active status)
   - POST /api/goals - Create new goal
   - PUT /api/goals/{id} - Update goal (toggle active, change description)
   - DELETE /api/goals/{id} - Soft delete (set active=false) or hard delete

3. Database Operations:
   - Create goal_repo functions for CRUD
   - Goals are user-scoped

4. Testing:
   - Test all CRUD operations
   - Test goal ownership validation
   - Test active filtering

This is a simpler module - focus on clean, consistent patterns matching the entries module.
```

**Tests expected:**
- `tests/test_goals.py` - Full CRUD testing

**Documentation:** Update README with Goals API endpoints.

---

### Prompt 5: Frontend Foundation (SvelteKit PWA)

**Goal:** Set up SvelteKit PWA with IndexedDB using Dexie.js

**Context to provide:**
- Section 10.2 (Frontend project structure)
- Section 5.1 (Offline-First Principles)
- Component diagram from Section 2.1.1

**Prompt:**
```
Create a SvelteKit PWA frontend for Cognito with offline-first architecture.

1. Project Setup:
   - Initialize SvelteKit project with TypeScript
   - Configure as PWA with manifest.json and service worker
   - Set up Vite config for offline caching

2. Dependencies:
   - dexie (IndexedDB wrapper)
   - Add any CSS framework setup (or vanilla CSS with custom properties)

3. Dexie Database (src/lib/db/index.ts):
   - Define schema matching backend: entries, goals, pendingChanges, settings
   - Create typed Dexie database class
   - Include sync metadata (lastSyncedAt)

4. Database Modules:
   - src/lib/db/entries.ts - Entry CRUD operations
   - src/lib/db/goals.ts - Goal CRUD operations
   - src/lib/db/sync.ts - Pending changes queue

5. API Client (src/lib/api/client.ts):
   - Base API client with fetch wrapper
   - Auto-include credentials (cookies)
   - Handle offline detection
   - Queue requests when offline

6. Auth API (src/lib/api/auth.ts):
   - login() - redirect to OAuth
   - logout() - call logout endpoint
   - getMe() - get current user

7. Stores (src/lib/stores/):
   - auth.ts - User state, isAuthenticated
   - entries.ts - Entries list with reactive updates
   - sync.ts - Sync status, pending count, last synced
   - ui.ts - Loading states, errors, toasts

8. Layout (src/routes/+layout.svelte):
   - Check auth status on load
   - Show offline indicator
   - Navigation structure

9. Service Worker (src/service-worker.ts):
   - Cache app shell for offline
   - Background sync registration

10. Testing (Vitest):
    - Test Dexie operations (mock IndexedDB)
    - Test store reactivity
    - Test API client offline handling

11. Design System - Cognito Brand Colors:
    Use these CSS custom properties for the color palette:
    
    --color-primary-dark: #1B3C53;    /* Deep navy - headers, primary buttons */
    --color-primary: #234C6A;          /* Navy - interactive elements */
    --color-primary-light: #456882;    /* Muted blue - secondary elements, borders */
    --color-background: #E3E3E3;       /* Light gray - page backgrounds */
    --color-surface: #FFFFFF;          /* White - cards, input backgrounds */
    --color-text-primary: #1B3C53;     /* Deep navy - headings, primary text */
    --color-text-secondary: #456882;   /* Muted blue - secondary text */
    
    Design guidelines:
    - Dark mode: invert the palette (light text on dark backgrounds)
    - Use primary-dark for headers and navigation
    - Use primary for buttons and interactive elements
    - Use primary-light for borders, dividers, and hover states
    - Use background for page backgrounds, surface for cards
    - Ensure AA contrast ratio compliance

Create a beautiful, modern design system with these CSS custom properties for theming.
```

**Tests expected:**
- `tests/lib/db.test.ts` - IndexedDB operations
- `tests/lib/stores.test.ts` - Store reactivity

**Documentation:** Create frontend README with setup instructions, project structure, and design system documentation.

---

### Prompt 6: Frontend - Authentication & Journal List

**Goal:** Implement login page, auth flow, and journal list view

**Context to provide:**
- Section 8.1 (Authentication Flow)
- Auth endpoints from Prompt 2

**Prompt:**
```
Implement authentication UI and journal list for the Cognito frontend.

1. Login Page (src/routes/login/+page.svelte):
   - Beautiful login screen with app branding
   - "Sign in with Google" button
   - Handle redirect to OAuth flow
   - Show error messages from URL params
   - Redirect to home if already authenticated

2. Auth Callback (src/routes/auth/callback/+page.svelte):
   - Handle OAuth callback
   - Show loading during token exchange
   - Redirect to home on success
   - Show error and retry option on failure

3. Layout Updates:
   - Protected layout wrapper that redirects to login if not authenticated
   - User avatar/name in header
   - Logout button

4. Journal List (src/routes/+page.svelte):
   - Display entries sorted by date (most recent first)
   - Show entry preview (refined_output truncated)
   - Show relevance indicator
   - Status badge (active/archived)
   - "New Entry" floating action button
   - Pull-to-refresh on mobile

5. Entry Card Component (src/components/EntryCard.svelte):
   - Date display (formatted nicely)
   - Preview text
   - Conversation count
   - Last interacted indicator
   - Click to open entry

6. Empty State:
   - Friendly message when no entries
   - Prompt to create first entry

7. Offline Behavior:
   - Load from IndexedDB first
   - Sync indicator showing pending changes
   - Work without network

8. Testing:
   - Test auth redirects
   - Test entry list rendering
   - Test offline data display

Ensure the UI is responsive and works beautifully on mobile.
```

**Tests expected:**
- `tests/routes/login.test.ts` - Auth flow
- `tests/routes/home.test.ts` - Journal list
- `tests/components/EntryCard.test.ts` - Component rendering

**Documentation:** Update frontend README with authentication flow and component usage.

---

### Prompt 7: Chat Interface & Gemini Integration

**Goal:** Implement chat UI and LLM integration for conversational journaling

**Context to provide:**
- Section 4.4 (Chat Endpoints)
- Section 3.1.1 (Conversation structure)
- Section 8.2.1-8.2.2 (Journaling flows)

**Prompt:**
```
Implement the chat interface and Gemini LLM integration for conversational journaling.

**Backend:**

1. LLM Service (app/services/llm.py):
   - GeminiClient class using httpx for API calls
   - OllamaClient class for local model fallback
   - LLMRouter that selects based on use_local_model flag
   - Streaming support for responses

2. Chat Router (app/routers/chat.py):
   - POST /api/chat - Send message, get LLM response
     - Input: entry_id, conversation_id, message, use_local_model
     - Build context from conversation history
     - Store user message and assistant response
     - Return response and conversation_id
   - POST /api/chat/refine - Generate refined output from all conversations
     - Process all conversations for the entry
     - Generate markdown summary
     - Update entry's refined_output

3. System Prompts:
   - Chat prompt: thoughtful journaling companion, asks follow-up questions
   - Refine prompt: synthesize conversations into coherent journal entry

4. Testing:
   - Mock LLM responses for testing
   - Test conversation context building
   - Test message storage
   - Test refined output generation

**Frontend:**

5. Chat Component (src/components/Chat.svelte):
   - Message list (user/assistant styling)
   - Input field with send button
   - Streaming response display
   - Loading indicators
   - Scroll to bottom on new messages

6. Entry Detail Page (src/routes/entry/[id]/+page.svelte):
   - Load entry from IndexedDB (or fetch)
   - Display refined_output in beautiful markdown
   - "Continue conversation" button → opens chat
   - Toggle to view raw conversations

7. New Entry Page (src/routes/entry/new/+page.svelte):
   - Auto-creates entry for today
   - Immediately opens chat interface
   - If entry for today exists, redirect to it

8. Offline Chat:
   - Queue messages when offline
   - Show queued indicator
   - Sync when back online

9. Testing:
   - Test chat message sending
   - Test streaming display
   - Test offline queuing

Make the chat experience feel native and responsive.
```

**Tests expected:**
- `tests/test_chat.py` - Chat endpoints with mocked LLM
- `tests/test_llm.py` - LLM client tests
- `tests/components/Chat.test.ts` - Chat component
- `tests/routes/entry.test.ts` - Entry detail page

**Documentation:** Update READMEs with Chat API endpoints, LLM configuration, and system prompt customization.

---

### Prompt 8: Basic Sync (Last-Write-Wins)

**Goal:** Implement simple sync mechanism with last-write-wins conflict resolution

**Context to provide:**
- Section 5.1 (Offline-First Principles)
- Section 4.2 (Sync Endpoints)
- Section 8.3.1 (Normal Sync flow)

**Prompt:**
```
Implement basic sync functionality with last-write-wins strategy. Full conflict resolution comes in Phase 2.

**Backend:**

1. Sync Service (app/services/sync.py):
   - Process pending changes from client
   - Compare timestamps, apply newer changes
   - Return server changes since last sync

2. Sync Router (app/routers/sync.py):
   - POST /api/sync
     - Input: last_synced_at, pending_changes[], base_versions{}
     - Process each pending change
     - Last-write-wins based on updated_at
     - Return: applied[], server_changes[]
   - Simple implementation - no merge conflicts yet

3. Testing:
   - Test sync with no conflicts
   - Test last-write-wins resolution
   - Test pulling server changes

**Frontend:**

4. Sync Service (src/lib/api/sync.ts):
   - collectPendingChanges() - gather from IndexedDB
   - pushChanges() - send to server
   - pullChanges() - apply server changes to IndexedDB

5. Sync Manager (src/lib/db/sync.ts):
   - Queue local changes with timestamps
   - Track base versions for future conflict detection
   - Mark changes as synced after success

6. Background Sync:
   - Trigger sync on app focus
   - Trigger sync on network reconnect
   - Periodic sync every 5 minutes when online

7. Sync UI:
   - Sync status indicator in header
   - Pending changes count
   - Last synced timestamp
   - Manual sync button

8. Testing:
   - Test change queuing
   - Test sync flow
   - Test offline → online transition

This foundation enables Phase 2's full conflict resolution.
```

**Tests expected:**
- `tests/test_sync.py` - Sync endpoint tests
- `tests/lib/sync.test.ts` - Frontend sync logic

**Documentation:** Update READMEs with sync API documentation and offline behavior notes.

---

## Phase 2: Intelligence Layer

### Prompt 9: Code-Based Diff & Version History

**Goal:** Implement diff calculation and entry version management

**Context to provide:**
- Section 5.2 (Diff Calculation)
- Section 3.2 (Entry Version model)
- Python difflib code from spec

**Prompt:**
```
Implement code-based diff calculation for sync conflict detection.

1. Diff Service (app/services/diff.py):
   - calculate_diff(old: str, new: str) → changes, similarity, unified diff
   - Use difflib.SequenceMatcher with Myers algorithm
   - Return change operations with text ranges

2. Overlap Detection:
   - regions_overlap(a: list[tuple], b: list[tuple]) → bool
   - Detect if two sets of changes affect same text regions

3. Auto-Merge:
   - merge_non_overlapping(base: str, changes_a: list, changes_b: list) → merged
   - Apply both sets of changes when they don't overlap

4. Version Service Updates:
   - Enhance entry update to always create version snapshot
   - Store full content_snapshot in entry_versions table

5. Version Endpoints:
   - GET /api/entries/{id}/versions - List all versions
   - GET /api/entries/{id}/versions/{version_id} - Get specific version content

6. Testing:
   - Test diff calculation with various inputs
   - Test overlap detection edge cases
   - Test auto-merge scenarios
   - Test version history retrieval

This enables the full sync system in the next prompt.
```

**Tests expected:**
- `tests/test_diff.py` - Diff calculation, overlap detection, merging
- `tests/test_versions.py` - Version history

**Documentation:** Update README with diff algorithm details and version history API.

---

### Prompt 10: Full Sync with Conflict Resolution

**Goal:** Implement complete sync system with auto-merge and conflict UI

**Context to provide:**
- Section 5.3-5.5 (Sync Flow, Conflict Detection, Resolution)
- Section 8.3.2-8.3.3 (Conflict scenarios)

**Prompt:**
```
Upgrade sync to full conflict detection and resolution using the diff system.

**Backend:**

1. Enhanced Sync Service:
   - Compare entry.version with client's base_version
   - If versions match: apply change
   - If versions differ: calculate diffs
   - Non-overlapping changes: auto-merge
   - Overlapping changes: return as conflict

2. Sync Response Enhancement:
   - applied: [entry_id] - successfully applied changes
   - conflicts: [{entry_id, local_diff, server_diff, auto_mergeable}]
   - new_server_changes: [Entry]

3. Conflict Resolution Endpoint:
   - POST /api/sync/resolve
   - Input: entry_id, resolution ('local'|'server'|'merged'), merged_content
   - Apply resolution, increment version

4. Testing:
   - Test non-overlapping auto-merge
   - Test overlapping conflict detection
   - Test all resolution options

**Frontend:**

5. Conflict Store (src/lib/stores/conflicts.ts):
   - Track pending conflicts
   - Methods to resolve conflicts

6. Conflict Resolver Component (src/components/ConflictResolver.svelte):
   - Side-by-side diff view
   - Highlight conflicting regions
   - "Keep Local" / "Keep Server" buttons
   - "Manual Merge" option with editor
   - Optional: "Explain Conflict" button (calls LLM)

7. Conflict Flow:
   - After sync, check for conflicts
   - Show conflict badge/indicator
   - Open resolver when user taps

8. Testing:
   - Test conflict UI rendering
   - Test resolution actions
   - Test merged content editing

Users can now work offline confidently.
```

**Tests expected:**
- `tests/test_sync_conflicts.py` - Conflict detection and resolution
- `tests/components/ConflictResolver.test.ts` - Conflict UI

**Documentation:** Update READMEs with conflict resolution UI guide and sync troubleshooting.

---

### Prompt 11: Cleanup System & Proposals

**Goal:** Implement automated cleanup analysis and proposal management

**Context to provide:**
- Section 6.1 (Cleanup System)
- Section 3.4 (Proposal model)
- Section 4.6 (Proposal Endpoints)
- Section 8.4 (Cleanup Flow)

**Prompt:**
```
Implement the cleanup system that proposes improvements to journal entries.

**Backend:**

1. Proposal Model (app/models/proposal.py):
   - Pydantic models: Proposal, ProposalCreate, ProposalInDB
   - Types: 'cleanup', 'question', 'goal_update', 'code_change'
   - Status: 'pending', 'approved', 'rejected'

2. Cleanup Service (app/services/cleanup.py):
   - analyze_entry(entry) → list[Proposal]
   - Use Gemini to identify improvements
   - Phase 1 prompt: formatting, spelling, grammar only
   - Parse LLM response into proposals with before/after

3. Cleanup Prompt (configurable):
   - Store in config or database
   - Initial version from spec Section 6.1.1

4. Proposal Router (app/routers/proposals.py):
   - GET /api/proposals - List proposals (filter by status, type)
   - POST /api/proposals/{id}/approve - Apply change to entry
   - POST /api/proposals/{id}/reject - Mark rejected
   - POST /api/cleanup/trigger - Manual cleanup trigger (for testing)

5. Apply Proposal:
   - On approve, apply diff to entry
   - Create version snapshot before applying
   - Mark proposal as approved with timestamp

6. Testing:
   - Mock LLM for cleanup analysis
   - Test proposal CRUD
   - Test approval flow applies changes
   - Test rejection flow

**Frontend:**

7. Proposals Page (src/routes/proposals/+page.svelte):
   - List pending proposals
   - Group by entry/type
   - Pending count badge in nav

8. Proposal Card Component (src/components/ProposalCard.svelte):
   - Show description
   - Side-by-side or inline diff view
   - Approve/Reject buttons
   - Link to affected entry

9. Testing:
   - Test proposal list rendering
   - Test approve/reject actions

Start with manual trigger, scheduled job comes in Phase 3.
```

**Tests expected:**
- `tests/test_cleanup.py` - Cleanup analysis with mocked LLM
- `tests/test_proposals.py` - Proposal CRUD and approval
- `tests/routes/proposals.test.ts` - Proposals page

**Documentation:** Update READMEs with Proposals API, cleanup configuration, and customizing cleanup prompts.

---

### Prompt 12: Relevance Scoring & Archive

**Goal:** Implement relevance calculation and archive functionality

**Context to provide:**
- Section 3.1.2 (Relevance Score Calculation)
- Interaction tracking requirements

**Prompt:**
```
Implement relevance scoring and archive functionality.

**Backend:**

1. Relevance Service:
   - calculate_relevance(days_since_interaction, interaction_count) → float
   - Formula: exp(-days/30) * (1 + log(interaction_count + 1))
   - Recalculate on access

2. Interaction Tracking:
   - Update last_interacted_at on entry read/edit
   - Increment interaction_count on access
   - Recalculate relevance_score

3. Archive Logic:
   - Entries with status='archived' are hidden from main list
   - Archive endpoint: PUT /api/entries/{id} with status='archived'
   - Unarchive endpoint: same with status='active'

4. Archive Suggestions:
   - Identify low-relevance entries (score < threshold)
   - Create suggestions for archiving

5. Testing:
   - Test relevance calculation
   - Test interaction tracking
   - Test archive/unarchive

**Frontend:**

6. Archive Page (src/routes/archive/+page.svelte):
   - List archived entries
   - Unarchive button on each
   - Empty state when no archives

7. Relevance Display:
   - Show relevance score indicator on entry cards
   - Sort by relevance option in list

8. Archive Suggestions UI:
   - Periodic prompt to archive old entries
   - Batch archive action

9. Testing:
   - Test archive page
   - Test relevance sorting

This completes the intelligence layer foundation.
```

**Tests expected:**
- `tests/test_relevance.py` - Score calculation
- `tests/routes/archive.test.ts` - Archive page

**Documentation:** Update READMEs with relevance scoring algorithm and archive behavior.

---

## Phase 3: Proactive Features

### Prompt 13: Push Notification Setup

**Goal:** Set up Web Push infrastructure with VAPID

**Context to provide:**
- Section 3.8 (Push Subscription model)
- Section 4.8 (Notification Endpoints)

**Prompt:**
```
Set up Web Push notification infrastructure.

**Backend:**

1. VAPID Setup:
   - Generate VAPID keys if not configured
   - Add VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY to config

2. Push Subscription Model (app/models/push_subscription.py):
   - endpoint, p256dh_key, auth_key, created_at

3. Notification Router (app/routers/notifications.py):
   - POST /api/push/subscribe - Register subscription
   - DELETE /api/push/unsubscribe - Remove subscription
   - GET /api/push/vapid-key - Return public key for client

4. Push Service (app/services/notifications.py):
   - send_push(subscription, payload) → success/failure
   - Use pywebpush library
   - Handle subscription expiry

5. Testing:
   - Test subscription storage
   - Test push sending (mock)
   - Test invalid subscription handling

**Frontend:**

6. Push Subscription Setup:
   - Request notification permission
   - Subscribe to push with VAPID key
   - Send subscription to server

7. Service Worker Push Handler:
   - Handle push events
   - Display notification with title, body
   - Handle notification click → open app

8. Settings Page Updates:
   - Enable/disable notifications toggle
   - Show permission status

9. Testing:
   - Test subscription flow
   - Test service worker push handling

This infrastructure enables proactive prompting.
```

**Tests expected:**
- `tests/test_push.py` - Push subscription and sending
- `tests/lib/push.test.ts` - Frontend subscription

**Documentation:** Update READMEs with VAPID key generation, push notification setup, and service worker configuration.

---

### Prompt 14: Notification Generation & Scheduling

**Goal:** Implement LLM-generated notification prompts with scheduling

**Context to provide:**
- Section 6.2 (Notification Generation)
- Section 3.6, 3.7 (Notification models)

**Prompt:**
```
Implement scheduled notification generation and delivery.

**Backend:**

1. Notification Models:
   - ScheduledNotification: prompt, scheduled_for, expires_at, status
   - NotificationConfig: prompts_per_day, quiet_hours, preferred_times, timezone

2. Notification Config Endpoints:
   - GET /api/notifications/config - Get user's config
   - PUT /api/notifications/config - Update config

3. Generation Service (app/services/notification_generation.py):
   - generate_prompts(goals, recent_entries, count) → list[str]
   - Use generation prompt from spec Section 6.2.2
   - Avoid repetition with existing scheduled prompts

4. Scheduling Logic:
   - Assign times based on preferred_times config
   - Respect quiet_hours
   - Set expiry (e.g., 4 hours after scheduled time)

5. Notification Jobs (app/jobs/notification_job.py):
   - Generation job: runs nightly, creates day's prompts
   - Delivery job: runs every 15 min, sends due notifications
   - Mark as sent/expired appropriately

6. Notification Endpoints:
   - GET /api/notifications - List notifications (filter by status)
   - POST /api/notifications/{id}/dismiss - Mark dismissed

7. Testing:
   - Test prompt generation (mock LLM)  
   - Test scheduling logic
   - Test delivery job

**Frontend:**

8. Settings Page (src/routes/settings/+page.svelte):
   - Prompts per day slider
   - Quiet hours configuration
   - Preferred times selection
   - Timezone selector

9. Notification Handler:
   - On notification click, open app to today's entry
   - Pre-fill chat with notification prompt

10. Testing:
    - Test settings updates
    - Test notification click handling

Users now receive proactive journaling prompts.
```

**Tests expected:**
- `tests/test_notification_generation.py` - Generation and scheduling
- `tests/test_notification_delivery.py` - Delivery job
- `tests/routes/settings.test.ts` - Settings page

**Documentation:** Update READMEs with notification configuration options and scheduling details.

---

### Prompt 15: Scheduled Jobs & Cron Setup

**Goal:** Implement APScheduler for all scheduled tasks

**Context to provide:**
- Section 6.1.1 (Cleanup schedule)
- Section 6.2.1 (Notification schedule)

**Prompt:**
```
Set up scheduled jobs for cleanup, notifications, and auto-archive.

1. Scheduler Setup (app/jobs/scheduler.py):
   - Configure APScheduler with BackgroundScheduler
   - Store jobs in memory (or database for persistence)
   - Integrate with FastAPI lifespan

2. Cleanup Job (app/jobs/cleanup_job.py):
   - Run at configured time (default: 4 AM user timezone)
   - Analyze recent active entries
   - Create proposals
   - Log results

3. Notification Jobs:
   - Generation job: 3 AM daily
   - Send job: every 15 minutes

4. Archive Job (app/jobs/archive_job.py):
   - Run weekly
   - Identify very low relevance entries
   - Auto-archive OR create proposals (configurable)

5. Job Configuration:
   - Environment variables for cron expressions
   - CLEANUP_CRON, NOTIFICATION_CRON, ARCHIVE_CRON

6. Job Monitoring:
   - Logging for job execution
   - Optional: job history table

7. Testing:
   - Test job scheduling
   - Test job execution (run immediately for test)
   - Test timezone handling

APScheduler runs in-process with FastAPI for simplicity.
```

**Tests expected:**
- `tests/test_scheduler.py` - Job scheduling and execution

**Documentation:** Update README with scheduled jobs configuration and cron expressions.

---

### Prompt 16: Local LLM (Ollama) Integration

**Goal:** Add Ollama support for confidential data

**Context to provide:**
- Section 2.1.1 (LLM Router)
- use_local_model flag in chat

**Prompt:**
```
Add Ollama support as an alternative to Gemini for local/confidential processing.

1. Ollama Client (update app/services/llm.py):
   - OllamaClient class for localhost:11434
   - Support /api/generate and /api/chat endpoints
   - Configure model name (e.g., llama2, mistral)
   - Streaming support

2. LLM Router Enhancement:
   - Route based on use_local_model flag
   - Fallback logic if Ollama unavailable
   - Health check for Ollama availability

3. Configuration:
   - OLLAMA_URL (default: http://localhost:11434)
   - OLLAMA_MODEL (default: llama2)

4. Frontend Toggle:
   - Add "Use Local Model" toggle in chat
   - Show indicator when using local model
   - Settings page: default model preference

5. Ollama Status:
   - Backend endpoint to check Ollama availability
   - Frontend shows Ollama status in settings

6. Testing:
   - Test Ollama client (mock API)
   - Test routing logic
   - Test fallback behavior

Optional: Add model selection if multiple models available.
```

**Tests expected:**
- `tests/test_ollama.py` - Ollama client and routing

**Documentation:** Update READMEs with Ollama setup, model configuration, and fallback behavior.

---

## Phase 4: Self-Evolution

### Prompt 17: Code Spec Management

**Goal:** Implement code specification tracking for self-modifying capabilities

**Context to provide:**
- Section 3.5 (Code Spec model)
- Section 4.7 (Code Spec Endpoints)
- Section 6.3 (Self-Modifying Code System)

**Prompt:**
```
Implement code specification management for tracking improvement ideas.

**Backend:**

1. Code Spec Model (app/models/code_spec.py):
   - Fields: title, problem, requirements, suggested_approach, affected_areas, acceptance_criteria, priority, status, github_pr_url
   - Status: 'proposed', 'approved', 'in_progress', 'completed'

2. Code Spec Router (app/routers/code_specs.py):
   - GET /api/code-specs - List specs (filter by status, priority)
   - POST /api/code-specs - Create new spec
   - PUT /api/code-specs/{id} - Update spec
   - POST /api/code-specs/{id}/approve - Mark approved
   - POST /api/code-specs/{id}/complete - Mark completed with PR URL

3. Spec Generation Service (optional):
   - LLM generates detailed spec from brief description
   - Suggest improvements based on journal patterns

4. Testing:
   - Test CRUD operations
   - Test status transitions
   - Test spec generation (mock LLM)

**Frontend:**

5. Code Specs Page (src/routes/code-specs/+page.svelte):
   - List specs by status (tabs or filters)
   - Create new spec form
   - Edit spec details

6. Spec Detail View:
   - Full spec display
   - Approve/Complete actions
   - GitHub PR link field
   - Markdown rendering for problem/approach

7. Quick Spec Creation:
   - Simple form: just describe the feature
   - LLM expands into full spec

8. Testing:
   - Test spec list and filters
   - Test create/edit forms

This enables structured improvement tracking.
```

**Tests expected:**
- `tests/test_code_specs.py` - Spec CRUD and status
- `tests/routes/code-specs.test.ts` - Specs page

**Documentation:** Update READMEs with Code Spec API and workflow for using specs with coding agents.

---

### Prompt 18: System Improvement Suggestions

**Goal:** Implement system-generated improvement suggestions

**Context to provide:**
- Section 6.3.2-6.3.4 (Spec generation, workflow, daily tracking)

**Prompt:**
```
Implement system-generated improvement suggestions and daily tracking.

1. Pattern Detection Service:
   - Analyze journal entries for improvement opportunities
   - Detect repeated frustrations, feature requests, workarounds
   - Generate code spec suggestions

2. Suggestion Types:
   - User mentioned wanting X feature
   - Detected repeated pattern (e.g., lots of searching)
   - System noticed usage pattern

3. Improvement Tracking:
   - Dashboard showing days since last code change
   - Encourage daily improvement cadence
   - Show pending specs, completed specs

4. Suggestion Job:
   - Weekly job to analyze patterns
   - Create 'proposed' code specs
   - Notification when new suggestions available

5. Frontend Dashboard Addition:
   - "Time to improve!" prompt when overdue
   - Suggested specs carousel
   - Quick approve/dismiss actions

6. Testing:
   - Test pattern detection (mock data)
   - Test suggestion generation
   - Test dashboard display

This completes the self-improving system loop.
```

**Tests expected:**
- `tests/test_suggestions.py` - Pattern detection and generation
- `tests/routes/dashboard.test.ts` - Dashboard with suggestions

**Documentation:** Update READMEs with improvement tracking features and pattern detection capabilities.

---

## Appendix: Testing Guidelines

### Backend Testing (pytest)

```bash
# Run all tests
uv run pytest backend/tests/ -v

# Run with coverage
uv run pytest backend/tests/ --cov=app --cov-report=html

# Run specific test file
uv run pytest backend/tests/test_auth.py -v
```

**Mocking Strategy:**
- Use `httpx.MockTransport` for external API calls (Google OAuth, Gemini, Ollama)
- Use separate test database (in-memory or test file)
- Use pytest fixtures for common setup

### Frontend Testing (Vitest + Playwright)

```
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Coverage
npm run test:coverage
```

**Mocking Strategy:**
- Mock Dexie.js with fake-indexeddb
- Mock fetch for API calls
- Use Playwright for E2E flows

### Test Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| Backend Services | 90%+ |
| Backend Routers | 85%+ |
| Frontend Stores | 90%+ |
| Frontend Components | 80%+ |
| E2E Critical Paths | 100% |

---

## Notes for Agent Usage

1. **Each prompt is designed to be self-contained** with sufficient context to complete the work without external references after the first few prompts.

2. **Sequential execution is required** - each prompt builds on previous work.

3. **Always run tests** before moving to the next prompt.

4. **The spec file should be updated** to include testing requirements (see separate modification plan).

5. **Docker deployment is deferred** - focus on local development first.
