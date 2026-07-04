import Layout from "./components/Layout";
import { LLMInputGroup } from "./components/LLMInputGroup";
import { NotebookProvider } from "./components/NotebookProvider";
import { ScrollArea } from "./components/ui/scroll-area";
import MessageBubble from "./components/MessageBubble";
import { useState } from "react";
import { type Message } from "./types";
import Separator from "./components/Separator";
import { ChatSettingsDropdown } from "./components/ChatSettingsDropdown";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);

  return (
    <NotebookProvider>
      <Layout
        headerActions={<ChatSettingsDropdown onClear={() => setMessages([])} />}
      >
        <ScrollArea className="flex-1 min-h-0 pb-4">
          <div className="flex flex-col">
            {messages?.map((m) => (
              <MessageBubble input={m.text} role={m.role} />
            ))}
          </div>
        </ScrollArea>
        <Separator />
        <LLMInputGroup messages={messages} setMessages={setMessages} />
      </Layout>
    </NotebookProvider>
  );
}
