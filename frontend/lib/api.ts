const API_URL = (
  process.env.NODE_ENV === "production"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

function requireApiUrl() {
  return API_URL;
}

export type User = {
  id: string;
  email: string;
  display_name: string;
  status: string;
  households?: HouseholdMembership[];
};

export type HouseholdMembership = {
  id: string;
  name: string;
  role: string;
  slug: string;
};

export type Household = {
  id: string;
  name: string;
  slug: string;
  base_currency: string;
  reporting_currency: string;
  timezone: string;
  country: string;
  fiscal_month_start_day: number;
  minimum_buffer_amount: string;
};

export type Member = {
  id: string;
  household_id: string;
  user_id: string | null;
  display_name: string;
  role: string;
  relationship: string;
  member_type: string;
  is_financial_contributor: boolean;
  permissions: { view_all_contributions: boolean; view_all_obligations: boolean };
};

export type Account = {
  id: string;
  name: string;
  type: string;
  currency: string;
  institution: string | null;
  current_balance: string;
  available_balance: string;
  is_protected: boolean;
  is_emergency: boolean;
  include_in_safe_to_spend: boolean;
  include_in_net_worth: boolean;
  status: string;
  access_scope: "shared" | "personal";
  owner_member_id: string | null;
};

export type Category = {
  id: string;
  name: string;
  kind: string;
};

export type IncomeSource = {
  id: string;
  name: string;
  type: string;
  expected_amount: string;
  frequency: string;
  is_active: boolean;
};

export type Transaction = {
  id: string;
  account_id: string;
  counterparty_account_id: string | null;
  member_id: string | null;
  access_scope: "shared" | "personal";
  amount: string;
  currency: string;
  base_amount?: string | null;
  base_currency?: string | null;
  exchange_rate?: string | null;
  exchange_rate_date?: string | null;
  counterparty_amount?: string | null;
  counterparty_currency?: string | null;
  counterparty_base_amount?: string | null;
  type: string;
  category_id: string | null;
  date: string;
  merchant: string | null;
  description: string | null;
  status: string;
};

export type CalendarEvent = {
  id: string;
  kind: string;
  title: string;
  date: string;
  amount: string;
  status: string;
  coverage_label: string | null;
  obligation_id: string | null;
  occurrence_id: string | null;
};

export type GivingPolicy = {
  id: string;
  name: string;
  kind: string;
  monthly_limit: string | null;
  annual_limit: string | null;
  requires_dual_approval: boolean;
  monthly_used: string;
  annual_used: string;
  limit_breached: boolean;
  status: string;
};

export type GivingRecord = {
  id: string;
  kind: string;
  beneficiary: string | null;
  amount: string;
  date: string;
  status: string;
  limit_warning: string | null;
  transaction_id: string | null;
};

export type GivingSummary = {
  period_month: string;
  policies: GivingPolicy[];
  records: GivingRecord[];
  pending_approvals: GivingRecord[];
  total_posted_month: string;
  total_posted_year: string;
};

export type CashFlowDay = {
  date: string;
  income: string;
  expenses: string;
  giving: string;
  transfers_net: string;
  net: string;
  closing_cash: string;
};

export type CashFlow = {
  period_start: string;
  period_end: string;
  opening_cash: string;
  closing_cash: string;
  income: string;
  expenses: string;
  giving: string;
  transfers_net: string;
  surplus: string;
  daily: CashFlowDay[];
};

export type AllocationLine = {
  id: string;
  rule_id: string | null;
  name: string;
  requested_amount: string;
  amount: string;
  destination_type: string;
  destination_id: string | null;
  mandatory: boolean;
  funded: boolean;
};

export type AllocationRun = {
  id: string;
  household_id: string;
  period_start: string;
  period_end: string;
  recognized_income: string;
  total_allocated: string;
  surplus: string;
  status: string;
  lines: AllocationLine[];
  unfunded_mandatory: { rule_id: string | null; name: string; requested_amount: string; amount: string }[];
};

export type AllocationRule = {
  id: string;
  household_id: string;
  name: string;
  type: string;
  basis: string;
  rate: string | null;
  amount: string | null;
  priority: number;
  mandatory: boolean;
  destination_type: string;
  destination_id: string | null;
  is_active: boolean;
};

export type SafeToSpendSnapshot = {
  currency: string;
  current: string;
  period: string;
  forecast: string;
  horizon_days: number;
  minimum_buffer_amount: string;
  components: {
    liquid_cash: string;
    expected_income: string;
    expected_contributions: string;
    committed_obligations: string;
    upcoming_bills: string;
    sinking_fund_requirements: string;
    protected_savings: string;
    pending_transactions: string;
  };
};

export type PurchaseCheckResult = {
  amount: string;
  affordable: boolean;
  severity: string;
  remaining_current_sts: string;
  obligations_affected: string[];
  buffer_breached: boolean;
  recommended_action: string;
};

export type HouseholdOverview = {
  household: Household;
  currency: string;
  cash_total: string;
  period_income: string;
  allocated_total?: string;
  surplus?: string;
  allocation?: AllocationRun | null;
  safe_to_spend?: SafeToSpendSnapshot;
  wealth?: {
    net_worth: string;
    investments: string;
    emergency_fund: string;
    debt: string;
  };
  health?: HealthScore | null;
  health_ready?: boolean;
  foundation?: {
    household: boolean;
    accounts: boolean;
    income: boolean;
    obligations: boolean;
    budget: boolean;
    goals: boolean;
    completed: number;
    total: number;
  };
  accounts: Account[];
  recent_transactions: Transaction[];
  upcoming_obligations?: CalendarEvent[];
};

export type HealthComponent = {
  key: string;
  weight: string;
  points: string;
  inputs: Record<string, string | number | boolean>;
};

export type HealthScore = {
  score: string;
  label: string;
  period_start: string;
  period_end: string;
  components: HealthComponent[];
};

export type FinancialSnapshot = {
  id: string;
  period_start: string;
  period_end: string;
  income: string;
  expenses: string;
  savings: string;
  investments: string;
  giving: string;
  surplus: string;
  net_worth: string;
  health_score: string;
  payload: {
    shock?: string;
    health?: HealthScore;
  };
};

export type Report = {
  id: string;
  kind: string;
  period_start: string;
  period_end: string;
  payload: Record<string, unknown>;
};

export type Insights = {
  currency?: string;
  period_start: string;
  period_end: string;
  spend: { category: string; amount: string }[];
  top_categories: { category: string; amount: string }[];
  overspend: { category: string; amount: string }[];
  cash_flow: { period_start: string; period_label: string; income: string; expenses: string; surplus: string }[];
  net_worth: { period_start: string; period_label: string; net_worth: string }[];
  health_history: { period_start: string; period_label: string; score: string; label: string }[];
  giving: { allocated: string; actual: string; limit: string; vs_limit: string };
  patterns?: {
    code: string;
    severity: string;
    title: string;
    detail: string;
    evidence: Record<string, unknown>;
  }[];
  health: HealthScore;
};

export type Occurrence = {
  id: string;
  obligation_id: string;
  due_date: string;
  amount: string;
  funded_amount: string;
  coverage: string;
  coverage_label: string;
  status: string;
};

export type Obligation = {
  id: string;
  household_id: string;
  name: string;
  amount: string;
  currency: string;
  frequency: string;
  next_due_date: string;
  priority: string;
  sinking_fund: boolean;
  fund_id: string | null;
  fund_name: string | null;
  status: string;
  required_monthly: string;
  next_occurrence: Occurrence | null;
  occurrences: Occurrence[];
  beneficiary_name: string | null;
};

export type Fund = {
  id: string;
  household_id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  target_date: string | null;
  obligation_id: string | null;
  obligation_name: string | null;
  monthly_contribution: string;
  required_monthly: string;
  expected_amount: string;
  shortfall: string;
  on_track: boolean;
  progress: string;
  coverage_label: string;
  account_id: string | null;
  is_protected: boolean;
  status: string;
};

export type BudgetCategory = {
  id: string;
  category_id: string;
  category_name: string;
  allocated_amount: string;
  spent_amount: string;
  remaining_amount: string;
  utilization: string | null;
  status: string;
  rollover: boolean;
};

export type Budget = {
  id: string;
  household_id: string;
  name: string;
  period_type: string;
  start_date: string;
  end_date: string;
  member_id: string | null;
  member_name: string | null;
  status: string;
  allocated_total: string;
  spent_total: string;
  remaining_total: string;
  categories: BudgetCategory[];
};

export type Recurring = {
  id: string;
  household_id: string;
  account_id: string;
  counterparty_account_id: string | null;
  member_id: string | null;
  category_id: string | null;
  amount: string;
  currency: string;
  type: string;
  frequency: string;
  next_date: string;
  merchant: string | null;
  description: string | null;
  is_active: boolean;
};

export type Alert = {
  id: string;
  household_id: string;
  type: string;
  severity: string;
  title: string;
  body: string;
  related_entity_type: string;
  related_entity_id: string;
  period_key: string;
  status: string;
};

let householdId: string | undefined;
let csrfToken: string | undefined;

export function setHouseholdId(id?: string) {
  householdId = id;
  currentHouseholdCache = undefined;
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("ipile:household-changed"));
  }
}

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : undefined;
}

