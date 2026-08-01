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

export const addFileSourceToNotebook = async (
  name: string,
): Promise<Source> => {
  const res = await api.post<Source>("/sources/addfile/", null, {
    params: { notebook_name: name },
  });
  return res.data;
};

export const addLinkSourceToNotebook = async (
  link: string,
  name: string,
): Promise<Source> => {
  const res = await api.post<Source>("/sources/addlink/", null, {
    params: { link: link, notebook_name: name },
  });
  return res.data;
};

export const newNotebook = async (name: string): Promise<string> => {
  const res = await api.post<Notebook>("/notebooks/new", null, {
    params: { name: name },
  });
  return res.data.name;
};

export const deleteSource = async (
  id: string,
  notebook: string,
): Promise<void> => {
  await api.delete(`/sources/del/`, {
    params: { source_id: id, notebook_name: notebook },
  });
};

export const renameSource = async (
  id: string,
  notebook: string,
  newName: string,
): Promise<Source> => {
  const res = await api.patch<Source>("/sources/rename/", null, {
    params: { source_id: id, notebook_name: notebook, new_name: newName },
  });
  return res.data;
};
