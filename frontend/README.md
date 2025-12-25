# Cognito Frontend

SvelteKit PWA frontend for Cognito thought journal with offline-first architecture.

## Features

- 🔒 **Google OAuth Authentication** - Secure login via Google
- 📱 **Progressive Web App** - Installable, works offline
- 💾 **Offline-First** - IndexedDB with Dexie.js for local storage
- 🔄 **Smart Sync** - Automatic synchronization when online
- 🎨 **Modern Design** - Skeleton UI with Cognito brand colors
- ⚡ **TypeScript** - Full type safety
- ✅ **Tested** - Vitest with fake-indexeddb

## Quick Start

### Prerequisites

- Node.js 20+ (managed with NVM, see `.nvmrc`)
- npm 10+

### Installation

```bash
# Use correct Node version
nvm use

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit `http://localhost:5173`

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
src/
├── lib/
│   ├── components/        # Reusable components
│   │   └── EntryCard.svelte
│   ├── db/               # Dexie.js database
│   │   ├── index.ts      # Schema and types
│   │   ├── entries.ts    # Entry CRUD
│   │   ├── goals.ts      # Goal CRUD
│   │   └── sync.ts       # Sync queue
│   ├── api/              # API client
│   │   ├── client.ts     # Base client
│   │   └── auth.ts       # Auth API
│   └── stores/           # Svelte stores
│       ├── auth.ts       # Authentication
│       ├── entries.ts    # Entries list
│       ├── sync.ts       # Sync status
│       └── ui.ts         # UI state
├── routes/               # SvelteKit pages
│   ├── +layout.svelte    # Root layout
│   ├── +page.svelte      # Journal list
│   ├── login/            # Login page
│   └── auth/callback/    # OAuth callback
├── app.css               # Global styles
└── service-worker.ts     # PWA service worker
```

## Authentication Flow

Cognito uses Google OAuth 2.0 for authentication:

1. **Login**: User clicks "Sign in with Google" on `/login`
2. **OAuth Redirect**: Redirects to Google's consent screen
3. **Callback**: Google redirects to `/auth/callback` with auth code
4. **Token Exchange**: Backend exchanges code for user info and issues JWT
5. **Session**: JWT stored in HttpOnly cookie for secure access

### Protected Routes

All routes except `/login` and `/auth/callback` require authentication. Unauthenticated users are automatically redirected to the login page.

### Error Handling

Authentication errors (e.g., email not authorized, access denied) are displayed on the login page via URL parameters:
- `/login?error=not_authorized` - Email not in allowed list
- `/login?error=access_denied` - User cancelled login

## Design System

### Brand Colors

```css
--color-primary-dark: #1B3C53;   /* Headers, primary buttons */
--color-primary: #234C6A;         /* Interactive elements */
--color-primary-light: #456882;   /* Secondary elements */
--color-background: #E3E3E3;      /* Page backgrounds */
--color-surface: #FFFFFF;         /* Cards, inputs */
```

### Components

- **Primary Button**: `.btn-primary` - Main actions
- **Secondary Button**: `.btn-secondary` - Secondary actions
- **Surface**: `.surface` - Cards with shadow
- **Input Field**: `.input-field` - Form inputs

## Database Schema

### Entry

```typescript
{
  id: string;              // UUID
  date: string;            // YYYY-MM-DD
  conversations: [];       // Chat history
  refined_output: string;  // LLM summary
  status: 'active' | 'archived';
  version: number;         // For sync conflict resolution
}
```

### Goal

```typescript
{
  id: string;
  category: string;
  description: string;
  active: boolean;
}
```

## Components

### EntryCard

Reusable card component for displaying journal entries.

**Props:**
- `entry: Entry` - Entry object to display
- `onClick?: () => void` - Optional click handler

**Features:**
- Smart date formatting:
  - "Today" / "Yesterday" for recent dates (timezone-aware)
  - "December 24" for current year
  - "December 24, 2023" for past years
- Preview text truncation (150 chars max)
- Conversation count badge
- Interaction count display
- Status badge (active/archived) with color coding
- Relevance indicator (colored dot: green ≥0.8, yellow ≥0.5, gray <0.5)
- Relative time for last interaction ("1h ago", "2d ago")
- Click/keyboard navigation support

> **Timezone Fix**: Date strings are parsed as local dates to ensure "Today"/"Yesterday" work correctly across all timezones.

**Usage:**
```svelte
<script>
  import EntryCard from '$lib/components/EntryCard.svelte';
  
  function handleClick() {
    console.log('Entry clicked');
  }
</script>

<EntryCard {entry} onClick={handleClick} />
```

### PendingChange

Queue for offline changes to sync:

```typescript
{
  id: string;
  type: 'create' | 'update' | 'delete';
  entity: 'entry' | 'goal';
  entity_id: string;
  data: any;
  timestamp: string;
}
```

## API Integration

Configure backend URL in `.env`:

```bash
PUBLIC_API_URL=https://server.epicrunze.com/api
```

## Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

### Test Files (44 tests passing)

- `tests/lib/db.test.ts` - Database CRUD operations (12 tests)
- `tests/lib/stores.test.ts` - Store reactivity (8 tests)
- `tests/lib/entrycard-utils.test.ts` - EntryCard utility functions (15 tests)
  - Date formatting with timezone handling
  - Relative time calculations  
  - Text truncation
  - Relevance color mapping
- `tests/lib/auth-logic.test.ts` - Authentication logic (9 tests)
  - Error message handling
  - OAuth callback state parsing

All tests use vitest directly without component mounting, focusing on business logic and utility functions.

> **Note**: Component rendering tests will be added using E2E testing with Playwright in a future phase. Current tests focus on business logic and utility functions.

## Offline Support

The app works fully offline:

1. **Service Worker** caches app shell and assets
2. **IndexedDB** stores all data locally with Dexie.js
3. **Sync Queue** tracks changes made offline
4. **Auto-Sync** when network reconnects

### Sync Behavior

- Changes made offline are queued in `pendingChanges` table
- When online, sync is triggered automatically
- Conflict resolution uses version numbers
- User resolves overlapping changes via UI

## PWA Installation

The app can be installed on:
- Desktop (Chrome, Edge, Safari)
- Mobile (iOS Safari "Add to Home Screen", Android Chrome)

Manifest: `static/manifest.json`

## Development

### Adding a New Page

1. Create `src/routes/pagename/+page.svelte`
2. Add to navigation in `+layout.svelte`

### Adding a New Store

1. Create `src/lib/stores/storename.ts`
2. Export writable/derived stores
3. Use in components with `$storeName` syntax

### Adding Database Entity

1. Add interface to `src/lib/db/index.ts`
2. Add table to Dexie schema
3. Create CRUD module in `src/lib/db/`
4. Add tests in `tests/lib/db.test.ts`

## Troubleshooting

### Build Errors

- Ensure Node 20+ is active: `nvm use`
- Clear `.svelte-kit`: `rm -rf .svelte-kit`
- Reinstall: `rm -rf node_modules && npm install`

### IndexedDB Not Working

- Check browser DevTools > Application > IndexedDB
- Clear database: `await db.delete()`
- Fake-indexeddb used for tests automatically

## License

Private project for Cognito
