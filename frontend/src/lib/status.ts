import type { ApplicationStatus, EmailCategory, JobStatus } from "./types";

interface StatusStyle {
  label: string;
  className: string;
}

export const jobStatusStyles: Record<JobStatus, StatusStyle> = {
  new: { label: "New", className: "bg-slate-100 text-slate-700" },
  matched: { label: "Matched", className: "bg-blue-100 text-blue-700" },
  review: { label: "Review", className: "bg-amber-100 text-amber-700" },
  applied: { label: "Applied", className: "bg-emerald-100 text-emerald-700" },
  failed: { label: "Failed", className: "bg-red-100 text-red-700" },
  skipped: { label: "Skipped", className: "bg-slate-100 text-slate-500" },
  expired: { label: "Expired", className: "bg-slate-100 text-slate-400" },
};

export const applicationStatusStyles: Record<ApplicationStatus, StatusStyle> = {
  queued: { label: "Queued", className: "bg-slate-100 text-slate-700" },
  running: { label: "Running", className: "bg-blue-100 text-blue-700" },
  success: { label: "Success", className: "bg-emerald-100 text-emerald-700" },
  failed: { label: "Failed", className: "bg-red-100 text-red-700" },
  review_required: { label: "Review Required", className: "bg-amber-100 text-amber-700" },
  pending_verification: { label: "Pending Verification", className: "bg-purple-100 text-purple-700" },
  cancelled: { label: "Cancelled", className: "bg-slate-100 text-slate-500" },
};

export const emailCategoryStyles: Record<EmailCategory, StatusStyle> = {
  interview: { label: "Interview", className: "bg-emerald-100 text-emerald-700" },
  job_offer: { label: "Job Offer", className: "bg-emerald-100 text-emerald-700" },
  assessment: { label: "Assessment", className: "bg-blue-100 text-blue-700" },
  technical_test: { label: "Technical Test", className: "bg-blue-100 text-blue-700" },
  follow_up: { label: "Follow Up", className: "bg-amber-100 text-amber-700" },
  rejection: { label: "Rejection", className: "bg-red-100 text-red-700" },
  auto_reply: { label: "Auto Reply", className: "bg-slate-100 text-slate-500" },
  newsletter: { label: "Newsletter", className: "bg-slate-100 text-slate-500" },
  unknown: { label: "Unknown", className: "bg-slate-100 text-slate-400" },
};
