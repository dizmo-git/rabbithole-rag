export interface Notebook {
  name: string;
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
