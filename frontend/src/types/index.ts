export interface Notebook {
  name: string;
}

export interface Source {
  id: string;
  notebook_id: string;
  filename: string;
  file_path: string;
  uploaded_at: Date;
  status: string;
}

export interface Message {
  role: MessageRoleType;
  text: string;
}

export type MessageRoleType = (typeof MessageRole)[keyof typeof MessageRole];

export const MessageRole = {
  User: "user",
  Assistant: "assistant",
} as const;
