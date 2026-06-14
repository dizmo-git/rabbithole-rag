import TextareaAutosize from "react-textarea-autosize";
import { useState } from "react";
import api from "./api";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
} from "@/components/ui/input-group";

export function LLMInputGroup() {
  const [text, setText] = useState("");

  async function askAssistant(input: string) {
    if (!input) {
      alert("Input is empty");
      return;
    }

    const response = await api.get("/ask/", { params: { question: input } });
    alert(response.data.answer);
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
