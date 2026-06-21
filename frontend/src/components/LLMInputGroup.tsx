import TextareaAutosize from "react-textarea-autosize";
import { useState } from "react";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
} from "@/components/ui/input-group";
import { ask } from "@/api/llm";
import { useNotebook } from "./NotebookProvider";

export function LLMInputGroup() {
  const [text, setText] = useState("");
  const { selectedNotebook } = useNotebook();

  async function askAssistant(input: string) {
    if (!input) {
      alert("Input is empty");
      return;
    }

    const answer = await ask(input, selectedNotebook);
    alert(answer);
  }

  return (
    <div className="grid w-1/2 max-w-sm gap-6">
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
  );
}
