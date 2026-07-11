import type { Source } from "@/types";
import {
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "./ui/sidebar";
import { Spinner } from "./ui/spinner";
import { LuEllipsisVertical } from "react-icons/lu";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

interface SourceItemProps {
  source: Source;
  onRename?: (source: Source) => void;
  onDelete?: (source: Source) => void;
}

export function SourceItem({ source, onRename, onDelete }: SourceItemProps) {
  const isPending = source.status === "pending";

  return (
    <SidebarMenuItem className="relative rounded-md group/item hover:bg-accent hover:text-accent-foreground transition-colors">
      <SidebarMenuButton
        title={source.filename}
        disabled={isPending}
        className="pr-8 hover:bg-transparent"
      >
        <span className="truncate">{source.filename}</span>
      </SidebarMenuButton>

      {isPending ? (
        <Spinner className="absolute right-2 top-1/2 -translate-y-1/2 size-4" />
      ) : (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuAction className="opacity-0 group-hover/item:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100 transition-opacity shrink-0">
              <LuEllipsisVertical />
            </SidebarMenuAction>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="right" align="start">
            <DropdownMenuItem onClick={() => onRename?.(source)}>
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onClick={() => onDelete?.(source)}
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </SidebarMenuItem>
  );
}
