import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, ExternalLink, MapPin, Plus, ShieldCheck, Star, X } from "lucide-react";
import { api, ApiError } from "../lib/api";
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
  const [showAddJob, setShowAddJob] = useState(false);

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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Jobs</h1>
          <p className="mt-1 text-sm text-slate-500">Every posting Flames has discovered and scored.</p>
        </div>
        <button className="btn-primary w-full sm:w-auto" onClick={() => setShowAddJob(true)}>
          <Plus className="h-4 w-4" />
          Add job manually
        </button>
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
      {showAddJob && <AddJobModal onClose={() => setShowAddJob(false)} />}
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
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
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

      {(job.client_total_spend != null ||
        job.client_rating != null ||
        job.client_payment_verified != null) && (
        <div className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:grid-cols-3">
          {job.client_total_spend != null && (
            <div className="flex items-center gap-2">
              <BadgeCheck className="h-4 w-4 shrink-0 text-brand-600" />
              <div>
                <p className="text-xs text-slate-500">Client spend</p>
                <p className="text-sm font-medium text-slate-900">
                  ${job.client_total_spend.toLocaleString()}+
                </p>
              </div>
            </div>
          )}
          {job.client_rating != null && (
            <div className="flex items-center gap-2">
              <Star className="h-4 w-4 shrink-0 text-amber-500" />
              <div>
                <p className="text-xs text-slate-500">Client rating</p>
                <p className="text-sm font-medium text-slate-900">{job.client_rating.toFixed(1)}</p>
              </div>
            </div>
          )}
          {job.client_payment_verified != null && (
            <div className="flex items-center gap-2">
              <ShieldCheck
                className={`h-4 w-4 shrink-0 ${job.client_payment_verified ? "text-emerald-600" : "text-slate-400"}`}
              />
              <div>
                <p className="text-xs text-slate-500">Payment</p>
                <p className="text-sm font-medium text-slate-900">
                  {job.client_payment_verified ? "Verified" : "Not verified"}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

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

function AddJobModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [provider, setProvider] = useState("Upwork");
  const [applicationUrl, setApplicationUrl] = useState("");
  const [description, setDescription] = useState("");
  const [remote, setRemote] = useState(true);
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
  const [clientTotalSpend, setClientTotalSpend] = useState("");
  const [clientRating, setClientRating] = useState("");
  const [clientPaymentVerified, setClientPaymentVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: api.jobs.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not add job."),
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    createMutation.mutate({
      title,
      company_name: companyName || null,
      provider,
      application_url: applicationUrl,
      description,
      remote,
      salary_min: salaryMin ? Number(salaryMin) : null,
      salary_max: salaryMax ? Number(salaryMax) : null,
      client_total_spend: clientTotalSpend ? Number(clientTotalSpend) : null,
      client_rating: clientRating ? Number(clientRating) : null,
      client_payment_verified: clientPaymentVerified || null,
    });
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <form
        onSubmit={handleSubmit}
        className="card max-h-[90vh] w-full max-w-lg overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Add a job manually</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              For gigs on Upwork, Fiverr, or anywhere else Flames doesn't search automatically.
            </p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">Title</label>
            <input className="input" required value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="label">Client / company name</label>
              <input className="input" value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
            </div>
            <div>
              <label className="label">Platform</label>
              <input
                className="input"
                placeholder="Upwork, Fiverr, ..."
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="label">Posting URL</label>
            <input
              className="input"
              type="url"
              required
              placeholder="https://"
              value={applicationUrl}
              onChange={(e) => setApplicationUrl(e.target.value)}
            />
          </div>

          <div>
            <label className="label">Description (optional)</label>
            <textarea
              className="input min-h-20"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div>
              <label className="label">Budget min ($)</label>
              <input
                className="input"
                type="number"
                min="0"
                value={salaryMin}
                onChange={(e) => setSalaryMin(e.target.value)}
              />
            </div>
            <div>
              <label className="label">Budget max ($)</label>
              <input
                className="input"
                type="number"
                min="0"
                value={salaryMax}
                onChange={(e) => setSalaryMax(e.target.value)}
              />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" checked={remote} onChange={(e) => setRemote(e.target.checked)} />
                Remote
              </label>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 p-3">
            <p className="label mb-2">Client signals (optional — you enter these yourself)</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="label">Client total spend ($)</label>
                <input
                  className="input"
                  type="number"
                  min="0"
                  placeholder="e.g. 150000"
                  value={clientTotalSpend}
                  onChange={(e) => setClientTotalSpend(e.target.value)}
                />
              </div>
              <div>
                <label className="label">Client rating (0-5)</label>
                <input
                  className="input"
                  type="number"
                  min="0"
                  max="5"
                  step="0.1"
                  value={clientRating}
                  onChange={(e) => setClientRating(e.target.value)}
                />
              </div>
            </div>
            <label className="mt-3 flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={clientPaymentVerified}
                onChange={(e) => setClientPaymentVerified(e.target.checked)}
              />
              Payment method verified
            </label>
          </div>

          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

          <button type="submit" className="btn-primary w-full" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Adding…" : "Add job"}
          </button>
        </div>
      </form>
    </div>
  );
}
