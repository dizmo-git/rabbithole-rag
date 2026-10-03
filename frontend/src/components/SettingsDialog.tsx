import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { ModelSelect } from "./ModelSelect";
import { LuSettings } from "react-icons/lu";
import { useState } from "react";
import type { AppSettings, OllamaModel } from "@/types";
import {
  getModels,
  getSettings,
  modelErrorMessage,
  updateSettings,
} from "@/api/settings";

export function SettingsDialog() {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [error, setError] = useState<string | null>(null);

  // refetch on every open: models may have been pulled/removed since last time
  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) return;
    setError(null);
    Promise.all([getSettings(), getModels()])
      .then(([s, m]) => {
        setSettings(s);
        setModels(m);
      })
      .catch((err) => setError(modelErrorMessage(err)));
  };

  const handleSave = async () => {
    if (!settings) return;
    try {
      await updateSettings(settings);
      setOpen(false);
    } catch (err) {
      setError(modelErrorMessage(err));
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" aria-label="Settings">
          <LuSettings />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Local Ollama models used by the app</DialogDescription>
        </DialogHeader>

        {settings && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="chat-model">Chat model</Label>
              <ModelSelect
                id="chat-model"
                models={models}
                capability="completion"
                value={settings.chat_model}
                onChange={(chat_model) => setSettings({ ...settings, chat_model })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="embedding-model">
                Default embedding model for new notebooks
              </Label>
              <ModelSelect
                id="embedding-model"
                models={models}
                capability="embedding"
                value={settings.embedding_model}
                onChange={(embedding_model) =>
                  setSettings({ ...settings, embedding_model })
                }
              />
              <p className="text-sm text-muted-foreground">
                Existing notebooks keep the model they were created with.
              </p>
            </div>
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button onClick={handleSave} disabled={!settings}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
