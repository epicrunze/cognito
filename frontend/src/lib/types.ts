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
  system_prompt_override: string | null;
}

export interface LabelDescription {
  label_id: number;
  title: string;
  description: string;
  created_at?: string;
  updated_at?: string;
}

export interface LabelStats {
  [label_id: number]: { total: number; done: number; open: number };
}

export interface ChatAction {
  type: 'create' | 'complete' | 'update' | 'move' | 'delete';
  task_id: number;
  title?: string;
  task_title?: string;
  fields?: string[];
  project_id?: number;
  changes?: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  proposals?: TaskProposal[];
  actions?: ChatAction[];
}

export interface ChatSession {
  conversation_id: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

// Google Calendar types

export interface GoogleCalendar {
  id: string;
  summary: string;
  background_color: string;
  primary: boolean;
  enabled: boolean;
}

export interface CalendarEvent {
  id: string;
  summary: string;
  start: string; // ISO datetime
  end: string; // ISO datetime
  description?: string | null;
  html_link?: string | null;
  task_id?: number | null; // linked Cognito task
  calendar_id?: string | null;
  calendar_color?: string | null;
  calendar_name?: string | null;
}

export interface ScheduleSuggestion {
  task_id: number;
  task_title: string;
  suggested_start: string;
  suggested_end: string;
  reason: string;
}

export interface Revision {
  id: number;
  task_id: number;
  action_type: 'create' | 'update' | 'complete' | 'move' | 'delete' | 'auto_tag';
  source: 'chat' | 'proposal' | 'auto_tag' | 'manual';
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  changes: Record<string, unknown> | null;
  conversation_id: string | null;
  proposal_id: string | null;
  undone: boolean;
  undone_at: string | null;
  created_at: string;
}
