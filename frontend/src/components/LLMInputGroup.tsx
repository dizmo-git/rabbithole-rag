import TextareaAutosize from "react-textarea-autosize";
import { useRef, useState } from "react";
import { LuArrowUp, LuSquare } from "react-icons/lu";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
} from "@/components/ui/input-group";
import { useNotebook } from "./NotebookProvider";

type LLMInputGroupProps = {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
};

export function LLMInputGroup({
  isStreaming,
  onSend,
  onStop,
}: LLMInputGroupProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { selectedNotebook } = useNotebook();

  // Typing is allowed while an answer streams, sending is not
  const canSend = !isStreaming && !!text.trim() && !!selectedNotebook;

  function submit() {
    if (!canSend) return;
    onSend(text.trim());
    setText("");
    textareaRef.current?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter is a newline. isComposing: Enter confirming an IME candidate
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex justify-center px-4 pb-4">
      <div className="w-full max-w-3xl">
        {/* Solid card that looks the same focused or not. The default InputGroup is
            translucent gray in dark mode, grows a focus ring, and fades out entirely
            (has-disabled) whenever the Send button is disabled, i.e. on empty input */}
        <InputGroup className="rounded-2xl border-border bg-card shadow-sm dark:bg-card has-disabled:bg-card has-disabled:opacity-100 dark:has-disabled:bg-card has-[[data-slot=input-group-control]:focus-visible]:border-border has-[[data-slot=input-group-control]:focus-visible]:ring-0">
          <TextareaAutosize
            ref={textareaRef}
            autoFocus
            data-slot="input-group-control"
            className="flex field-sizing-content min-h-16 max-h-60 w-full resize-none rounded-md bg-transparent px-3 py-2.5 text-base transition-[color,box-shadow] outline-none md:text-sm"
            placeholder={
              selectedNotebook ? "Ask anything..." : "Select a notebook first"
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <InputGroupAddon align="block-end">
            {isStreaming ? (
              <InputGroupButton
                onClick={onStop}
                aria-label="Stop"
                className="ml-auto rounded-full"
                size="icon-sm"
                variant="default"
              >
                <LuSquare className="size-3 fill-current" />
              </InputGroupButton>
            ) : (
              <InputGroupButton
                onClick={submit}
                disabled={!canSend}
                aria-label="Send"
                className="ml-auto rounded-full"
                size="icon-sm"
                variant="default"
              >
                <LuArrowUp />
              </InputGroupButton>
            )}
          </InputGroupAddon>
        </InputGroup>
      </div>
    </div>
  );
}
