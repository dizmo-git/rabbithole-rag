import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "./ui/input";
import { useEffect, useState } from "react";
import type { Source } from "@/types";

interface RenameSourceDialogProps {
  source: Source | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (source: Source, newName: string) => void;
}

export function RenameSourceDialog({
  source,
  open,
  onOpenChange,
  onConfirm,
}: RenameSourceDialogProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && source) {
      setName(source.filename ?? source.url ?? "");
      setError(null);
    }
  }, [open, source]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setName(e.target.value);
    if (error) setError(null);
  };

  const handleConfirm = (e: React.MouseEvent) => {
    const trimmed = name.trim();

    if (!trimmed) {
      e.preventDefault();
      setError("Name can't be empty");
      return;
    }

    if (source && trimmed !== (source.filename ?? source.url)) {
      onConfirm(source, trimmed);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Rename Source</AlertDialogTitle>
          <AlertDialogDescription>
            Choose a new name for this source
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex flex-col gap-1">
          <Input
            value={name}
            onChange={handleChange}
            placeholder="Source name..."
            autoFocus
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm}>Rename</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
