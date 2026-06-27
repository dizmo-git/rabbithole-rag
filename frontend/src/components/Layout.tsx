import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <main className="flex flex-col h-screen">
          <SidebarTrigger />
          <div className="flex flex-col flex-1 min-h-0">{children}</div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
