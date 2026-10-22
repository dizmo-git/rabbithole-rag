export interface Notebook {
  name: string;
}

// mirrors backend/settings.py AppSettings
export interface AppSettings {
  chat_model: string;
  embedding_model: string; // default for new notebooks, existing ones keep theirs
}

export interface OllamaModel {
  name: string;
  family: string | null;
  parameter_size: string | null;
  capabilities: string[]; // e.g. ["completion"] or ["embedding"], empty on old Ollama
}

export interface Source {
  id: string;
  notebook_id: string;
  source_type: "file" | "post";
  filename: string | null;
  file_path: string | null;
  url: string | null;
  uploaded_at: Date;
  status: "pending" | "processed" | "failed";
  error: string | null; // why ingestion failed, set together with "failed"
}

export interface Citation {
  id: string;
  source_type: string;
  score: number;
  title: string;
  content: string;
  links: string[]; // original posts this chunk came from (empty for files)
}

export interface Message {
  role: MessageRoleType;
  content: string;
  citations?: Citation[];
  // UI-only, never sent to the backend (see api/llm.ts)
  error?: string; // the request failed, shown instead of the answer
  stopped?: boolean; // the user pressed Stop, content is partial
}

export type MessageRoleType = (typeof MessageRole)[keyof typeof MessageRole];

export const MessageRole = {
  User: "user",
  Assistant: "assistant",
} as const;
