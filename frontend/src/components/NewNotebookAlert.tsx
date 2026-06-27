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
import { useState } from "react";
import { newNotebook } from "@/api/notebooks";
import { useNotebook } from "./NotebookProvider";

export function NewNotebookAlert({
  onCreated,
}: {
  onCreated: () => Promise<string[]>;
}) {
  const [title, setTitle] = useState("");
  const { setSelectedNotebook } = useNotebook();

  const handleCreateNewNotebook = async () => {
    const newTitle = await newNotebook(title);
    setSelectedNotebook(newTitle);
    await onCreated();
  };

  return (
    <AlertDialog>
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
