import { Coffee, Moon, Sun } from "lucide-react";
import { clsx } from "clsx";
import { useTheme, type Theme } from "../lib/theme";

const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "cream", label: "Cream", icon: Coffee },
  { value: "dark", label: "Dark", icon: Moon },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex items-center gap-0.5 rounded-lg bg-slate-100 p-0.5">
      {OPTIONS.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          onClick={() => setTheme(value)}
          title={label}
          aria-label={`${label} theme`}
          aria-pressed={theme === value}
          className={clsx(
            "flex h-7 w-7 items-center justify-center rounded-md transition-colors",
            theme === value
              ? "bg-white text-brand-600 shadow-sm"
              : "text-slate-400 hover:text-slate-600",
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  );
}
