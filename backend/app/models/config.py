"""
Pydantic model: AgentConfig (Spec §2.2)

Represents per-user agent configuration stored in the `agent_config` table.
Controls LLM behaviour, default project, extraction preferences, etc.

TODO:
- AgentConfig pydantic BaseModel with all fields from Spec §2.2
- AgentConfigUpdate partial model for PATCH requests
- Fields: default_project_id, llm_provider, llm_model, extraction_language,
          auto_approve, max_tasks_per_extraction, system_prompt_override
"""

# TODO: Implement AgentConfig model