async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const fromCookie = readCookie("ffos_csrf");
  if (fromCookie) {
    csrfToken = fromCookie;
    return fromCookie;
  }
  const response = await fetch(`${requireApiUrl()}/api/v1/auth/csrf`, { credentials: "include" });
  const data = (await response.json()) as { csrf_token?: string };
  if (!response.ok || !data.csrf_token) {
    throw new Error("Unable to establish CSRF protection.");
  }
  csrfToken = data.csrf_token;
  return csrfToken;
}

export function clearCsrfToken() {
  csrfToken = undefined;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiUrl = requireApiUrl();
  const method = (init?.method ?? "GET").toUpperCase();
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(householdId ? { "X-Household-Id": householdId } : {}),
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    headers["X-CSRF-Token"] = await ensureCsrfToken();
  }

  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init,
      method,
      credentials: "include",
      headers,
    });
  } catch {
    throw new Error(
      `IPÌLẸ̀ is temporarily unavailable. Please try again in a moment.`,
    );
  }

  if (response.status === 403 && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    clearCsrfToken();
    headers["X-CSRF-Token"] = await ensureCsrfToken();
    const retry = await fetch(`${apiUrl}${path}`, {
      ...init,
      method,
      credentials: "include",
      headers,
    });
    return parseResponse<T>(retry);
  }

  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  let data: Record<string, unknown> = {};
  let rawText = "";

  if (contentType.includes("application/json")) {
    data = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  } else {
    rawText = await response.text().catch(() => "");
    try {
      data = rawText ? (JSON.parse(rawText) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }
  }

  if (!response.ok) {
    const retryAfter = response.headers.get("retry-after");
    const errorObject = data.error as { message?: string } | undefined;
    const detail = data.detail ?? errorObject?.message;
    const message =
      typeof detail === "string"
        ? detail
        : response.status === 429
          ? "Too many requests. Please wait a moment before trying again."
          : rawText.trim() || `Request failed (HTTP ${response.status}).`;
    throw new Error(retryAfter && response.status === 429 ? `${message} Try again in ${retryAfter} seconds.` : message);
  }

  if (!contentType.includes("application/json") && rawText) {
    throw new Error("The server returned an unexpected response. Please try again shortly.");
  }
  return data as T;
}

