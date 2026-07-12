import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { UploadSourceButton } from "./UploadSourceButton";
import { LuUpload, LuX } from "react-icons/lu";
import { Input } from "./ui/input";
import { useState } from "react";

export function UploadSourceAlert({
  onFile,
  onLink,
}: {
  onFile: () => void;
  onLink: (link: string) => void;
}) {
  const [url, setUrl] = useState("");

  const handleClick = () => {
    if (!url) {
      onFile();
    } else {
      onLink(url);
    }

    setUrl("");
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <span>
          <UploadSourceButton />
        </span>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader className="flex flex-col w-full relative">
          <div className="absolute -right-2 -top-2">
            <AlertDialogCancel size="icon" variant="ghost" className="h-6 w-6">
              <LuX className="h-4 w-4" />
            </AlertDialogCancel>
          </div>
          <div className="w-full text-center mt-2">
            <AlertDialogTitle>Upload New Source</AlertDialogTitle>
            <AlertDialogDescription>
              Either upload a file or a link to a forum post
            </AlertDialogDescription>
          </div>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex">
          <div className="flex flex-row gap-2 w-full">
            <Input
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste a URL..."
              className="flex-1"
            />
          </div>
          <div>
            <AlertDialogAction
              onClick={handleClick}
              variant="outline"
              size="sm"
              className="w-full h-full"
            >
              <span>{url ? "From Link" : "From File"}</span>
              <LuUpload className="mr-2" />
            </AlertDialogAction>
          </div>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
