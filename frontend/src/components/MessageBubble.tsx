import { useState } from "react";
import { MessageRole, type Message } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { LuCheck, LuCopy, LuPencil, LuRefreshCw } from "react-icons/lu";
import { CitationList } from "./CitationList";
import { Button } from "./ui/button";
import { Spinner } from "./ui/spinner";
import { Textarea } from "./ui/textarea";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";

export interface MessageBubbleProps {
  message: Message;
  // the answer currently being streamed into (last message while isStreaming)
  isPending?: boolean;
  // set only where the action applies: regenerate on the last answer, edit on user
  // messages while nothing streams
  onRegenerate?: () => void;
  onEdit?: (text: string) => void;
}

const DEBUG_MARKDOWN = false;
const TEST_MARKDOWN = `# Heading One
## Heading Two

This is a paragraph with **bold text**, *italic text*, and \`inline code\`. Here's a [link](https://example.com) too.

### Code block

\`\`\`typescript
function greet(name: string): string {
  return \`Hello, \${name}!\`;
}
\`\`\`

### Lists

Unordered:
- First item
- Second item
  - Nested item
- Third item

Ordered:
1. Step one
2. Step two
3. Step three

### Blockquote

> This is a blockquote. Useful for testing quote styling.

### Table

| Name | Role | Active |
|------|------|--------|
| Alice | Admin | true |
| Bob | User | false |

---

That horizontal rule above should render too. And here's a longer paragraph to check line height and paragraph spacing: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
`;


export default function MessageBubble({
  message,
  isPending = false,
  onRegenerate,
  onEdit,
}: MessageBubbleProps) {
  const isUser = message.role === MessageRole.User;
  const [editing, setEditing] = useState(false);

  const content =
    DEBUG_MARKDOWN && !isUser ? TEST_MARKDOWN : message.content;

  if (isUser) {
    return (
      <div className="group flex w-full max-w-3xl mx-auto mb-4 px-4 justify-end">
        {editing && onEdit ? (
          <EditBox
            initial={message.content}
            onCancel={() => setEditing(false)}
            onSave={(text) => {
              setEditing(false);
              onEdit(text);
            }}
          />
        ) : (
          <div className="flex flex-col items-end max-w-[75%]">
            <div className="px-4 py-2.5 shadow-sm bg-accent text-accent-foreground rounded-2xl rounded-tr-sm">
              <p className="text-sm whitespace-pre-wrap break-words">
                {message.content}
              </p>
            </div>
            <ActionRow>
              <CopyButton text={message.content} />
              {onEdit && (
                <ActionButton label="Edit" onClick={() => setEditing(true)}>
                  <LuPencil />
                </ActionButton>
              )}
            </ActionRow>
          </div>
        )}
      </div>
    );
  }

  // Assistant: full width, no bubble, so long answers read like a document
  const waiting = isPending && !message.content && !message.error;

  return (
    <div className="group w-full max-w-3xl mx-auto mb-6 px-4">
      {waiting ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Searching sources…
        </div>
      ) : (
        message.content && (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={{
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )
      )}
      {message.error && (
        <p className="text-sm text-destructive">
          Couldn't get an answer: {message.error}
        </p>
      )}
      {message.stopped && (
        <p className="mt-1 text-xs italic text-muted-foreground">Stopped</p>
      )}
      {message.citations && <CitationList citations={message.citations} />}
      {!isPending && (message.content || onRegenerate) && (
        <ActionRow>
          {message.content && <CopyButton text={message.content} />}
          {onRegenerate && (
            <ActionButton label="Regenerate" onClick={onRegenerate}>
              <LuRefreshCw />
            </ActionButton>
          )}
        </ActionRow>
      )}
    </div>
  );
}

// Shown on hover (or keyboard focus) under a message
function ActionRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-1 flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
      {children}
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon-xs"
          aria-label={label}
          onClick={onClick}
          className="text-muted-foreground"
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <ActionButton label={copied ? "Copied" : "Copy"} onClick={copy}>
      {copied ? <LuCheck /> : <LuCopy />}
    </ActionButton>
  );
}

function EditBox({
  initial,
  onSave,
  onCancel,
}: {
  initial: string;
  onSave: (text: string) => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState(initial);
  const canSave = !!text.trim() && text.trim() !== initial.trim();

  return (
    <div className="flex w-full max-w-[75%] flex-col gap-2">
      <Textarea
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") onCancel();
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            if (canSave) onSave(text.trim());
          }
        }}
      />
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button size="sm" disabled={!canSave} onClick={() => onSave(text.trim())}>
          Send
        </Button>
      </div>
    </div>
  );
}
