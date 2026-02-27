# Cognito — Task Agent

An AI integration layer for Vikunja project management.

Turns unstructured inputs (meeting notes, emails, ideas) into structured Vikunja tasks via LLM extraction with tool-calling. Built with FastAPI + SvelteKit.

## Status

🚧 **In development** — see [`new-cognito-spec.md`](./new-cognito-spec.md) for the full technical specification.

## Stack

- **Backend:** FastAPI (Python), SQLite, Google OAuth
- **Frontend:** SvelteKit (static build, served via nginx)
- **LLM:** Gemini API (general) / Ollama with Qwen 3.x (confidential)
- **PM:** Vikunja (self-hosted)

## Archive

Previous codebase (thought journal PWA) is preserved on the [`archive/thought-journal`](https://github.com/epicrunze/cognito/tree/archive/thought-journal) branch.
