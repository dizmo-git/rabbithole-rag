import { MessageRole, type MessageRoleType } from "@/types";

export interface MessageBubbleProps {
  input: string;
  role: MessageRoleType;
}

export default function MessageBubble({ input, role }: MessageBubbleProps) {
  const isUser = role === MessageRole.User;

  const bubbleWrapper = `
    flex w-full max-w-6xl mx-auto mb-4 px-4 
    ${isUser ? "justify-end" : "justify-start"}
  `;

  const bubbleBox = `
    max-w-[75%] 
    px-4 py-2.5 
    shadow-sm
    bg-accent text-accent-foreground
    rounded-2xl 
    ${isUser ? "rounded-tr-sm" : "rounded-tl-sm"}
  `;

  return (
    <div className={bubbleWrapper}>
      <div className={bubbleBox}>
        <p className="text-sm leading-relaxed whitespace-pre-wrap break-all">
          {input}
        </p>
      </div>
    </div>
  );
}
