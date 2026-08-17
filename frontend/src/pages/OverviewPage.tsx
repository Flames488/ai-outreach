import { useMutation, useQuery } from "@tanstack/react-query";
import { Briefcase, CheckCircle2, Clock, Loader2, Mail, Search, Sparkles } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import { StatCard } from "../components/StatCard";
import { ErrorState, LoadingState } from "../components/States";

const JOB_STATUS_COLORS: Record<string, string> = {
  new: "#94a3b8",
  matched: "#3b82f6",
  review: "#f59e0b",
  applied: "#10b981",
  failed: "#ef4444",
  skipped: "#cbd5e1",
  expired: "#e2e8f0",
};

export function OverviewPage() {
  const summaryQuery = useQuery({ queryKey: ["dashboard-summary"], queryFn: api.dashboard.summary });
  const statsQuery = useQuery({ queryKey: ["dashboard-stats"], queryFn: api.dashboard.stats });
  const triggerSearch = useMutation({ mutationFn: api.jobs.triggerSearch });

  if (summaryQuery.isLoading || statsQuery.isLoading) return <LoadingState />;
  if (summaryQuery.isError || statsQuery.isError || !summaryQuery.data || !statsQuery.data) {
    return <ErrorState message="Could not load dashboard data." />;
  }

  const summary = summaryQuery.data;
  const stats = statsQuery.data;

  const jobStatusData = Object.entries(stats.jobs_by_status).map(([status, count]) => ({
    status,
    count,
  }));

  const applicationStatusData = Object.entries(stats.applications_by_status)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({ name: status.replace("_", " "), value: count }));

  const APP_COLORS = ["#3b82f6", "#10b981", "#ef4444", "#f59e0b", "#a855f7", "#94a3b8"];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Overview</h1>
          <p className="mt-1 text-sm text-slate-500">Live snapshot of your job search pipeline.</p>
        </div>
        <button
          className="btn-primary w-full sm:w-auto"
          disabled={triggerSearch.isPending}
          onClick={() => triggerSearch.mutate()}
        >
          {triggerSearch.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {triggerSearch.isSuccess ? "Search queued" : "Run job search"}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Jobs" value={summary.total_jobs} icon={Briefcase} accent="brand" hint={`${summary.new_jobs_today} discovered today`} />
        <StatCard label="Matched Jobs" value={summary.matched_jobs} icon={Sparkles} accent="emerald" hint={`${summary.pending_review} awaiting review`} />
        <StatCard label="Applications" value={summary.total_applications} icon={CheckCircle2} accent="brand" hint={`${summary.applications_today} sent today`} />
        <StatCard label="Unread Emails" value={summary.unprocessed_emails} icon={Mail} accent="amber" hint={`${summary.queued_applications} applications queued`} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card p-6">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Jobs by status</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={jobStatusData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="status" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <Tooltip
                cursor={{ fill: "#f8fafc" }}
                contentStyle={{ borderRadius: 8, borderColor: "#e2e8f0", fontSize: 12 }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {jobStatusData.map((entry) => (
                  <Cell key={entry.status} fill={JOB_STATUS_COLORS[entry.status] ?? "#94a3b8"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Applications by status</h2>
          {applicationStatusData.length === 0 ? (
            <div className="flex h-[260px] items-center justify-center text-sm text-slate-400">
              <Clock className="mr-2 h-4 w-4" /> No applications yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={applicationStatusData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={2}
                >
                  {applicationStatusData.map((entry, index) => (
                    <Cell key={entry.name} fill={APP_COLORS[index % APP_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#e2e8f0", fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
