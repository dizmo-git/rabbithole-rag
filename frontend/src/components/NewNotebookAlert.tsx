import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { NewNotebookButton } from "./NewNotebookButton";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { ModelSelect } from "./ModelSelect";
import { useState } from "react";
import { newNotebook } from "@/api/notebooks";
import { getModels, getSettings, modelErrorMessage } from "@/api/settings";
import { useNotebook } from "./NotebookProvider";
import type { OllamaModel } from "@/types";

export function NewNotebookAlert({
  onCreated,
}: {
  onCreated: () => Promise<string[]>;
}) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [embeddingModel, setEmbeddingModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { setSelectedNotebook } = useNotebook();

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) return;
    setError(null);
    Promise.all([getSettings(), getModels()])
      .then(([s, m]) => {
        setModels(m);
        setEmbeddingModel(s.embedding_model); // preselect the default from settings
      })
      .catch((err) => setError(modelErrorMessage(err)));
  };

  const handleCreateNewNotebook = async (e: React.MouseEvent) => {
    e.preventDefault(); // keep the dialog open if creation fails
    try {
      // "" = models didn't load, let the backend fall back to its default
      const newTitle = await newNotebook(title, embeddingModel || undefined);
      setSelectedNotebook(newTitle);
      await onCreated();
      setOpen(false);
    } catch (err) {
      setError(modelErrorMessage(err));
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogTrigger asChild>
        <span>
          <NewNotebookButton />
        </span>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Create a new Notebook</AlertDialogTitle>
          <Input
            placeholder="Give it a title..."
            onChange={(e) => setTitle(e.target.value)}
          />
        </AlertDialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor="notebook-embedding-model">Embedding model</Label>
          <ModelSelect
            id="notebook-embedding-model"
            models={models}
            capability="embedding"
            value={embeddingModel}
            onChange={setEmbeddingModel}
          />
          <p className="text-sm text-muted-foreground">
            Can't be changed later.
          </p>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <AlertDialogFooter>
          <AlertDialogAction onClick={handleCreateNewNotebook}>
            Create
          </AlertDialogAction>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
