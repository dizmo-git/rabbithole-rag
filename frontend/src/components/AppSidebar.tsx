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
import { getNotebooks } from "@/api/notebooks";
import { useEffect, useState } from "react";

export function AppSidebar() {
  const [notebookNames, setNotebookNames] = useState<string[]>([]);

  useEffect(() => {
    const fetchNotebooks = async () => {
      const names = await getNotebooks();
      setNotebookNames(names);
    };

    fetchNotebooks();
  }, []);

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader>
        <NotebookSwitcher
          versions={notebookNames}
          defaultVersion={notebookNames[0]}
        />
        <p className="text-sm font-semibold p-2">Sources</p>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Notebooks</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton>Notebook 1</SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton>Notebook 2</SidebarMenuButton>
              </SidebarMenuItem>
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
