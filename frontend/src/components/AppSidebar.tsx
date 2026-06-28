import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarHeader,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { NotebookSwitcher } from "./NotebookSwitcher";
import {
  addSourceToNotebook,
  getNotebooks,
  getSourcesByNotebook,
} from "@/api/notebooks";
import { useEffect, useRef, useState } from "react";
import { useNotebook } from "./NotebookProvider";
import { UploadSourceButton } from "./UploadSourceButton";
import { NewNotebookAlert } from "./NewNotebookAlert";
import type { Source } from "@/types";
import { Spinner } from "./ui/spinner";

export function AppSidebar() {
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [notebookNames, setNotebookNames] = useState<string[]>([]);
  const { selectedNotebook, setSelectedNotebook } = useNotebook();
  const [sources, setSources] = useState<Source[]>([]);

  const fetchSources = async () => {
    const sources = await getSourcesByNotebook(selectedNotebook);
    setSources(sources);
    return sources;
  };

  const fetchNotebooks = async () => {
    const names = await getNotebooks();
    setNotebookNames(names);
    return names;
  };

  const handleUploadSource = async () => {
    if (!selectedNotebook) return;
    const newSource = await addSourceToNotebook(selectedNotebook);
    setSources((prev) => [...prev, newSource]);
    startPolling();
  };

  useEffect(() => {
    const fetch = async () => {
      const names = await fetchNotebooks();
      setSelectedNotebook(names[0]);
    };

    fetch();
  }, []);

  useEffect(() => {
    if (!selectedNotebook) return;
    fetchSources();
  }, [selectedNotebook]);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const startPolling = () => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      const sources = await fetchSources();
      if (!sources.some((s) => s.status === "pending")) {
        stopPolling();
      }
    }, 2500);
  };

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader>
        <NewNotebookAlert onCreated={fetchNotebooks} />
        <NotebookSwitcher
          versions={notebookNames}
          defaultVersion={selectedNotebook}
          onSelect={setSelectedNotebook}
        />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Sources</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {sources.map((source) => (
                <SidebarMenuItem key={source.id}>
                  <SidebarMenuButton title={source.filename}>
                    {source.status === "pending" && <Spinner />}
                    {source.filename}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <UploadSourceButton onClick={handleUploadSource} />
        {/* <UploadSourceAlert /> */}
      </SidebarFooter>
    </Sidebar>
  );
}
