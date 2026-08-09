import { useState } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Citation } from "@/types";

interface CitationListProps {
  citations: Citation[];
  limit?: number;
}

export function CitationList({ citations, limit = 3 }: CitationListProps) {
  if (!citations?.length) return null;

  const top = [...citations].sort((a, b) => b.score - a.score).slice(0, limit);

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2 ml-1">
      <span className="text-xs text-muted-foreground mr-0.5">Sources</span>
      {top.map((citation) => (
        <CitationButton key={citation.id} citation={citation} />
      ))}
    </div>
  );
}

function CitationButton({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className="flex h-6 min-w-6 items-center justify-center rounded-full
                     bg-muted px-2 text-xs font-medium text-muted-foreground
                     hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          {citation.score.toFixed(2)}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0" align="start">
        <div className="border-b px-3 py-2">
          <p className="text-sm font-medium truncate">
            {citation.title ?? "Untitled source"}
          </p>
          <p className="text-xs text-muted-foreground">
            {citation.source_type} · relevance {citation.score.toFixed(2)}
          </p>
        </div>
        <ScrollArea className="h-56 px-3 py-2">
          <p className="text-sm whitespace-pre-wrap">{citation.content}</p>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
