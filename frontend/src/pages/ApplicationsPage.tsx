import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, X } from "lucide-react";
import { api } from "../lib/api";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { ApplicationStatusBadge } from "../components/StatusBadge";
import { formatDateTime } from "../lib/format";
import type { ApplicationStatus } from "../lib/types";

const STATUS_OPTIONS: ApplicationStatus[] = [
  "queued",
  "running",
  "success",
  "failed",
  "review_required",
  "pending_verification",
  "cancelled",
];
const PAGE_SIZE = 25;

export function ApplicationsPage() {
  const [status, setStatus] = useState<ApplicationStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const applicationsQuery = useQuery({
    queryKey: ["applications", { status, offset }],
    queryFn: () => api.applications.list({ limit: PAGE_SIZE, offset, status: status || undefined }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Applications</h1>
        <p className="mt-1 text-sm text-slate-500">Track every application Flames has queued or submitted.</p>
      </div>

      <select
        className="input w-auto"
        value={status}
        onChange={(e) => {
          setOffset(0);
          setStatus(e.target.value as ApplicationStatus | "");
        }}
      >
        <option value="">All statuses</option>
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s.replace("_", " ")}
          </option>
        ))}
      </select>

      {applicationsQuery.isLoading && <LoadingState />}
      {applicationsQuery.isError && <ErrorState message="Could not load applications." />}
      {applicationsQuery.data && applicationsQuery.data.length === 0 && (
        <EmptyState title="No applications yet" description="Queue an application from the Jobs page." />
      )}

      {applicationsQuery.data && applicationsQuery.data.length > 0 && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Retries</th>
                <th className="px-4 py-3 font-medium">Submitted</th>
                <th className="px-4 py-3 font-medium">Completed</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {applicationsQuery.data.map((application) => (
                <tr
                  key={application.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => setSelectedId(application.id)}
                >
                  <td className="px-4 py-3">
                    <ApplicationStatusBadge status={application.application_status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{application.retry_count}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDateTime(application.submitted_at)}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDateTime(application.completed_at)}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDateTime(application.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>

          <div className="flex flex-col gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <span>
              Showing {offset + 1}–{offset + applicationsQuery.data.length}
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
                disabled={applicationsQuery.data.length < PAGE_SIZE}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedId && <ApplicationDetailDrawer id={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  );
}

function ApplicationDetailDrawer({ id, onClose }: { id: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const detailQuery = useQuery({ queryKey: ["application", id], queryFn: () => api.applications.get(id) });
  const retryMutation = useMutation({
    mutationFn: () => api.applications.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["application", id] });
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-lg overflow-y-auto bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {detailQuery.isLoading && <LoadingState />}
        {detailQuery.isError && <ErrorState message="Could not load application." />}
        {detailQuery.data && (
          <div className="p-6">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Application</h2>
                <div className="mt-2">
                  <ApplicationStatusBadge status={detailQuery.data.application_status} />
                </div>
              </div>
              <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
                <X className="h-5 w-5" />
              </button>
            </div>

            {detailQuery.data.error_message && (
              <p className="mb-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {detailQuery.data.error_message}
              </p>
            )}

            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Timeline</h3>
            <ol className="mb-6 space-y-3 border-l border-slate-200 pl-4">
              {detailQuery.data.timeline.length === 0 && (
                <p className="text-sm text-slate-400">No events recorded yet.</p>
              )}
              {detailQuery.data.timeline.map((event, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-brand-500" />
                  <p className="text-sm font-medium text-slate-800">{event.action}</p>
                  <p className="text-xs text-slate-400">{formatDateTime(event.created_at)}</p>
                </li>
              ))}
            </ol>

            {(detailQuery.data.application_status === "failed" ||
              detailQuery.data.application_status === "review_required") && (
              <button
                className="btn-primary"
                disabled={retryMutation.isPending}
                onClick={() => retryMutation.mutate()}
              >
                <RefreshCw className="h-4 w-4" />
                Retry application
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
