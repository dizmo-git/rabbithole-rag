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
import {
  parseTelegramUrl,
  TELEGRAM_DEFAULT_POSTS,
  TELEGRAM_MAX_POSTS,
} from "@/lib/telegram";

export function UploadSourceAlert({
  onFile,
  onLink,
}: {
  onFile: () => void;
  // maxPosts is only passed for Telegram links
  onLink: (link: string, maxPosts?: number) => void;
}) {
  const [url, setUrl] = useState("");
  // kept as a string so the field can be cleared while typing
  const [postCount, setPostCount] = useState(String(TELEGRAM_DEFAULT_POSTS));

  const telegram = parseTelegramUrl(url);
  const maxPosts = Number(postCount);
  const postCountValid =
    Number.isInteger(maxPosts) &&
    maxPosts >= 1 &&
    maxPosts <= TELEGRAM_MAX_POSTS;

  const handleClick = () => {
    if (!url) {
      onFile();
    } else {
      onLink(url.trim(), telegram ? maxPosts : undefined);
    }

    setUrl("");
    setPostCount(String(TELEGRAM_DEFAULT_POSTS));
  };

  const buttonLabel = !url ? "From File" : telegram ? "From Telegram" : "From Link";

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
              Upload a file, or paste a link to a forum post or a public
              Telegram channel
            </AlertDialogDescription>
          </div>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex">
          <div className="flex flex-col gap-2 w-full">
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste a URL..."
              className="flex-1"
            />
            {/* Telegram links read a channel timeline, so ask how far back to go */}
            {telegram && (
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <label
                    htmlFor="telegram-post-count"
                    className="text-sm whitespace-nowrap"
                  >
                    Posts to fetch
                  </label>
                  <Input
                    id="telegram-post-count"
                    type="number"
                    min={1}
                    max={TELEGRAM_MAX_POSTS}
                    step={1}
                    value={postCount}
                    onChange={(e) => setPostCount(e.target.value)}
                    aria-invalid={!postCountValid}
                    className="w-24"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {postCountValid
                    ? `Counting back from ${
                        telegram.postId !== null
                          ? `post #${telegram.postId}`
                          : "the latest post"
                      } in @${telegram.channel}`
                    : `Enter a whole number from 1 to ${TELEGRAM_MAX_POSTS}`}
                </p>
              </div>
            )}
          </div>
          <div className="sm:self-start">
            <AlertDialogAction
              onClick={handleClick}
              disabled={telegram !== null && !postCountValid}
              variant="outline"
              size="sm"
              className="w-full h-8"
            >
              <span>{buttonLabel}</span>
              <LuUpload className="mr-2" />
            </AlertDialogAction>
          </div>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
