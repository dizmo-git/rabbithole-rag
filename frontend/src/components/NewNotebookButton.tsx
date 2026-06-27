import { LuPlus } from "react-icons/lu";
import { Button } from "./ui/button";

export function NewNotebookButton() {
  return (
    <Button variant="outline" size="sm" className="w-full">
      <LuPlus className="mr-2" />
      New Notebook
    </Button>
  );
}
