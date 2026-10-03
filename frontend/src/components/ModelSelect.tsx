import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import type { OllamaModel } from "@/types";

interface ModelSelectProps {
  id?: string;
  models: OllamaModel[];
  capability: "completion" | "embedding";
  value: string;
  onChange: (model: string) => void;
}

export function ModelSelect({
  id,
  models,
  capability,
  value,
  onChange,
}: ModelSelectProps) {
  // Ollama versions that don't report capabilities give [], show those everywhere
  const options = models.filter(
    (m) => m.capabilities.length === 0 || m.capabilities.includes(capability),
  );

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue placeholder="Select a model..." />
      </SelectTrigger>
      <SelectContent>
        {options.map((m) => (
          <SelectItem key={m.name} value={m.name}>
            {m.name}
            {m.parameter_size && (
              <span className="text-muted-foreground">{m.parameter_size}</span>
            )}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
