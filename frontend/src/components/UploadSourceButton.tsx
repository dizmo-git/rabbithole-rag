import { Button } from "@/components/ui/button";

import { LuUpload } from "react-icons/lu";

export function UploadSourceButton({ onClick }: { onClick: () => void }) {
  return (
    <Button onClick={onClick} variant="outline" size="sm" className="w-full">
      <LuUpload className="mr-2" />
      Upload Source
    </Button>
  );
}
