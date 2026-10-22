import { useRef, useState } from "react";
import { ask } from "@/api/llm";
import { MessageRole, type Message } from "@/types";

// Chat state for the single global conversation (not tied to a notebook on purpose:
// switching notebooks keeps the chat, the user clears it from the header menu).
export function useChat(notebook: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  // Patch the trailing assistant message (the one being streamed into)
  const updateLast = (patch: (m: Message) => Partial<Message>) =>
    setMessages((prev) => {
      if (!prev.length) return prev; // cleared mid-stream
      const next = [...prev];
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, ...patch(last) };
      return next;
    });

  // Show `history` plus an empty assistant message and stream the answer into it.
  // `history` must end with the user message being answered.
  const run = async (history: Message[]) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setMessages([...history, { role: MessageRole.Assistant, content: "" }]);
    setIsStreaming(true);

    // Failed or empty answers are noise for the LLM, leave them out of the context
    const context = history.filter(
      (m) => m.role === MessageRole.User || (m.content && !m.error),
    );

    // Regenerate/edit abort the previous request and reuse the trailing slot,
    // so a superseded request must not touch it anymore
    const isCurrent = () => controllerRef.current === controller;

    try {
      await ask(
        context,
        notebook,
        (delta) =>
          isCurrent() && updateLast((m) => ({ content: m.content + delta })),
        (citations) => isCurrent() && updateLast(() => ({ citations })),
        controller.signal,
      );
    } catch (e) {
      if (!isCurrent()) return;
      if (controller.signal.aborted) {
        updateLast(() => ({ stopped: true }));
      } else {
        updateLast(() => ({
          error: e instanceof Error ? e.message : String(e),
        }));
      }
    } finally {
      if (isCurrent()) {
        controllerRef.current = null;
        setIsStreaming(false);
      }
    }
  };

  const send = (text: string) =>
    run([...messages, { role: MessageRole.User, content: text }]);

  const stop = () => controllerRef.current?.abort();

  // Re-ask the last question, replacing the last answer
  const regenerate = () => {
    const lastUser = messages.findLastIndex((m) => m.role === MessageRole.User);
    if (lastUser !== -1) run(messages.slice(0, lastUser + 1));
  };

  // Replace the user message at `index` and drop everything after it
  const editAndResend = (index: number, text: string) =>
    run([...messages.slice(0, index), { role: MessageRole.User, content: text }]);

  const clear = () => {
    stop();
    setMessages([]);
  };

  return { messages, isStreaming, send, stop, regenerate, editAndResend, clear };
}
