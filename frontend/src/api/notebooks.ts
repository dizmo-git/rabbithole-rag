import type { Notebook, Source } from "@/types";
import api from "./client";

export const getNotebooks = async (): Promise<string[]> => {
  const res = await api.get<{ names: string[] }>("/notebooks/");
  return res.data.names;
};

export const getSourcesByNotebook = async (name: string): Promise<Source[]> => {
  const res = await api.get<Source[]>("/sources/", {
    params: { notebook: name },
  });
  return res.data;
};

export const addSourceToNotebook = async (name: string): Promise<Source> => {
  const res = await api.post<Source>("/sources/add/", null, {
    params: { notebook_name: name },
  });
  return res.data;
};

export const newNotebook = async (name: string): Promise<string> => {
  const res = await api.post<Notebook>("/notebooks/new", null, {
    params: { name: name },
  });
  return res.data.name;
};
