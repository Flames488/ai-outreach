import { format, formatDistanceToNow } from "date-fns";

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return format(new Date(value), "MMM d, yyyy");
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return format(new Date(value), "MMM d, yyyy 'at' h:mm a");
}

export function formatRelative(value: string | null): string {
  if (!value) return "—";
  return formatDistanceToNow(new Date(value), { addSuffix: true });
}

export function formatSalary(min: number | null, max: number | null, currency: string | null): string {
  const cur = currency ?? "USD";
  if (min && max) return `${cur} ${min.toLocaleString()} – ${max.toLocaleString()}`;
  if (min) return `${cur} ${min.toLocaleString()}+`;
  if (max) return `Up to ${cur} ${max.toLocaleString()}`;
  return "Not disclosed";
}

export function formatScore(score: number | null): string {
  if (score === null || score === undefined) return "—";
  return `${Math.round(score)}%`;
}
