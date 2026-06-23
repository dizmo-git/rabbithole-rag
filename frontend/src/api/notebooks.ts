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

export const addSourceToNotebook = async (name: string): Promise<string> => {
  const res = await api.post<string>("/sources/add/", null, {
    params: { notebook_name: name },
  });
  return res.data;
};
