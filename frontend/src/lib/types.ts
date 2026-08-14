export type JobStatus = "new" | "matched" | "review" | "applied" | "failed" | "skipped" | "expired";

export type ApplicationStatus =
  | "queued"
  | "running"
  | "success"
  | "failed"
  | "review_required"
  | "pending_verification"
  | "cancelled";

export type EmailCategory =
  | "interview"
  | "job_offer"
  | "assessment"
  | "technical_test"
  | "follow_up"
  | "rejection"
  | "auto_reply"
  | "newsletter"
  | "unknown";

export type RulePriorityTier = "critical" | "required" | "preference";

export type RuleOperator = "==" | "!=" | ">=" | "<=" | ">" | "<" | "in" | "not_in" | "contains";

export type UserRole = "admin" | "user";

export interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
  meta?: Record<string, unknown>;
}

export interface ErrorEnvelope {
  success: false;
  message: string;
  errors: { code: string; detail: string }[];
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserProfile {
  full_name: string | null;
  phone: string | null;
  country: string | null;
  city: string | null;
  years_of_experience: number | null;
  current_position: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  work_authorization: string | null;
  visa_sponsorship_needed: boolean | null;
  expected_salary: number | null;
  notice_period: string | null;
  education: unknown[] | null;
  certifications: unknown[] | null;
  languages: unknown[] | null;
}

export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: UserRole;
  telegram_chat_id: string | null;
  gmail_connected: boolean;
  profile: UserProfile | null;
}

export interface Job {
  id: string;
  provider: string;
  title: string;
  company_id: string | null;
  location: string | null;
  country: string | null;
  city: string | null;
  remote: boolean;
  employment_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  application_url: string;
  ai_score: number | null;
  status: JobStatus;
  posted_date: string | null;
  discovered_at: string;
}

export interface JobDetail extends Job {
  description: string;
}

export interface Application {
  id: string;
  job_id: string;
  application_status: ApplicationStatus;
  error_message: string | null;
  retry_count: number;
  submitted_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TimelineEvent {
  action: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
}

export interface ApplicationDetail extends Application {
  timeline: TimelineEvent[];
}

export interface EmailMessage {
  id: string;
  sender: string;
  recipient: string | null;
  subject: string;
  snippet: string;
  received_at: string;
  category: EmailCategory;
  processed: boolean;
}

export interface RuleCondition {
  field: string;
  op: RuleOperator;
  value: unknown;
}

export interface ApplicationRule {
  id: string;
  name: string;
  description: string | null;
  priority_tier: RulePriorityTier;
  condition: RuleCondition;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobStatusCounts {
  new: number;
  matched: number;
  review: number;
  applied: number;
  failed: number;
  skipped: number;
  expired: number;
}

export interface ApplicationStatusCounts {
  pending: number;
  running: number;
  success: number;
  failed: number;
  review_required: number;
  cancelled: number;
}

export interface DashboardStats {
  total_jobs_discovered: number;
  jobs_by_status: JobStatusCounts;
  total_applications: number;
  applications_by_status: ApplicationStatusCounts;
}

export interface DashboardSummary {
  total_jobs: number;
  new_jobs_today: number;
  matched_jobs: number;
  pending_review: number;
  total_applications: number;
  applications_today: number;
  queued_applications: number;
  unprocessed_emails: number;
}

export interface FeatureFlags {
  enable_playwright: boolean;
  enable_gmail: boolean;
  enable_telegram: boolean;
  enable_ai_scoring: boolean;
  enable_auto_apply: boolean;
  enable_dashboard: boolean;
  enable_screenshots: boolean;
  enable_resume_generator: boolean;
  enable_interview_preparation: boolean;
}

export interface Settings {
  job_match_threshold: number;
  job_search_max_results: number;
  feature_flags: FeatureFlags;
}

export interface GmailStatus {
  connected: boolean;
  last_synced_at: string | null;
}
