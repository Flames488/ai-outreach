import type {
  Application,
  ApplicationDetail,
  ApplicationRule,
  ApplicationStatus,
  DashboardStats,
  DashboardSummary,
  EmailMessage,
  Envelope,
  GmailStatus,
  Job,
  JobDetail,
  JobStatus,
  RuleCondition,
  RulePriorityTier,
  Settings,
  TokenPair,
  User,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

const ACCESS_TOKEN_KEY = "flames_access_token";
const REFRESH_TOKEN_KEY = "flames_refresh_token";

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  set: (tokens: TokenPair) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refreshToken = tokenStore.getRefresh();
  if (!refreshToken) return false;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) return false;
        const body = (await res.json()) as Envelope<TokenPair>;
        tokenStore.set(body.data);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const token = tokenStore.getAccess();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (response.status === 401 && retry && tokenStore.getRefresh()) {
    const refreshed = await tryRefresh();
    if (refreshed) return request<T>(path, options, false);
    tokenStore.clear();
    window.location.assign("/login");
    throw new ApiError(401, "Session expired");
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const message = body?.message ?? response.statusText;
    const code = body?.errors?.[0]?.code;
    throw new ApiError(response.status, message, code);
  }

  return (body as Envelope<T>).data;
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  const search = new URLSearchParams(entries.map(([k, v]) => [k, String(v)]));
  return `?${search.toString()}`;
}

export const api = {
  auth: {
    login: async (email: string, password: string): Promise<TokenPair> => {
      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString(),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new ApiError(response.status, body?.message ?? "Login failed");
      }
      return (body as Envelope<TokenPair>).data;
    },
    logout: async (): Promise<void> => {
      const refreshToken = tokenStore.getRefresh();
      if (!refreshToken) return;
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => undefined);
    },
  },

  me: () => request<User>("/users/me"),

  dashboard: {
    summary: () => request<DashboardSummary>("/dashboard"),
    stats: () => request<DashboardStats>("/stats/summary"),
  },

  jobs: {
    list: (params: {
      limit?: number;
      offset?: number;
      status?: JobStatus;
      provider?: string;
      remote?: boolean;
      country?: string;
      employment_type?: string;
      min_score?: number;
    }) => request<Job[]>(`/jobs${qs(params)}`),
    get: (id: string) => request<JobDetail>(`/jobs/${id}`),
    triggerSearch: () => request<{ task_id: string }>("/jobs/search", { method: "POST" }),
  },

  applications: {
    list: (params: { limit?: number; offset?: number; status?: ApplicationStatus }) =>
      request<Application[]>(`/applications${qs(params)}`),
    get: (id: string) => request<ApplicationDetail>(`/applications/${id}`),
    create: (jobId: string) =>
      request<Application>("/applications", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId }),
      }),
    retry: (id: string) => request<Application>(`/applications/${id}/retry`, { method: "POST" }),
  },

  emails: {
    list: (params: { limit?: number; offset?: number }) =>
      request<EmailMessage[]>(`/emails${qs(params)}`),
    get: (id: string) => request<EmailMessage>(`/emails/${id}`),
  },

  rules: {
    list: () => request<ApplicationRule[]>("/rules"),
    create: (body: {
      name: string;
      description?: string;
      priority_tier: RulePriorityTier;
      condition: RuleCondition;
      enabled?: boolean;
    }) => request<ApplicationRule>("/rules", { method: "POST", body: JSON.stringify(body) }),
    update: (
      id: string,
      body: Partial<{
        name: string;
        description: string;
        priority_tier: RulePriorityTier;
        condition: RuleCondition;
        enabled: boolean;
      }>,
    ) =>
      request<ApplicationRule>(`/rules/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    remove: (id: string) => request<Record<string, never>>(`/rules/${id}`, { method: "DELETE" }),
  },

  settings: {
    get: () => request<Settings>("/settings"),
    setFlag: (key: string, enabled: boolean) =>
      request<Record<string, never>>("/settings", {
        method: "POST",
        body: JSON.stringify({ key, enabled }),
      }),
  },

  gmail: {
    status: () => request<GmailStatus>("/gmail/status"),
    connect: () => request<{ consent_url: string }>("/gmail/connect", { method: "POST" }),
  },
};