export type MemberFinancialSummary = {
  currency: string;
  period_start: string;
  period_end: string;
  accessible_accounts: number;
  cash_total: string;
  income: string;
  expenses: string;
  net_cash_flow: string;
  transaction_count: number;
};

export function getMemberFinancialSummary(periodStart?: string, periodEnd?: string) {
  const params = new URLSearchParams();
  if (periodStart) params.set("period_start", periodStart);
  if (periodEnd) params.set("period_end", periodEnd);
  const query = params.toString() ? `?${params.toString()}` : "";
  return request<MemberFinancialSummary>(`/api/v1/member/financial-summary${query}`);
}

export function getOverview() {
  return request<HouseholdOverview>("/api/v1/overview");
}

let currentUserCache: { value: Promise<User>; expiresAt: number } | undefined;
let currentHouseholdCache: { householdId: string | undefined; value: Promise<Household>; expiresAt: number } | undefined;

export function getCurrentUser() {
  const now = Date.now();
  if (currentUserCache && currentUserCache.expiresAt > now) return currentUserCache.value;
  const value = request<User>("/api/v1/auth/me").catch((error) => { currentUserCache = undefined; throw error; });
  currentUserCache = { value, expiresAt: now + 15_000 };
  return value;
}

export function invalidateCurrentUserCache() { currentUserCache = undefined; }

export function getCurrentHousehold() {
  const now = Date.now();
  if (currentHouseholdCache && currentHouseholdCache.householdId === householdId && currentHouseholdCache.expiresAt > now) return currentHouseholdCache.value;
  const value = request<Household>("/api/v1/households/current").catch((error) => { currentHouseholdCache = undefined; throw error; });
  currentHouseholdCache = { householdId, value, expiresAt: now + 15_000 };
  return value;
}

export function getCurrencyCatalog() {
  return request<{ currencies: { code: string; name: string; symbol: string }[]; default: string }>("/api/v1/currencies");
}

