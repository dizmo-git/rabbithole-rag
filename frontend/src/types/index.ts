export interface Notebook {
  name: string;
}

export interface Source {
  id: string;
  notebook_id: string;
  source_type: "file" | "post";
  filename: string | null;
  file_path: string | null;
  url: string | null;
  uploaded_at: Date;
  status: string;
}

export interface Citation {
  id: string;
  source_type: string;
  score: number;
  title: string;
  content: string;
}

export interface Message {
  role: MessageRoleType;
  content: string;
  citations?: Citation[];
}

export type MessageRoleType = (typeof MessageRole)[keyof typeof MessageRole];

export const MessageRole = {
  User: "user",
  Assistant: "assistant",
} as const;
