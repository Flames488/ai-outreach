import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, MapPin, X } from "lucide-react";
import { api } from "../lib/api";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { JobStatusBadge } from "../components/StatusBadge";
import { formatDate, formatSalary, formatScore } from "../lib/format";
import type { Job, JobStatus } from "../lib/types";

const STATUS_OPTIONS: JobStatus[] = ["new", "matched", "review", "applied", "failed", "skipped", "expired"];
const PAGE_SIZE = 25;

export function JobsPage() {
  const [status, setStatus] = useState<JobStatus | "">("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const jobsQuery = useQuery({
    queryKey: ["jobs", { status, remoteOnly, offset }],
    queryFn: () =>
      api.jobs.list({
        limit: PAGE_SIZE,
        offset,
        status: status || undefined,
        remote: remoteOnly || undefined,
      }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Jobs</h1>
        <p className="mt-1 text-sm text-slate-500">Every posting Flames has discovered and scored.</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          className="input w-auto"
          value={status}
          onChange={(e) => {
            setOffset(0);
            setStatus(e.target.value as JobStatus | "");
          }}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={remoteOnly}
            onChange={(e) => {
              setOffset(0);
              setRemoteOnly(e.target.checked);
            }}
          />
          Remote only
        </label>
      </div>

      {jobsQuery.isLoading && <LoadingState />}
      {jobsQuery.isError && <ErrorState message="Could not load jobs." />}
      {jobsQuery.data && jobsQuery.data.length === 0 && (
        <EmptyState title="No jobs match these filters" description="Try widening your search." />
      )}

      {jobsQuery.data && jobsQuery.data.length > 0 && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Location</th>
                <th className="px-4 py-3 font-medium">Salary</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Discovered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobsQuery.data.map((job) => (
                <tr
                  key={job.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => setSelectedJobId(job.id)}
                >
                  <td className="max-w-xs truncate px-4 py-3 font-medium text-slate-900">{job.title}</td>
                  <td className="px-4 py-3 text-slate-600">
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5 text-slate-400" />
                      {job.remote ? "Remote" : job.location ?? "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatSalary(job.salary_min, job.salary_max, job.currency)}</td>
                  <td className="px-4 py-3 text-slate-600">{formatScore(job.ai_score)}</td>
                  <td className="px-4 py-3">
                    <JobStatusBadge status={job.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(job.discovered_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>

          <div className="flex flex-col gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <span>
              Showing {offset + 1}–{offset + jobsQuery.data.length}
            </span>
            <div className="flex gap-2">
              <button
                className="btn-secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                Previous
              </button>
              <button
                className="btn-secondary"
                disabled={jobsQuery.data.length < PAGE_SIZE}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedJobId && <JobDetailDrawer jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />}
    </div>
  );
}

function JobDetailDrawer({ jobId, onClose }: { jobId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const jobQuery = useQuery({ queryKey: ["job", jobId], queryFn: () => api.jobs.get(jobId) });
  const applyMutation = useMutation({
    mutationFn: () => api.applications.create(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-lg overflow-y-auto bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {jobQuery.isLoading && <LoadingState />}
        {jobQuery.isError && <ErrorState message="Could not load job details." />}
        {jobQuery.data && (
          <JobDetailBody job={jobQuery.data} onClose={onClose} applyMutation={applyMutation} />
        )}
      </div>
    </div>
  );
}

function JobDetailBody({
  job,
  onClose,
  applyMutation,
}: {
  job: Job & { description: string };
  onClose: () => void;
  applyMutation: ReturnType<typeof useMutation<unknown, Error, void>>;
}) {
  return (
    <div className="p-6">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{job.title}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {job.provider} · {job.remote ? "Remote" : job.location ?? "Location unknown"}
          </p>
        </div>
        <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <JobStatusBadge status={job.status} />
        <span className="text-xs text-slate-400">Score {formatScore(job.ai_score)}</span>
        <span className="text-xs text-slate-400">
          {formatSalary(job.salary_min, job.salary_max, job.currency)}
        </span>
      </div>

      <div className="mb-6 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
        {job.description}
      </div>

      <div className="flex gap-3">
        <a href={job.application_url} target="_blank" rel="noreferrer" className="btn-secondary">
          <ExternalLink className="h-4 w-4" />
          View posting
        </a>
        <button
          className="btn-primary"
          disabled={applyMutation.isPending || applyMutation.isSuccess}
          onClick={() => applyMutation.mutate()}
        >
          {applyMutation.isSuccess ? "Queued for application" : "Queue application"}
        </button>
      </div>
    </div>
  );
}
