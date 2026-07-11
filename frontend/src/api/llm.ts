import type { Message } from "@/types";

export const ask = async function (
  messages: Message[],
  notebook: string,
  onChunk: (delta: string) => void,
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

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    onChunk(chunk);
  }
};
