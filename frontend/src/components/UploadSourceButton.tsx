import { Button } from "@/components/ui/button";

import { LuUpload } from "react-icons/lu";

export function UploadSourceButton() {
  return (
    <Button variant="outline" size="sm" className="w-full">
      <LuUpload className="mr-2" />
      Upload Source
    </Button>
  );
}