export async function updateCurrentHousehold(body: {
  name?: string;
  minimum_buffer_amount?: string;
  fiscal_month_start_day?: number;
  reporting_currency?: string;
}) {
  const household = await request<Household>("/api/v1/households/current", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  currentHouseholdCache = undefined;
  if (typeof window !== "undefined") window.dispatchEvent(new Event("ipile:household-changed"));
  return household;
}

export function getFinancialHealth() {
  return request<HealthScore>("/api/v1/financial-health");
}

export function explainFinancialHealth() {
  return request<HealthScore>("/api/v1/financial-health/explain");
}

export function getInsights() {
  return request<Insights>("/api/v1/insights");
}

export function getSnapshots() {
  return request<FinancialSnapshot[]>("/api/v1/snapshots");
}

export function getMonthlyReport(period?: string) {
  const query = period ? `?period=${period}` : "";
  return request<Report>(`/api/v1/reports/monthly${query}`);
}

export function getQuarterlyReport(year?: number, quarter?: number) {
  const params = new URLSearchParams();
  if (year) params.set("year", String(year));
  if (quarter) params.set("quarter", String(quarter));
  const query = params.toString() ? `?${params}` : "";
  return request<Report>(`/api/v1/reports/quarterly${query}`);
}

export function getAnnualReport(year?: number) {
  const query = year ? `?year=${year}` : "";
  return request<Report>(`/api/v1/reports/annual${query}`);
}

export function getGivingReport(year?: number) {
  const query = year ? `?year=${year}` : "";
  return request<Report>(`/api/v1/reports/giving${query}`);
}

export type SimulationMonth = {
  month_index: number;
  income: string;
  contributions: string;
  debt_payments: string;
  debt_interest: string;
  surplus: string;
  cash: string;
  emergency: string;
  investments: string;
  net_worth: string;
  forecast_sts: string;
  cash_flow: string;
  obligations: string;
  emergency_fund: string;
  investments_status: string;
  safe_to_spend: string;
  net_worth_delta: string;
};

export type SimulationRun = {
  id: string;
  name: string;
  status: string;
  parameters: Record<string, unknown>;
  months: SimulationMonth[];
  summary: SimulationMonth;
};

export function runSimulation(body: {
  name?: string;
  monthly_income?: string;
  income_change_rate?: string;
  contribution_change_rate?: string;
  debt_strategy?: "snowball" | "avalanche";
  debt_extra_payment?: string;
  expense_category_deltas?: Record<string, string>;
  obligation_deltas?: Record<string, string>;
  investment_override?: string;
  unexpected_expense?: string;
  horizon_months?: number;
}) {
  return request<SimulationRun>("/api/v1/simulations", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getSimulation(id: string) {
  return request<SimulationRun>(`/api/v1/simulations/${id}`);
}

export type Notification = {
  id: string;
  household_id: string;
  alert_id: string | null;
  channel: string;
  title: string;
  body: string;
  severity: string;
  status: string;
  created_at: string;
  read_at: string | null;
};

export type AutomationTick = {
  id: string;
  household_id: string;
  tick_type: string;
  period_key: string;
  status: string;
  result: Record<string, unknown>;
  skipped: boolean;
};

export function getNotifications(unreadOnly = false) {
  const query = unreadOnly ? "?unread_only=true" : "";
  return request<Notification[]>(`/api/v1/notifications${query}`);
}

export function markNotificationRead(id: string) {
  return request<Notification>(`/api/v1/notifications/${id}/read`, { method: "POST" });
}

export function runAutomationTick(body: { tick_type?: string; period_key?: string } = {}) {
  return request<AutomationTick>("/api/v1/automation/tick", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export type AiExplain = {
  explanation: string;
  source: string;
  payload: Record<string, unknown>;
};

export function explainWithAi() {
  return request<AiExplain>("/api/v1/ai/explain", { method: "POST" });
}

export type ImportJob = {
  id: string;
  household_id: string;
  source: string;
  filename: string | null;
  status: string;
  created_count: number;
  skipped_count: number;
  error_count: number;
  result: {
    sender?: string;
    message_id?: string | null;
    suggested_account_id?: string | null;
    account_match?: string;
    corrected?: boolean;
    intelligence?: {
      confidence_score: number;
      confidence_band: "high" | "medium" | "low";
      review_reasons: string[];
      account_match: string;
      suggested_account_id: string | null;
      sender_verified: boolean;
      category_suggestion: { name: string | null; confidence: string; reason: string };
      normalized_event: {
        provider: string;
        provider_event_id: string | null;
        external_id: string;
        occurred_on: string;
        amount: string;
        currency: string | null;
        direction: string;
        description: string | null;
        merchant: string | null;
        sender_verified: boolean;
      };
    };
    errors?: string[];
    account_id?: string;
    row_count?: number;
    duplicate_count_at_preview?: number;
    rows?: { date: string; amount: string; currency?: string | null; type: string; description: string | null; external_id?: string; merchant?: string | null; category_name?: string | null }[];
  };
};

export function previewImport(body: { account_id: string; source: "csv" | "statement"; content: string; filename?: string }) {
  return request<ImportJob>("/api/v1/imports/preview", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function previewStatementUpload(accountId: string, file: File) {
  const body = new FormData();
  body.append("account_id", accountId);
  body.append("file", file);
  return request<ImportJob>("/api/v1/imports/preview-upload", { method: "POST", body });
}

export function commitStagedImport(jobId: string, accountId: string) {
  return request<ImportJob>(`/api/v1/imports/jobs/${jobId}/commit`, {
    method: "POST",
    body: JSON.stringify({ account_id: accountId }),
  });
}

export function createImportMailbox() {
  return request<{ address: string; enabled: boolean; note: string }>("/api/v1/imports/mailbox", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getImportReview() {
  return request<ImportJob[]>("/api/v1/imports/review");
}

export function approveEmailImport(jobId: string, accountId: string) {
  return request<ImportJob>(`/api/v1/imports/${jobId}/approve`, {
    method: "POST",
    body: JSON.stringify({ account_id: accountId }),
  });
}

export function correctEmailImport(
  jobId: string,
  correction: { amount?: string; date?: string; type?: "income" | "expense"; description?: string; currency?: string },
) {
  return request<ImportJob>(`/api/v1/imports/${jobId}/review`, {
    method: "PATCH",
    body: JSON.stringify(correction),
  });
}

export type GmailConnectionStatus = {
  connected: boolean;
  email_address: string | null;
  last_sync_at: string | null;
  last_error: string | null;
};
export const getGmailConnection = () => request<GmailConnectionStatus>("/api/v1/imports/gmail/connection");
export const connectGmail = () => request<{ authorization_url: string }>("/api/v1/imports/gmail/connect", { method: "POST" });
export const disconnectGmail = () => request<{ connected: boolean }>("/api/v1/imports/gmail/disconnect", { method: "POST" });
export const syncGmail = () => request<{ scanned: number; queued: number; auto_posted: number; rejected: number; ignored: number }>("/api/v1/imports/gmail/sync", { method: "POST" });
export type ImportAutomationMode = "review_everything" | "auto_trusted" | "full_automation";
export const getImportPreferences = () => request<{ automation_mode: ImportAutomationMode }>("/api/v1/imports/preferences");
export const updateImportPreferences = (automation_mode: ImportAutomationMode) =>
  request<{ automation_mode: ImportAutomationMode }>("/api/v1/imports/preferences", {
    method: "PUT",
    body: JSON.stringify({ automation_mode }),
  });

export function exportHousehold() {
  return request<Record<string, unknown>>("/api/v1/export");
}

export function deleteCurrentHousehold() {
  return request<void>("/api/v1/households/current", { method: "DELETE" });
}

export type Invite = {
  id: string;
  household_id: string;
  email: string;
  role: string;
  token: string | null;
  invitation_url?: string | null;
  status: string;
  expires_at: string;
};

export function listInvites() {
  return request<Invite[]>("/api/v1/invites");
}

export function createInvite(body: { email: string; role: string }) {
  return request<Invite>("/api/v1/invites", { method: "POST", body: JSON.stringify(body) });
}

export function revokeInvite(id: string) {
  return request<void>(`/api/v1/invites/${id}`, { method: "DELETE" });
}

export function resendInvite(id: string) {
  return request<Invite>(`/api/v1/invites/${id}/resend`, { method: "POST" });
}

export function previewInvite(token: string) {
  return request<{
    id: string;
    household_id: string;
    household_name: string;
    email: string;
    role: string;
    status: string;
    expires_at: string;
  }>(`/api/v1/invites/preview/${encodeURIComponent(token)}`);
}

export function acceptInvite(token: string) {
  return request<{ id: string; household_id: string; role: string }>("/api/v1/invites/accept", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export type Billing = {
  household_id: string;
  plan: string;
  plan_name: string;
  price_monthly: string;
  currency: string;
  billing_status: string;
  plans: { id: string; name: string; price_monthly: string; currency: string; description: string }[];
};

export function getBilling() {
  return request<Billing>("/api/v1/billing");
}

export function changeBillingPlan(plan: string) {
  return request<Billing>("/api/v1/billing/plan", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}

export type SupportTicket = {
  id: string;
  household_id: string | null;
  subject: string;
  body: string;
  status: string;
  created_at: string;
};

export function listSupportTickets() {
  return request<SupportTicket[]>("/api/v1/support/tickets");
}

export function createSupportTicket(body: { subject: string; body: string }) {
  return request<SupportTicket>("/api/v1/support/tickets", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function onboardHousehold(body: { name: string; minimum_buffer_amount?: string; base_currency?: string; country?: string }) {
  return request<Household>("/api/v1/onboarding/household", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getAccounts() {
  return request<Account[]>("/api/v1/accounts");
}

export function getSafeToSpend() {
  return request<SafeToSpendSnapshot>("/api/v1/safe-to-spend");
}

export function runPurchaseCheck(body: { amount: string; category_id?: string; account_id?: string }) {
  return request<PurchaseCheckResult>("/api/v1/purchase-checks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getAllocationRules() {
  return request<AllocationRule[]>("/api/v1/allocation-rules");
}

export function createAllocationRule(body: {
  name: string;
  type: string;
  basis?: string;
  rate?: string | null;
  amount?: string | null;
  priority?: number;
  mandatory?: boolean;
  destination_type: string;
  destination_id?: string | null;
}) {
  return request<AllocationRule>("/api/v1/allocation-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getLatestAllocation() {
  return request<AllocationRun>("/api/v1/allocations/latest");
}

export function runAllocation() {
  return request<AllocationRun>("/api/v1/allocations/run", { method: "POST" });
}

export type WealthSnapshot = {
  currency: string;
  net_worth: string;
  total_assets: string;
  total_liabilities: string;
  emergency_fund: string;
  investments: string;
  debt: string;
  buckets: {
    cash: string;
    savings: string;
    investments: string;
    business: string;
    property: string;
    vehicle: string;
    other: string;
    loans: string;
    credit: string;
    other_debt: string;
  };
  history: {
    period_start: string;
    period_end: string;
    as_of: string;
    net_worth: string;
    total_assets: string;
    total_liabilities: string;
  }[];
};

export type HouseholdAsset = {
  id: string;
  name: string;
  type: string;
  current_value: string;
  is_emergency: boolean;
  include_in_net_worth: boolean;
};

export type HouseholdLiability = {
  id: string;
  name: string;
  type: string;
  current_balance: string;
  interest_rate?: string | null;
  minimum_payment?: string | null;
  status: string;
};

export type DebtStrategy = {
  strategy: string;
  order: {
    id: string;
    name: string;
    balance: string;
    interest_rate: string;
    min_payment: string;
    position: number;
  }[];
  months: number;
  total_interest: string;
  total_paid: string;
  paid_off: boolean;
  remaining_balance: string;
  schedule_summary: {
    month: number;
    total_payment: string;
    total_interest: string;
    remaining_balance: string;
    debts_remaining: number;
  }[];
};

export type DebtStrategies = {
  extra_payment: string;
  currency: string;
  snowball: DebtStrategy;
  avalanche: DebtStrategy;
  liabilities_considered: number;
};

export type HouseholdInvestment = {
  id: string;
  name: string;
  type: string;
  current_value: string;
  cost_basis: string;
  institution: string | null;
};

export function getNetWorth() {
  return request<WealthSnapshot>("/api/v1/net-worth");
}

export function getAssets() {
  return request<HouseholdAsset[]>("/api/v1/assets");
}

export function createAsset(body: {
  name: string;
  type: string;
  current_value: string;
  account_id?: string;
  is_emergency?: boolean;
}) {
  return request<HouseholdAsset>("/api/v1/assets", { method: "POST", body: JSON.stringify(body) });
}

export function getLiabilities() {
  return request<HouseholdLiability[]>("/api/v1/liabilities");
}

export function getDebtStrategies(extraPayment = "0") {
  return request<DebtStrategies>(`/api/v1/debts/strategies?extra_payment=${encodeURIComponent(extraPayment)}`);
}

export function createLiability(body: {
  name: string;
  type: string;
  current_balance: string;
  interest_rate?: string;
  minimum_payment?: string;
}) {
  return request<HouseholdLiability>("/api/v1/liabilities", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function payLiability(id: string, body: { account_id: string; amount: string }) {
  return request<HouseholdLiability>(`/api/v1/liabilities/${id}/payments`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getInvestments() {
  return request<HouseholdInvestment[]>("/api/v1/investments");
}

export function getCashFlow(periodStart?: string, periodEnd?: string) {
  const params = new URLSearchParams();
  if (periodStart) params.set("period_start", periodStart);
  if (periodEnd) params.set("period_end", periodEnd);
  const query = params.toString() ? `?${params.toString()}` : "";
  return request<CashFlow>(`/api/v1/cash-flow${query}`);
}

export function createInvestment(body: {
  name: string;
  type?: string;
  current_value?: string;
  cost_basis?: string;
  institution?: string;
  account_id?: string;
}) {
  return request<HouseholdInvestment>("/api/v1/investments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export type HouseholdGoal = {
  id: string;
  household_id: string;
  name: string;
  type: string;
  target_amount: string;
  current_amount: string;
  remaining: string;
  deadline: string | null;
  monthly_contribution: string | null;
  required_monthly: string;
  months_left: number | null;
  priority: number;
  progress: string;
  percent: number;
  coverage_label: string;
  status: string;
};

export function getGoals() {
  return request<HouseholdGoal[]>("/api/v1/goals");
}

export function createGoal(body: {
  name: string;
  type: string;
  target_amount: string;
  current_amount?: string;
  deadline?: string;
  monthly_contribution?: string;
}) {
  return request<HouseholdGoal>("/api/v1/goals", { method: "POST", body: JSON.stringify(body) });
}

export type BusinessPnL = {
  revenue: string;
  expenses: string;
  profit: string;
  family_invested: string;
  family_withdrawn: string;
  current_business_equity: string;
  family_return: string;
};

export type BusinessEmployee = {
  id: string;
  business_id: string;
  name: string;
  role: string;
  compensation: string | null;
  status: string;
};

export type BusinessTx = {
  id: string;
  type: string;
  amount: string;
  date: string;
  description: string | null;
};

export type HouseholdBusiness = {
  id: string;
  household_id: string;
  name: string;
  type: string;
  account_id: string | null;
  status: string;
  pnl: BusinessPnL;
  employees: BusinessEmployee[];
  transactions: BusinessTx[];
};

export function getBusinesses() {
  return request<HouseholdBusiness[]>("/api/v1/businesses");
}

export function createBusiness(body: { name: string; type?: string }) {
  return request<HouseholdBusiness>("/api/v1/businesses", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getBusiness(id: string) {
  return request<HouseholdBusiness>(`/api/v1/businesses/${id}`);
}

export function getBusinessPnL(id: string) {
  return request<BusinessPnL>(`/api/v1/businesses/${id}/pnl`);
}

export function addBusinessEmployee(id: string, body: { name: string; role?: string }) {
  return request<BusinessEmployee>(`/api/v1/businesses/${id}/employees`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function postBusinessTx(
  id: string,
  body: { type: string; amount: string; date: string; account_id?: string; description?: string },
) {
  return request<HouseholdBusiness>(`/api/v1/businesses/${id}/transactions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function contributeToGoal(id: string, body: { account_id: string; amount: string }) {
  return request<HouseholdGoal>(`/api/v1/goals/${id}/contributions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function recordInvestmentTx(
  id: string,
  body: { type: string; amount: string; date: string; account_id?: string },
) {
  return request<{ id: string }>(`/api/v1/investments/${id}/transactions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export const api = {
  health: () => request<{ status: string }>("/api/v1/health"),
  me: () => getCurrentUser(),
  register: (body: {
    email: string;
    password: string;
    display_name: string;
    invite_token?: string;
    create_household?: boolean;
  }) =>
    request<User>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(body) }).then(
      (user) => {
        invalidateCurrentUserCache();
        clearCsrfToken();
        return user;
      },
    ),
  login: (body: { email: string; password: string }) =>
    request<User>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(body) }).then(
      (user) => {
        clearCsrfToken();
        return user;
      },
    ),
  logout: () =>
    request<void>("/api/v1/auth/logout", { method: "POST" }).then(() => {
      invalidateCurrentUserCache();
      clearCsrfToken();
    }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    request<void>("/api/v1/auth/password/change", { method: "POST", body: JSON.stringify(body) }),
  getOverview,
  getMemberFinancialSummary,
  getFinancialHealth,
  explainFinancialHealth,
  getInsights,
  getSnapshots,
  getMonthlyReport,
  getQuarterlyReport,
  getAnnualReport,
  getGivingReport,
  runSimulation,
  getSimulation,
  getNotifications,
  markNotificationRead,
  runAutomationTick,
  explainWithAi,
  getSafeToSpend,
  runPurchaseCheck,
  getAllocationRules,
  getLatestAllocation,
  runAllocation,
  getAccounts,
  getNetWorth,
  getAssets,
  createAsset,
  getLiabilities,
  createLiability,
  payLiability,
  getInvestments,
  createInvestment,
  recordInvestmentTx,
  getGoals,
  createGoal,
  contributeToGoal,
  getBusinesses,
  createBusiness,
  getBusiness,
  getBusinessPnL,
  addBusinessEmployee,
  postBusinessTx,
  households: () => request<HouseholdMembership[]>("/api/v1/households"),
  currentHousehold: () => request<Household>("/api/v1/households/current"),
  members: () => request<Member[]>("/api/v1/members"),
  createMember: (body: {
    display_name: string;
    role: string;
    relationship: string;
    member_type: string;
  }) => request<Member>("/api/v1/members", { method: "POST", body: JSON.stringify(body) }),
  updateMember: (id: string, body: {
    display_name?: string;
    role?: string;
    relationship?: string;
    member_type?: string;
    permissions?: { view_all_contributions?: boolean; view_all_obligations?: boolean };
  }) =>
    request<Member>(`/api/v1/members/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteMember: (id: string) => request<void>(`/api/v1/members/${id}`, { method: "DELETE" }),
  transferOwnership: (member_id: string) =>
    request<HouseholdMembership>("/api/v1/households/current/transfer-ownership", {
      method: "POST",
      body: JSON.stringify({ member_id }),
    }),
  accounts: () => request<Account[]>("/api/v1/accounts"),
  createAccount: (body: {
    name: string;
    type: string;
    currency?: string;
    institution?: string;
    current_balance?: string;
    is_protected?: boolean;
    access_scope?: "shared" | "personal";
    owner_member_id?: string;
  }) => request<Account>("/api/v1/accounts", { method: "POST", body: JSON.stringify(body) }),
  currentMember: async () => {
    // Older production API deployments do not expose GET /members/me yet.
    // Resolve the current household member using endpoints already supported
    // by those deployments, while preserving household scoping.
    const [user, members] = await Promise.all([
      getCurrentUser(),
      request<Member[]>("/api/v1/members"),
    ]);
    const member = members.find((row) => row.user_id === user.id);
    if (!member) {
      throw new Error("Your household member profile could not be found.");
    }
    return member;
  },
  updateAccount: (id: string, body: {
    name?: string;
    institution?: string | null;
    is_protected?: boolean;
    is_emergency?: boolean;
    include_in_safe_to_spend?: boolean;
    include_in_net_worth?: boolean;
    status?: string;
  }) => request<Account>(`/api/v1/accounts/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  categories: () => request<Category[]>("/api/v1/categories"),
  incomeSources: () => request<IncomeSource[]>("/api/v1/income/sources"),
  createIncomeSource: (body: { name: string; expected_amount: string; type?: string }) =>
    request<IncomeSource>("/api/v1/income/sources", { method: "POST", body: JSON.stringify(body) }),
  income: () => request<Transaction[]>("/api/v1/income"),
  recordIncome: (body: { account_id: string; amount: string; date: string; income_source_id?: string; description?: string }) =>
    request<Transaction>("/api/v1/income", { method: "POST", body: JSON.stringify(body) }),
  transactions: (query = "") => request<Transaction[]>(`/api/v1/transactions${query}`),
  createTransaction: (body: {
    account_id: string;
    amount: string;
    type: string;
    date: string;
    counterparty_account_id?: string;
    category_id?: string;
    member_id?: string;
    access_scope?: "shared" | "personal";
    description?: string;
    merchant?: string;
  }) => request<Transaction>("/api/v1/transactions", { method: "POST", body: JSON.stringify(body) }),
  updateTransaction: (
    id: string,
    body: { merchant?: string | null; description?: string | null; category_id?: string | null; date?: string; member_id?: string | null },
  ) => request<Transaction>(`/api/v1/transactions/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  voidTransaction: (id: string) =>
    request<Transaction>(`/api/v1/transactions/${id}/void`, { method: "POST" }),
  budgets: () => request<Budget[]>("/api/v1/budget"),
  createBudget: (body: {
    name: string;
    period_type?: string;
    start_date?: string;
    end_date?: string;
    member_id?: string;
    categories: { category_id: string; allocated_amount: string }[];
  }) => request<Budget>("/api/v1/budget", { method: "POST", body: JSON.stringify(body) }),
  recurring: () => request<Recurring[]>("/api/v1/recurring"),
  createRecurring: (body: {
    account_id: string;
    amount: string;
    type: string;
    frequency: string;
    next_date: string;
    category_id?: string;
    member_id?: string;
    counterparty_account_id?: string;
    description?: string;
    merchant?: string;
  }) => request<Recurring>("/api/v1/recurring", { method: "POST", body: JSON.stringify(body) }),
  postRecurring: (id: string) => request<Transaction>(`/api/v1/recurring/${id}/post`, { method: "POST" }),
  deleteRecurring: (id: string) => request<void>(`/api/v1/recurring/${id}`, { method: "DELETE" }),
  alerts: () => request<Alert[]>("/api/v1/alerts"),
  readAlert: (id: string) => request<Alert>(`/api/v1/alerts/${id}/read`, { method: "POST" }),
  obligations: () => request<Obligation[]>("/api/v1/obligations"),
  createObligation: (body: {
    name: string;
    amount: string;
    frequency: string;
    next_due_date: string;
    priority?: string;
    sinking_fund?: boolean;
    beneficiary_name?: string;
  }) => request<Obligation>("/api/v1/obligations", { method: "POST", body: JSON.stringify(body) }),
  payOccurrence: (obligationId: string, occurrenceId: string, accountId: string) =>
    request<Obligation>(`/api/v1/obligations/${obligationId}/occurrences/${occurrenceId}/pay`, {
      method: "POST",
      body: JSON.stringify({ account_id: accountId }),
    }),
  funds: () => request<Fund[]>("/api/v1/funds"),
  createFund: (body: {
    name: string;
    target_amount: string;
    target_date?: string;
    obligation_id?: string;
    monthly_contribution?: string;
  }) => request<Fund>("/api/v1/funds", { method: "POST", body: JSON.stringify(body) }),
  contribute: (fundId: string, body: { account_id: string; amount: string }) =>
    request<Fund>(`/api/v1/funds/${fundId}/contributions`, { method: "POST", body: JSON.stringify(body) }),
  calendar: (days = 30) => request<CalendarEvent[]>(`/api/v1/calendar?days=${days}`),
  getCashFlow: (periodStart?: string, periodEnd?: string) => {
    const params = new URLSearchParams();
    if (periodStart) params.set("period_start", periodStart);
    if (periodEnd) params.set("period_end", periodEnd);
    const query = params.toString() ? `?${params.toString()}` : "";
    return request<CashFlow>(`/api/v1/cash-flow${query}`);
  },
  givingSummary: () => request<GivingSummary>("/api/v1/giving/summary"),
  givingPolicies: () => request<GivingPolicy[]>("/api/v1/giving/policies"),
  createGivingPolicy: (body: {
    name: string;
    kind: string;
    monthly_limit?: string;
    annual_limit?: string;
    requires_dual_approval?: boolean;
  }) => request<GivingPolicy>("/api/v1/giving/policies", { method: "POST", body: JSON.stringify(body) }),
  createGiving: (body: {
    kind: string;
    amount: string;
    account_id: string;
    policy_id?: string;
    beneficiary?: string;
    notes?: string;
    date?: string;
  }) => request<GivingRecord>("/api/v1/giving", { method: "POST", body: JSON.stringify(body) }),
  approveGiving: (id: string) =>
    request<GivingRecord>(`/api/v1/giving/${id}/approve`, { method: "POST" }),
  rejectGiving: (id: string) =>
    request<GivingRecord>(`/api/v1/giving/${id}/reject`, { method: "POST" }),
};


export type ContributionAgreement = {
  id: string;
  household_id: string;
  member_id: string;
  name: string;
  amount: string;
  currency: string;
  cadence: string;
  due_day: number | null;
  start_date: string;
  end_date: string | null;
  status: string;
  notes: string | null;
};

export type ContributionRecord = {
  id: string;
  household_id: string;
  agreement_id: string;
  member_id: string;
  amount: string;
  currency: string;
  contributed_on: string;
  transaction_id: string | null;
  note: string | null;
};

export type ContributionForecast = {
  currency: string;
  horizon_days: number;
  expected: string;
  verified_received: string;
  outstanding: string;
  other_currency_outstanding: Record<string, string>;
  rows: ContributionScheduleRow[];
};

export type ContributionScheduleRow = {
  agreement_id: string;
  member_id: string;
  name: string;
  due_date: string;
  currency: string;
  expected_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  status: "paid" | "partial" | "overdue" | "upcoming";
};

export function getContributionForecast(horizonDays = 90) {
  return request<ContributionForecast>(
    `/api/v1/contributions/forecast?horizon_days=${horizonDays}`,
  );
}

export function listContributionSchedule(fromDate?: string, toDate?: string) {
  const params = new URLSearchParams();
  if (fromDate) params.set("from_date", fromDate);
  if (toDate) params.set("to_date", toDate);
  const query = params.toString() ? `?${params.toString()}` : "";
  return request<ContributionScheduleRow[]>(`/api/v1/contributions/schedule${query}`);
}

export function listContributionAgreements() {
  return request<ContributionAgreement[]>("/api/v1/contributions");
}

export function updateContributionAgreement(
  id: string,
  body: {
    amount?: string;
    cadence?: string;
    due_day?: number | null;
    end_date?: string | null;
    status?: string;
    notes?: string | null;
  },
) {
  return request<ContributionAgreement>(`/api/v1/contributions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function createContributionAgreement(body: {
  member_id: string;
  name: string;
  amount: string;
  currency: string;
  cadence: string;
  due_day?: number;
  start_date: string;
  end_date?: string;
  notes?: string;
}) {
  return request<ContributionAgreement>("/api/v1/contributions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listContributionRecords(id: string) {
  return request<ContributionRecord[]>(`/api/v1/contributions/${id}/records`);
}

export function recordContribution(id: string, body: {
  amount: string;
  contributed_on: string;
  transaction_id?: string;
  note?: string;
}) {
  return request<ContributionRecord>(`/api/v1/contributions/${id}/records`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}


export type ReceiptDocument = {
  id: string;
  account_id: string;
  filename: string | null;
  media_type: string;
  status: string;
  merchant: string | null;
  date: string | null;
  amount: string | null;
  currency: string | null;
  extracted: {
    overall_confidence?: number;
    field_confidence?: Record<string, number>;
    warnings?: string[];
  };
  transaction_id: string | null;
  created_at: string | null;
};

export function getReceipts() {
  return request<ReceiptDocument[]>("/api/v1/receipts");
}

export function previewReceipt(accountId: string, file: File) {
  const body = new FormData();
  body.set("account_id", accountId);
  body.set("file", file);
  return request<ReceiptDocument>("/api/v1/receipts/preview", { method: "POST", body });
}

export function correctReceipt(id: string, body: {
  amount?: string;
  date?: string;
  merchant?: string | null;
  currency?: string;
}) {
  return request<ReceiptDocument>(`/api/v1/receipts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function approveReceipt(id: string) {
  return request<ReceiptDocument>(`/api/v1/receipts/${id}/approve`, { method: "POST" });
}

export function rejectReceipt(id: string) {
  return request<ReceiptDocument>(`/api/v1/receipts/${id}/reject`, { method: "POST" });
}

export type BankConnection = { id: string; account_id: string; institution_name: string | null; masked_account_number: string | null; currency: string | null; status: string; data_status: string; last_error: string | null };
export type ReconciliationItem = { id: string; date: string; amount: string; currency: string; type: string; merchant: string | null; description: string | null; status: string; match_reason: string | null; suggested_transaction: Transaction | null };
export type ReconciliationSession = { id: string; account_id: string; source: string; status: string; total_rows: number; matched_count: number; suggested_count: number; unmatched_count: number; conflict_count: number; balance_difference: string | null; items?: ReconciliationItem[] };
export const getBankConnections = () => request<BankConnection[]>("/api/v1/bank-connections");
export const initiateBankConnection = (id: string) => request<{mono_url:string}>("/api/v1/bank-connections/initiate?account_id="+encodeURIComponent(id),{method:"POST"});
export const syncBankConnection = (id: string) => request<{session_id:string}>("/api/v1/bank-connections/"+id+"/sync",{method:"POST"});
export const disconnectBankConnection = (id: string) => request<BankConnection>("/api/v1/bank-connections/"+id+"/disconnect",{method:"POST"});
export const reauthorizeBankConnection = (id: string) => request<{mono_url:string}>("/api/v1/bank-connections/"+id+"/reauthorize",{method:"POST"});
export const getReconciliationSessions = () => request<ReconciliationSession[]>("/api/v1/reconciliation/sessions");
export const getReconciliationSession = (id: string) => request<ReconciliationSession>("/api/v1/reconciliation/sessions/"+id);
export function previewReconciliationStatement(accountId: string,file: File) { const body=new FormData(); body.set("account_id",accountId); body.set("file",file); return request<ReconciliationSession>("/api/v1/reconciliation/sessions/preview",{method:"POST",body}); }
export const matchReconciliationItem = (id: string,transactionId: string) => request<ReconciliationItem>("/api/v1/reconciliation/items/"+id+"/match",{method:"POST",body:JSON.stringify({transaction_id:transactionId})});
export const postReconciliationItem = (id: string) => request<ReconciliationItem>("/api/v1/reconciliation/items/"+id+"/post",{method:"POST"});
export const ignoreReconciliationItem = (id: string) => request<ReconciliationItem>("/api/v1/reconciliation/items/"+id+"/ignore",{method:"POST"});
export const completeReconciliationSession = (id: string) => request<ReconciliationSession>("/api/v1/reconciliation/sessions/"+id+"/complete",{method:"POST"});

export type ReconciliationCandidate = Pick<Transaction, "id" | "date" | "amount" | "currency" | "type" | "merchant" | "description">;
export const getReconciliationCandidates = (id: string) =>
  request<ReconciliationCandidate[]>("/api/v1/reconciliation/items/" + id + "/candidates");
