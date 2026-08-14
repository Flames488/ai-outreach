import { clsx } from "clsx";
import { applicationStatusStyles, emailCategoryStyles, jobStatusStyles } from "../lib/status";
import type { ApplicationStatus, EmailCategory, JobStatus } from "../lib/types";

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        className,
      )}
    >
      {label}
    </span>
  );
}

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const style = jobStatusStyles[status];
  return <Badge label={style.label} className={style.className} />;
}

export function ApplicationStatusBadge({ status }: { status: ApplicationStatus }) {
  const style = applicationStatusStyles[status];
  return <Badge label={style.label} className={style.className} />;
}

export function EmailCategoryBadge({ category }: { category: EmailCategory }) {
  const style = emailCategoryStyles[category];
  return <Badge label={style.label} className={style.className} />;
}
