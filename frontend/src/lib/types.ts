// Vikunja API shapes (snake_case, matching API responses)

export interface User {
  id: number;
  email: string;
  name: string;
  picture: string | null;
}

export interface Label {
  id: number;
  title: string;
  hex_color: string;
}

export interface ProjectView {
  id: number;
  title: string;
  project_id: number;
  view_kind: 'list' | 'gantt' | 'table' | 'kanban';
  filter: string;
  bucket_configuration_mode: string;
  default_bucket_id: number;
  done_bucket_id: number;
  position: number;
}

export interface Project {
  id: number;
  title: string;
  description: string;
  identifier: string;
  hex_color: string;
  is_archived: boolean;
  is_favorite: boolean;
  parent_project_id: number | null;
  position: number;
  views: ProjectView[];
}

export interface Bucket {
  id: number;
  title: string;
  position: number;
  limit: number;
  project_view_id: number;
  count: number;
  tasks?: Task[];
  created_by: User;
  created: string;
  updated: string;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  done: boolean;
  done_at: string | null;
  priority: 0 | 1 | 2 | 3 | 4 | 5;
  due_date: string | null;
  start_date: string | null;
  end_date: string | null;
  project_id: number;
  labels: Label[];
  attachments: TaskAttachment[];
  percent_done: number;
  hex_color: string;
  repeat_after: number;
  repeat_mode: number;
  index: number;
  identifier: string; // read-only, e.g. "PHD-12"
  is_favorite: boolean;
  position: number;
  bucket_id: number;
  subtask_done?: number;
  subtask_total?: number;
  created_by: User | null;
  created: string;
  updated: string;
}

export interface AttachmentFile {
  id: number;
  name: string;
  mime: string;
  size: number;
  created: string;
}

export interface TaskAttachment {
  id: number;
  task_id: number;
  file: AttachmentFile;
  created: string;
  created_by: User;
}

export interface Subtask {
  id: number;
  title: string;
  done: boolean;
  priority: 0 | 1 | 2 | 3 | 4 | 5;
  created: string;
}

// Agent data types

export interface TaskProposal {
  id: string; // UUID
  source_id: string;
  title: string;
  description: string;
  project_name: string;
  project_id: number | null;
  priority: 1 | 2 | 3 | 4 | 5;
  due_date: string | null;
  estimated_minutes: number | null;
  labels: string[];
  source_type: 'notes' | 'email' | 'idea' | 'manual';
  source_text: string;
  confidential: boolean;
  status: 'pending' | 'approved' | 'rejected' | 'created';
  vikunja_task_id: number | null;
  gcal_event_id: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface AgentConfig {
  id: number;
  default_project_id: number | null;
  ollama_model: string;
  gemini_model: string;
  gcal_calendar_id: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  messages: ChatMessage[];
  created_at: string;
}
