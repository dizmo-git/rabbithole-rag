import { useState } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { LuExternalLink } from "react-icons/lu";
import type { Citation } from "@/types";

interface CitationListProps {
  citations: Citation[];
  limit?: number;
}

// The backend sends up to 10 citations (top_results in routers/query.py)
const MAX_VISIBLE_CITATIONS = 5;

export function CitationList({
  citations,
  limit = MAX_VISIBLE_CITATIONS,
}: CitationListProps) {
  if (!citations?.length) return null;

  const top = [...citations].sort((a, b) => b.score - a.score).slice(0, limit);

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2 ml-1">
      <span className="text-xs text-muted-foreground mr-0.5">Sources</span>
      {top.map((citation, i) => (
        // citation.id is always null for now (no "id" in Chroma metadata)
        <CitationButton key={citation.id ?? i} citation={citation} />
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
          <CitationLinks links={citation.links ?? []} />
        </div>
        <ScrollArea className="h-56 px-3 py-2">
          <p className="text-sm whitespace-pre-wrap">{citation.content}</p>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

// One link -> "Open original". Several (a Telegram chunk grouping posts) -> one link per
// post, labelled with the post number from the URL (t.me/<channel>/<id>).
function CitationLinks({ links }: { links: string[] }) {
  if (!links.length) return null;

  const linkClass =
    "inline-flex items-center gap-1 text-xs text-primary hover:underline";

  if (links.length === 1) {
    return (
      <a
        href={links[0]}
        target="_blank"
        rel="noopener noreferrer"
        className={`${linkClass} mt-1`}
      >
        Open original <LuExternalLink className="size-3" />
      </a>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-2 mt-1">
      <span className="text-xs text-muted-foreground">Posts</span>
      {links.map((link) => (
        <a
          key={link}
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className={linkClass}
        >
          #{postLabel(link)}
        </a>
      ))}
    </div>
  );
}

function postLabel(link: string): string {
  try {
    return new URL(link).pathname.split("/").filter(Boolean).pop() ?? link;
  } catch {
    return link;
  }
}
