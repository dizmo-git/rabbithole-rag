import Layout from "./components/Layout";
import { LLMInputGroup } from "./components/LLMInputGroup";
import { NotebookProvider } from "./components/NotebookProvider";
import { ScrollArea } from "./components/ui/scroll-area";
import MessageBubble, { MessageRole } from "./components/MessageBubble";

export default function App() {
  return (
    <NotebookProvider>
      <Layout>
        <ScrollArea>
          <MessageBubble input="Hello world!" role={MessageRole.User} />
          <MessageBubble input="Hello user!" role={MessageRole.Assistant} />
        </ScrollArea>
        <LLMInputGroup />
      </Layout>
    </NotebookProvider>
  );
}
