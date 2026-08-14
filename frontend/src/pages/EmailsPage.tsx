import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { EmailCategoryBadge } from "../components/StatusBadge";
import { formatRelative } from "../lib/format";

const PAGE_SIZE = 25;

export function EmailsPage() {
  const [offset, setOffset] = useState(0);

  const emailsQuery = useQuery({
    queryKey: ["emails", { offset }],
    queryFn: () => api.emails.list({ limit: PAGE_SIZE, offset }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Emails</h1>
        <p className="mt-1 text-sm text-slate-500">Recruiter replies synced from Gmail and classified by AI.</p>
      </div>

      {emailsQuery.isLoading && <LoadingState />}
      {emailsQuery.isError && <ErrorState message="Could not load emails." />}
      {emailsQuery.data && emailsQuery.data.length === 0 && (
        <EmptyState title="No emails synced yet" description="Connect Gmail from Settings to start syncing." />
      )}

      {emailsQuery.data && emailsQuery.data.length > 0 && (
        <div className="card divide-y divide-slate-100">
          {emailsQuery.data.map((email) => (
            <div key={email.id} className="flex items-start gap-4 px-5 py-4">
              <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${email.processed ? "bg-slate-200" : "bg-brand-500"}`} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-medium text-slate-900">{email.subject}</p>
                  <span className="shrink-0 text-xs text-slate-400">{formatRelative(email.received_at)}</span>
                </div>
                <p className="mt-0.5 truncate text-xs text-slate-500">{email.sender}</p>
                <p className="mt-1 line-clamp-2 text-sm text-slate-600">{email.snippet}</p>
                <div className="mt-2">
                  <EmailCategoryBadge category={email.category} />
                </div>
              </div>
            </div>
          ))}

          <div className="flex items-center justify-between px-5 py-3 text-sm text-slate-500">
            <span>
              Showing {offset + 1}–{offset + emailsQuery.data.length}
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
                disabled={emailsQuery.data.length < PAGE_SIZE}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
