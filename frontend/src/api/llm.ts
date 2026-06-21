import api from "./client";

export const ask = async (input: string, notebook: string): Promise<string> => {
  const res = await api.get<{ answer: string }>("/query/", {
    params: { question: input, notebook: notebook },
  });
  return res.data.answer;
};
