import api from "./client";

export const ask = async (input: string): Promise<string> => {
  const res = await api.get<{ answer: string }>("/ask/", {
    params: { question: input },
  });
  return res.data.answer;
};
