import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, X } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import type { ApplicationRule, RuleOperator, RulePriorityTier } from "../lib/types";

const ALLOWED_FIELDS = [
  "ai_score",
  "remote",
  "country",
  "city",
  "salary_min",
  "salary_max",
  "employment_type",
  "experience_level",
  "provider",
  "applications_today",
  "skills",
];

const OPERATORS: RuleOperator[] = ["==", "!=", ">=", "<=", ">", "<", "in", "not_in", "contains"];
const TIERS: RulePriorityTier[] = ["critical", "required", "preference"];

const tierStyles: Record<RulePriorityTier, string> = {
  critical: "bg-red-100 text-red-700",
  required: "bg-amber-100 text-amber-700",
  preference: "bg-slate-100 text-slate-600",
};

export function RulesPage() {
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();
  const rulesQuery = useQuery({ queryKey: ["rules"], queryFn: api.rules.list });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.rules.update(id, { enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.rules.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Rules</h1>
          <p className="mt-1 text-sm text-slate-500">
            Critical/required rules gate auto-apply; preference rules only affect ranking.
          </p>
        </div>
        <button className="btn-primary w-full sm:w-auto" onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4" />
          New rule
        </button>
      </div>

      {rulesQuery.isLoading && <LoadingState />}
      {rulesQuery.isError && <ErrorState message="Could not load rules." />}
      {rulesQuery.data && rulesQuery.data.length === 0 && (
        <EmptyState title="No rules defined" description="Add a rule to control which jobs get auto-applied." />
      )}

      {rulesQuery.data && rulesQuery.data.length > 0 && (
        <div className="card divide-y divide-slate-100">
          {rulesQuery.data.map((rule: ApplicationRule) => (
            <div key={rule.id} className="flex items-center justify-between gap-4 px-5 py-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium text-slate-900">{rule.name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tierStyles[rule.priority_tier]}`}>
                    {rule.priority_tier}
                  </span>
                </div>
                <p className="mt-0.5 font-mono text-xs text-slate-500">
                  {rule.condition.field} {rule.condition.op} {JSON.stringify(rule.condition.value)}
                </p>
                {rule.description && <p className="mt-1 text-xs text-slate-400">{rule.description}</p>}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <label className="flex items-center gap-2 text-xs text-slate-500">
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    onChange={(e) => toggleMutation.mutate({ id: rule.id, enabled: e.target.checked })}
                  />
                  Enabled
                </label>
                <button
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                  onClick={() => {
                    if (confirm(`Delete rule "${rule.name}"?`)) deleteMutation.mutate(rule.id);
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && <NewRuleModal onClose={() => setShowForm(false)} />}
    </div>
  );
}

function NewRuleModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [priorityTier, setPriorityTier] = useState<RulePriorityTier>("required");
  const [field, setField] = useState(ALLOWED_FIELDS[0]);
  const [op, setOp] = useState<RuleOperator>("==");
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: api.rules.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not create rule."),
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    let parsedValue: unknown = value;
    if (value === "true") parsedValue = true;
    else if (value === "false") parsedValue = false;
    else if (value !== "" && !Number.isNaN(Number(value))) parsedValue = Number(value);
    else if (op === "in" || op === "not_in") parsedValue = value.split(",").map((v) => v.trim());

    createMutation.mutate({
      name,
      description: description || undefined,
      priority_tier: priorityTier,
      condition: { field, op, value: parsedValue },
    });
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <form
        onSubmit={handleSubmit}
        className="card w-full max-w-md space-y-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">New rule</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div>
          <label className="label">Name</label>
          <input className="input" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>

        <div>
          <label className="label">Description (optional)</label>
          <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div>
          <label className="label">Priority tier</label>
          <select className="input" value={priorityTier} onChange={(e) => setPriorityTier(e.target.value as RulePriorityTier)}>
            {TIERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div>
            <label className="label">Field</label>
            <select className="input" value={field} onChange={(e) => setField(e.target.value)}>
              {ALLOWED_FIELDS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Operator</label>
            <select className="input" value={op} onChange={(e) => setOp(e.target.value as RuleOperator)}>
              {OPERATORS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Value</label>
            <input className="input" required value={value} onChange={(e) => setValue(e.target.value)} />
          </div>
        </div>

        {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <button type="submit" className="btn-primary w-full" disabled={createMutation.isPending}>
          Create rule
        </button>
      </form>
    </div>
  );
}
