import TextareaAutosize from "react-textarea-autosize";
import { useState } from "react";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
} from "@/components/ui/input-group";
import { ask } from "@/api/llm";
import { useNotebook } from "./NotebookProvider";
import { MessageRole, type Message } from "@/types";

type LLMInputGroupProps = {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
};

export function LLMInputGroup({ messages, setMessages }: LLMInputGroupProps) {
  const [text, setText] = useState("");
  const { selectedNotebook } = useNotebook();

  async function askAssistant(input: string) {
    if (!input) {
      alert("Input is empty");
      return;
    }

    const newMessage: Message = { text: input, role: MessageRole.User };
    setMessages((prev) => [...prev, newMessage]);
    const answer: Message = {
      text: await ask(input, selectedNotebook),
      role: MessageRole.Assistant,
    };
    setMessages((prev) => [...prev, answer]);
  }

  return (
    <div className="flex justify-center px-4 pb-4">
      <div className="w-full max-w-2xl">
        <InputGroup>
          <TextareaAutosize
            data-slot="input-group-control"
            className="flex field-sizing-content min-h-16 w-full resize-none rounded-md bg-transparent px-3 py-2.5 text-base transition-[color,box-shadow] outline-none md:text-sm"
            placeholder="Ask anything..."
            onChange={(e) => setText(e.target.value)}
          />
          <InputGroupAddon align="block-end">
            <InputGroupButton
              onClick={async () => {
                await askAssistant(text);
              }}
              className="ml-auto"
              size="sm"
              variant="default"
            >
              Submit
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
      </div>
    </div>
  );
}
