import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";

export default function Layout({
  children,
  headerActions,
}: {
  children: React.ReactNode;
  headerActions?: React.ReactNode;
}) {
  return (
    <SidebarProvider
      style={{ "--sidebar-width": "24rem" } as React.CSSProperties}
    >
      <AppSidebar />
      <SidebarInset>
        <main className="flex flex-col h-screen">
          <div className="flex flex-row items-center">
            <SidebarTrigger size="icon-lg" />
            <div className="ml-auto">{headerActions}</div>
          </div>
          <div className="flex flex-col flex-1 min-h-0">{children}</div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
