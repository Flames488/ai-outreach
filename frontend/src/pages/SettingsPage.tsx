import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Mail, XCircle } from "lucide-react";
import { api } from "../lib/api";
import { ErrorState, LoadingState } from "../components/States";
import { useAuth } from "../lib/auth";
import type { FeatureFlags } from "../lib/types";

const FLAG_LABELS: Record<keyof FeatureFlags, string> = {
  enable_playwright: "Playwright application automation",
  enable_gmail: "Gmail sync",
  enable_telegram: "Telegram bot",
  enable_ai_scoring: "AI job scoring",
  enable_auto_apply: "Auto-apply to matched jobs",
  enable_dashboard: "Dashboard API access",
  enable_screenshots: "Screenshot on application failure",
  enable_resume_generator: "AI resume generator",
  enable_interview_preparation: "AI interview preparation",
};

export function SettingsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.settings.get });
  const gmailQuery = useQuery({ queryKey: ["gmail-status"], queryFn: api.gmail.status });

  const flagMutation = useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) => api.settings.setFlag(key, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  const connectMutation = useMutation({
    mutationFn: api.gmail.connect,
    onSuccess: (data) => {
      window.location.href = data.consent_url;
    },
  });

  if (settingsQuery.isLoading) return <LoadingState />;
  if (settingsQuery.isError || !settingsQuery.data) return <ErrorState message="Could not load settings." />;

  const { feature_flags, job_match_threshold, job_search_max_results } = settingsQuery.data;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">Signed in as {user?.email}</p>
      </div>

      <section className="card p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-700">Gmail integration</h2>
        {gmailQuery.data?.connected ? (
          <div className="flex items-center gap-2 text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4" />
            Connected — last synced {gmailQuery.data.last_synced_at ?? "never"}
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <XCircle className="h-4 w-4" />
              Not connected
            </div>
            <button className="btn-primary" onClick={() => connectMutation.mutate()}>
              <Mail className="h-4 w-4" />
              Connect Gmail
            </button>
          </div>
        )}
      </section>

      <section className="card p-6">
        <h2 className="mb-1 text-sm font-semibold text-slate-700">Matching thresholds</h2>
        <p className="mb-4 text-xs text-slate-400">Boot-time configuration — change via environment variables.</p>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-slate-500">Job match threshold</dt>
            <dd className="mt-0.5 font-medium text-slate-900">{job_match_threshold}%</dd>
          </div>
          <div>
            <dt className="text-slate-500">Max results per search</dt>
            <dd className="mt-0.5 font-medium text-slate-900">{job_search_max_results}</dd>
          </div>
        </dl>
      </section>

      <section className="card p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-700">Feature flags</h2>
        <div className="divide-y divide-slate-100">
          {(Object.keys(feature_flags) as (keyof FeatureFlags)[]).map((key) => (
            <div key={key} className="flex items-center justify-between gap-4 py-3">
              <span className="text-sm text-slate-700">{FLAG_LABELS[key]}</span>
              <label className="relative inline-flex shrink-0 cursor-pointer items-center">
                <input
                  type="checkbox"
                  className="peer sr-only"
                  checked={feature_flags[key]}
                  onChange={(e) => flagMutation.mutate({ key, enabled: e.target.checked })}
                />
                <div className="h-5 w-9 rounded-full bg-slate-200 transition-colors peer-checked:bg-brand-600" />
                <div className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform peer-checked:translate-x-4" />
              </label>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
