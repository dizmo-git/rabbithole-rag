import type { AppSettings, OllamaModel } from "@/types";
import { isAxiosError } from "axios";
import api from "./client";

export const getSettings = async (): Promise<AppSettings> => {
  const res = await api.get<AppSettings>("/settings/");
  return res.data;
};

export const updateSettings = async (
  settings: AppSettings,
): Promise<AppSettings> => {
  const res = await api.put<AppSettings>("/settings/", settings);
  return res.data;
};

export const getModels = async (): Promise<OllamaModel[]> => {
  const res = await api.get<OllamaModel[]>("/settings/models");
  return res.data;
};

// Turns a failed settings/models request into something to show the user
export const modelErrorMessage = (err: unknown): string => {
  if (isAxiosError(err)) {
    if (err.response?.status === 503) return "Can't reach Ollama. Is it running?";
    if (err.response?.data?.detail) return String(err.response.data.detail);
  }
  return "Something went wrong";
};
