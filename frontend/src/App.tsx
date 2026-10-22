import Layout from "./components/Layout";
import { LLMInputGroup } from "./components/LLMInputGroup";
import { NotebookProvider, useNotebook } from "./components/NotebookProvider";
import { ScrollArea } from "./components/ui/scroll-area";
import { TooltipProvider } from "./components/ui/tooltip";
import { Button } from "./components/ui/button";
import MessageBubble from "./components/MessageBubble";
import { useLayoutEffect, useRef, useState } from "react";
import { MessageRole } from "./types";
import Separator from "./components/Separator";
import { ChatSettingsDropdown } from "./components/ChatSettingsDropdown";
import { useChat } from "./hooks/useChat";
import { LuArrowDown, LuMessagesSquare } from "react-icons/lu";

// How close (px) to the bottom still counts as "at the bottom" for auto-follow
const FOLLOW_THRESHOLD = 80;

export default function App() {
  return (
    <NotebookProvider>
      <TooltipProvider>
        <Chat />
      </TooltipProvider>
    </NotebookProvider>
  );
}

function Chat() {
  const { selectedNotebook } = useNotebook();
  const chat = useChat(selectedNotebook);
  const { messages, isStreaming } = chat;

  const viewportRef = useRef<HTMLDivElement>(null);
  // Follow the stream only while the user is at the bottom, so scrolling up to
  // read isn't undone by the next token
  const followRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = (behavior: ScrollBehavior = "auto") => {
    const el = viewportRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior });
  };

  const onScroll = () => {
    const el = viewportRef.current;
    if (!el) return;
    const atBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < FOLLOW_THRESHOLD;
    followRef.current = atBottom;
    setShowJump(!atBottom);
  };

  useLayoutEffect(() => {
    if (followRef.current) scrollToBottom();
  }, [messages]);

  const send = (text: string) => {
    followRef.current = true; // a new question always jumps to the bottom
    chat.send(text);
  };

  const editAndResend = (index: number, text: string) => {
    followRef.current = true;
    chat.editAndResend(index, text);
  };

  const clear = () => {
    chat.clear();
    followRef.current = true;
    setShowJump(false);
  };

  const lastIndex = messages.length - 1;

  return (
    <Layout headerActions={<ChatSettingsDropdown onClear={clear} />}>
      {messages.length === 0 ? (
        <EmptyState notebook={selectedNotebook} />
      ) : (
        <div className="relative flex-1 min-h-0">
          <ScrollArea
            className="h-full"
            viewportRef={viewportRef}
            onViewportScroll={onScroll}
          >
            <div className="flex flex-col pt-4 pb-4">
              {messages.map((m, index) => {
                const isLast = index === lastIndex;
                const isUser = m.role === MessageRole.User;
                return (
                  <MessageBubble
                    key={index}
                    message={m}
                    isPending={isLast && isStreaming}
                    onRegenerate={
                      !isUser && isLast && !isStreaming
                        ? chat.regenerate
                        : undefined
                    }
                    onEdit={
                      isUser && !isStreaming
                        ? (text) => editAndResend(index, text)
                        : undefined
                    }
                  />
                );
              })}
            </div>
          </ScrollArea>
          {showJump && (
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Jump to latest"
              className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full shadow-md"
              onClick={() => scrollToBottom("smooth")}
            >
              <LuArrowDown />
            </Button>
          )}
        </div>
      )}
      <Separator />
      <LLMInputGroup
        isStreaming={isStreaming}
        onSend={send}
        onStop={chat.stop}
      />
    </Layout>
  );
}

function EmptyState({ notebook }: { notebook: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center text-muted-foreground">
      <LuMessagesSquare className="size-8" />
      {notebook ? (
        <>
          <p className="text-lg font-medium text-foreground">{notebook}</p>
          <p className="text-sm">Ask a question about this notebook's sources</p>
        </>
      ) : (
        <p className="text-sm">Select or create a notebook to start chatting</p>
      )}
    </div>
  );
}
