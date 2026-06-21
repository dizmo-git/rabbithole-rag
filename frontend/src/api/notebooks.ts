import api from "./client";

export const getNotebooks = async (): Promise<string[]> => {
  const res = await api.get<{ names: string[] }>("/notebooks/");
  return res.data.names;
};

export const getSourcesByNotebook = async (name: string): Promise<string[]> => {
  const res = await api.get<{ sources: string[] }>("/sources/", {
    params: { notebook: name },
  });
  return res.data.sources;
};
