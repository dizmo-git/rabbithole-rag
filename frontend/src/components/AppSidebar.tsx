import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarHeader,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { NotebookSwitcher } from "./NotebookSwitcher";
import {
  addFileSourceToNotebook,
  addLinkSourceToNotebook,
  deleteSource,
  getNotebooks,
  getSourcesByNotebook,
  renameSource,
} from "@/api/notebooks";
import { useEffect, useRef, useState } from "react";
import { useNotebook } from "./NotebookProvider";
import { NewNotebookAlert } from "./NewNotebookAlert";
import type { Source } from "@/types";
import { SourceItem } from "./SourceItem";
import { UploadSourceAlert } from "./UploadSourceAlert";
import { RenameSourceDialog } from "./RenameSourceDialog";

export function AppSidebar() {
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [notebookNames, setNotebookNames] = useState<string[]>([]);
  const { selectedNotebook, setSelectedNotebook } = useNotebook();
  const [sources, setSources] = useState<Source[]>([]);
  const [renameTarget, setRenameTarget] = useState<Source | null>(null);

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

  const handleUploadFileSource = async () => {
    if (!selectedNotebook) return;
    const newSource = await addFileSourceToNotebook(selectedNotebook);
    setSources((prev) => [...prev, newSource]);
    startPolling();
  };

  const handleUploadLinkSource = async (link: string) => {
    if (!selectedNotebook) return;
    const newSource = await addLinkSourceToNotebook(link, selectedNotebook);
    setSources((prev) => [...prev, newSource]);
    startPolling();
  };

  const handleDeleteSource = async (source: Source) => {
    try {
      await deleteSource(source.id, selectedNotebook);
      setSources((prev) => prev.filter((s) => s.id !== source.id));
    } catch (err) {
      console.error("Failed to delete source", err);
    }
  };

  const handleConfirmRename = async (source: Source, newName: string) => {
    try {
      const updated = await renameSource(source.id, selectedNotebook, newName);
      setSources((prev) =>
        prev.map((s) => (s.id === updated.id ? updated : s)),
      );
    } catch (err) {
      console.error("Failed to rename source", err);
    } finally {
      setRenameTarget(null);
    }
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
                <SourceItem
                  key={source.id}
                  source={source}
                  onRename={setRenameTarget}
                  onDelete={handleDeleteSource}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <UploadSourceAlert
          onFile={handleUploadFileSource}
          onLink={handleUploadLinkSource}
        />
      </SidebarFooter>
      <RenameSourceDialog
        source={renameTarget}
        open={renameTarget !== null}
        onOpenChange={(open) => !open && setRenameTarget(null)}
        onConfirm={handleConfirmRename}
      />
    </Sidebar>
  );
}
