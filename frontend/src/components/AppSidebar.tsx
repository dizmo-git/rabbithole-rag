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
import { UploadSourceAlert } from "./UploadSourceAlert";
import { getNotebooks, getSourcesByNotebook } from "@/api/notebooks";
import { useEffect, useState } from "react";

export function AppSidebar() {
  const [notebookNames, setNotebookNames] = useState<string[]>([]);
  const [selectedNotebook, setSelectedNotebook] = useState<string>("");
  const [sources, setSources] = useState<string[]>([]);

  useEffect(() => {
    const fetchNotebooks = async () => {
      const names = await getNotebooks();
      setNotebookNames(names);
      setSelectedNotebook(names[0]);
    };

    fetchNotebooks();
  }, []);

  useEffect(() => {
    const fetchSources = async () => {
      const sources = await getSourcesByNotebook(selectedNotebook);
      setSources(sources);
    };

    fetchSources();
  }, [selectedNotebook]);

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader>
        <NotebookSwitcher
          versions={notebookNames}
          defaultVersion={notebookNames[0]}
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
        <UploadSourceAlert />
      </SidebarFooter>
    </Sidebar>
  );
}
