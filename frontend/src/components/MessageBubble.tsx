import { MessageRole, type MessageRoleType } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";

export interface MessageBubbleProps {
  input: string;
  role: MessageRoleType;
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

  const content = DEBUG_MARKDOWN && !isUser ? TEST_MARKDOWN : input;

  return (
    <div className={bubbleWrapper}>
      <div className={bubbleBox}>
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
      </div>
    </div>
  );
}
