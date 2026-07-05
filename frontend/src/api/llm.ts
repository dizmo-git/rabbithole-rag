import type { Message } from "@/types";
import api from "./client";

export const ask = async (
  messages: Message[],
  notebook: string,
): Promise<string> => {
  const res = await api.post<{ answer: string }>("/query/", messages, {
    params: { notebook: notebook },
  });
  return res.data.answer;
};
