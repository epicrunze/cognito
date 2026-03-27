# Testing

## Architecture

- **Database**: In-memory SQLite (`sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)`)
- **Auth bypass**: `app.dependency_overrides[get_current_user] = lambda: mock_user`
- **HTTP mocking**: `respx.mock` for httpx (Vikunja client calls)
- **Async**: `asyncio_mode = "auto"` in `pyproject.toml` -- no `@pytest.mark.asyncio` needed

## Key Patterns

### `make_mock_db(conn)`
Helper in `conftest.py` that wraps an in-memory SQLite connection as a FastAPI dependency override for `get_db`.

### Monkeypatching
Patch `app.routers.MODULE.get_db` (not `app.database.get_db`) with `make_mock_db(conn)` for routers that use SQLite.

### LLM mocking
For chat tests, patch `app.services.llm.get_llm_client` (not `app.routers.chat.get_llm_client`) because the import happens inline.

### Vikunja mocking
Use `AsyncMock` for async vikunja methods or `respx.mock` for full HTTP-level mocking.

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_agent.py` | 11 | ChatAgent, modification tools |
| `test_chat.py` | 17 | Chat router, conversation flow |
| `test_config.py` | 9 | Config API CRUD |
| `test_extractor.py` | 14 | Task extraction pipeline |
| `test_ingest.py` | 4 | Ingest router, SSE streaming |
| `test_labels.py` | 12 | Label CRUD, descriptions, stats |
| `test_llm.py` | 9 | LLM clients, fallback |
| `test_project_management.py` | 10 | Project CRUD, kanban |
| `test_proposals.py` | 16 | Proposal queue, approve/reject |
| `test_revisions.py` | 13 | Task revision history |
| `test_schedule.py` | 11 | Google Calendar integration |
| `test_tasks.py` | 14 | Task CRUD proxy |
| `test_vikunja.py` | 17 | Vikunja client methods |
| **Total** | **157** | |

## Running Tests

```bash
cd backend
uv run pytest tests/ -v              # all tests
uv run pytest tests/test_agent.py -v  # single file
```
