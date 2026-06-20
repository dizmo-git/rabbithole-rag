import api from "./client";

export const getNotebooks = async (): Promise<string[]> => {
  const res = await api.get<{ names: string[] }>("/notebooks");
  return res.data.names;
};
