import React, { useContext, createContext, useState } from "react";

const NotebookContext = createContext<{
  selectedNotebook: string;
  setSelectedNotebook: (name: string) => void;
}>({ selectedNotebook: "", setSelectedNotebook: () => {} });

export function NotebookProvider({ children }: { children: React.ReactNode }) {
  const [selectedNotebook, setSelectedNotebook] = useState("");
  return (
    <NotebookContext.Provider value={{ selectedNotebook, setSelectedNotebook }}>
      {children}
    </NotebookContext.Provider>
  );
}

export const useNotebook = () => useContext(NotebookContext);
