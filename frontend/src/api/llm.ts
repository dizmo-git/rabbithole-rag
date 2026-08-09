import type { Message, Citation } from "@/types";

export const ask = async function (
  messages: Message[],
  notebook: string,
  onChunk: (delta: string) => void,
  onCitations: (citations: Citation[]) => void,
) {
  const response = await fetch(
    `query/?notebook=${encodeURIComponent(notebook)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(messages),
    },
  );

  if (!response.body) throw Error("No response body!");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let buffer = "";
  let citationsParsed = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });

    if (!citationsParsed) {
      buffer += chunk;
      const newlineIdx = buffer.indexOf("\n");
      if (newlineIdx === -1) continue;

      const citationsLine = buffer.slice(0, newlineIdx);
      onCitations(JSON.parse(citationsLine).sources);
      citationsParsed = true;

      const rest = buffer.slice(newlineIdx + 1);
      buffer = "";
      if (rest) onChunk(rest);
      continue;
    }

    onChunk(chunk);
  }
};
