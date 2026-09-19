const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "")
).replace(/\/$/, "");

function requireApiUrl() {
  if (!API_URL) {
    throw new Error(
      "The production API URL is missing. Set NEXT_PUBLIC_API_URL in Vercel and redeploy.",
    );
  }
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
  timezone: string;
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
  is_emergency?: boolean;
  status: string;
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
  amount: string;
  currency: string;
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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
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
      `Unable to reach the IPÌLẸ̀ API at ${apiUrl}. Check backend availability and CORS settings.`,
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
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.detail ?? data.error?.message ?? "Request failed.";
    throw new Error(typeof message === "string" ? message : "Request failed.");
  }
  return data as T;
}

export function getOverview() {
  return request<HouseholdOverview>("/api/v1/overview");
}

export function getCurrentHousehold() {
  return request<Household>("/api/v1/households/current");
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
  source: string;
  filename: string | null;
  status: string;
  created_count: number;
  skipped_count: number;
  error_count: number;
  result: { errors?: string[] };
};

export function importCsv(body: { account_id: string; content: string; filename?: string }) {
  return request<ImportJob>("/api/v1/imports/csv", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function importStatement(body: { account_id: string; content: string; filename?: string }) {
  return request<ImportJob>("/api/v1/imports/statement", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

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
  token: string;
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

export function acceptInvite(token: string) {
  return request<{ id: string; role: string }>("/api/v1/invites/accept", {
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

export function onboardHousehold(body: { name: string; minimum_buffer_amount?: string }) {
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
  me: () => request<User>("/api/v1/auth/me"),
  register: (body: {
    email: string;
    password: string;
    display_name: string;
    invite_token?: string;
    create_household?: boolean;
  }) =>
    request<User>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(body) }).then(
      (user) => {
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
      clearCsrfToken();
    }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    request<void>("/api/v1/auth/password/change", { method: "POST", body: JSON.stringify(body) }),
  getOverview,
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
  accounts: () => request<Account[]>("/api/v1/accounts"),
  createAccount: (body: {
    name: string;
    type: string;
    institution?: string;
    current_balance?: string;
    is_protected?: boolean;
  }) => request<Account>("/api/v1/accounts", { method: "POST", body: JSON.stringify(body) }),
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
    description?: string;
    merchant?: string;
  }) => request<Transaction>("/api/v1/transactions", { method: "POST", body: JSON.stringify(body) }),
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
