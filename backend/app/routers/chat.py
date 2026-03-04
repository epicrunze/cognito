"""
Router: /api/chat

Conversational extraction endpoint (Spec §3.3).
Supports multi-turn chat sessions where the user can refine task extraction
through natural language conversation with the AI agent.

TODO:
- POST /api/chat — start or continue a chat session
- POST /api/chat/{session_id}/messages — send a message in an existing session
- GET /api/chat/{session_id} — retrieve chat history
- DELETE /api/chat/{session_id} — end/clear a session
- SSE streaming support for real-time AI responses
- Session state management (in-memory or DB-backed)
"""

# TODO: Implement chat router
