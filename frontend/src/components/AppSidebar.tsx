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
import { useEffect, useState } from "react";
import { useNotebook } from "./NotebookProvider";
import { UploadSourceButton } from "./UploadSourceButton";
import { NewNotebookAlert } from "./NewNotebookAlert";

export function AppSidebar() {
  const [notebookNames, setNotebookNames] = useState<string[]>([]);
  const { selectedNotebook, setSelectedNotebook } = useNotebook();
  const [sources, setSources] = useState<string[]>([]);

  const fetchSources = async () => {
    const sources = await getSourcesByNotebook(selectedNotebook);
    setSources(sources);
  };

  const fetchNotebooks = async () => {
    const names = await getNotebooks();
    setNotebookNames(names);
    return names;
  };

  const handleUploadSource = async () => {
    if (!selectedNotebook) return;
    await addSourceToNotebook(selectedNotebook);
    await fetchSources();
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
                <SidebarMenuItem key={source}>
                  <SidebarMenuButton title={source}>{source}</SidebarMenuButton>
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
