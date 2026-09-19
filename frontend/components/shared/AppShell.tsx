"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BriefcaseBusiness,
  CalendarDays,
  ChevronRight,
  CircleHelp,
  Home,
  Inbox,
  LineChart,
  MoreHorizontal,
  Plus,
  Settings,
  Sparkles,
  Search,
  Users,
  Wallet,
  Landmark,
  LogOut,
} from "lucide-react";
import { Wordmark } from "@/components/brand/Wordmark";
import { GlobalAddMenu } from "@/components/shared/GlobalAddMenu";
import { CommandMenu, type CommandItem } from "@/components/ui/command-menu";
import { LoadingState } from "@/components/shared/LoadingState";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { api, setHouseholdId, type HouseholdMembership, type User } from "@/lib/api";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "ffos_household_id";

type NavChild = { href: string; label: string };
type NavGroup = {
  href: string;
  label: string;
  match: string;
  icon: typeof Home;
  children?: NavChild[];
};

const primaryNav: NavGroup[] = [
  { href: "/overview", label: "Home", match: "/overview", icon: Home },
  {
    href: "/money/transactions",
    label: "Money",
    match: "/money",
    icon: Wallet,
    children: [
      { href: "/money/transactions", label: "Transactions" },
      { href: "/money/accounts", label: "Accounts" },
      { href: "/money/income", label: "Income" },
      { href: "/money/cash-flow", label: "Cash flow" },
      { href: "/money/import", label: "Import" },
    ],
  },
  {
    href: "/plan/budget",
    label: "Plan",
    match: "/plan",
    icon: Landmark,
    children: [
      { href: "/plan/budget", label: "Budget" },
      { href: "/plan/obligations", label: "Obligations" },
      { href: "/plan/funds", label: "Funds" },
      { href: "/plan/recurring", label: "Recurring" },
      { href: "/plan/allocation", label: "Allocation" },
    ],
  },
  {
    href: "/family/members",
    label: "Family",
    match: "/family",
    icon: Users,
    children: [
      { href: "/family/members", label: "Members" },
      { href: "/family/giving", label: "Giving" },
    ],
  },
  {
    href: "/wealth",
    label: "Wealth",
    match: "/wealth",
    icon: LineChart,
    children: [
      { href: "/wealth", label: "Overview" },
      { href: "/wealth/investments", label: "Investments" },
      { href: "/wealth/goals", label: "Goals" },
      { href: "/wealth/debts", label: "Debts" },
    ],
  },
];

const moreLinks = [
  { href: "/forecast", label: "Forecast", icon: CalendarDays },
  { href: "/business", label: "Businesses", icon: BriefcaseBusiness },
  { href: "/business/revenue", label: "Business revenue", icon: BriefcaseBusiness },
  { href: "/business/expenses", label: "Business expenses", icon: BriefcaseBusiness },
  { href: "/business/pnl", label: "Business P&L", icon: BriefcaseBusiness },
  { href: "/insights", label: "Insights", icon: Sparkles },
  { href: "/reports", label: "Reports", icon: LineChart },
  { href: "/calendar", label: "Calendar", icon: CalendarDays },
  { href: "/simulate", label: "Simulator", icon: Sparkles },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/help", label: "Help", icon: CircleHelp },
];

const commandItems: CommandItem[] = [
  ...primaryNav.flatMap((group) => [
    { label: group.label, href: group.href, keywords: group.children?.map((child) => child.label).join(" ") },
    ...(group.children ?? []).map((child) => ({ label: child.label, href: child.href, keywords: group.label })),
  ]),
  ...moreLinks.map((link) => ({ label: link.label, href: link.href })),
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [activeId, setActiveId] = useState<string | undefined>();
  const [addOpen, setAddOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

  useEffect(() => {
    api
      .me()
      .then((me) => {
        setUser(me);
        const households = me.households ?? [];
        if (households.length === 0) {
          router.replace("/onboarding");
          return;
        }
        const saved = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
        const match = households.find((h) => h.id === saved) ?? households[0];
        setActiveId(match.id);
        setHouseholdId(match.id);
        window.localStorage.setItem(STORAGE_KEY, match.id);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  function switchHousehold(id: string) {
    setActiveId(id);
    setHouseholdId(id);
    window.localStorage.setItem(STORAGE_KEY, id);
    window.location.assign(pathname.startsWith("/onboarding") ? "/overview" : pathname);
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas">
        <LoadingState />
      </main>
    );
  }

  const households = user.households ?? [];
  const household = households.find((h) => h.id === activeId) ?? households[0];

  return (
    <div className="min-h-screen md:grid md:grid-cols-[248px_1fr]">
      <aside className="hidden border-r border-line bg-surface px-5 py-7 md:flex md:flex-col">
        <Wordmark href="/overview" tone="light" size="sm" />
        {households.length > 1 ? (
          <label className="mt-4 block text-sm">
            <span className="sr-only">Household</span>
            <select
              className="mt-1 w-full border border-line bg-canvas px-2 py-1.5 text-sm"
              value={household?.id}
              onChange={(e) => switchHousehold(e.target.value)}
            >
              {households.map((row: HouseholdMembership) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <p className="mt-3 text-sm text-muted">{household?.name ?? "Household"}</p>
        )}
        <nav className="mt-8 flex-1 space-y-1 text-sm">
          {primaryNav.map((link) => {
            const sectionActive =
              pathname === link.match ||
              pathname.startsWith(link.match + "/") ||
              (link.match === "/overview" && pathname === "/overview") ||
              (link.match === "/wealth" && pathname.startsWith("/wealth"));
            const Icon = link.icon;
            return (
              <div key={link.href} className="space-y-0.5">
                <NavLink href={link.href} active={sectionActive}>
                  <Icon className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
                  <span className="flex-1">{link.label}</span>
                  {link.children ? (
                    <ChevronRight
                      className={cn("h-3.5 w-3.5 text-muted transition-transform", sectionActive && "rotate-90")}
                      aria-hidden
                    />
                  ) : null}
                </NavLink>
                {link.children && sectionActive ? (
                  <div className="ml-2 space-y-0.5 border-l border-line pl-2">
                    {link.children.map((child) => (
                      <NavLink
                        key={child.href}
                        href={child.href}
                        active={
                          child.href === "/wealth"
                            ? pathname === "/wealth"
                            : pathname === child.href || pathname.startsWith(child.href + "/")
                        }
                        nested
                      >
                        {child.label}
                      </NavLink>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
          <p className="pt-5 text-[11px] uppercase tracking-[0.18em] text-muted">More</p>
          {moreLinks.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.href}
                href={link.href}
                active={pathname === link.href || pathname.startsWith(link.href + "/")}
              >
                <Icon className="h-4 w-4 shrink-0 opacity-70" aria-hidden />
                <span>{link.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <Button type="button" className="mt-4 w-full" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4" aria-hidden />
          Add
        </Button>
        <Link href="/insights" className="mt-2 block text-center text-sm text-gold underline">
          Ask IPÌLẸ̀
        </Link>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="flex items-center justify-between border-b border-line bg-surface/90 px-5 py-3 backdrop-blur md:px-10">
          <div className="md:hidden">
            <Wordmark href="/overview" tone="light" size="sm" />
          </div>
          <p className="hidden text-sm text-muted md:block">{user.display_name}</p>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setCommandOpen((value) => !value)}
              aria-label="Search pages"
              aria-expanded={commandOpen}
            >
              <Search className="h-4 w-4" aria-hidden="true" />
            </Button>
            <ThemeToggle />
            <Button
              type="button"
              size="sm"
              className="hidden md:inline-flex"
              onClick={() => setAddOpen(true)}
            >
              <Plus className="h-4 w-4" aria-hidden />
              Add
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={async () => {
                await api.logout();
                setHouseholdId(undefined);
                window.localStorage.removeItem(STORAGE_KEY);
                router.replace("/login");
              }}
            >
              <LogOut className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </header>
        {commandOpen ? (
          <div className="border-b border-line bg-canvas px-5 py-3 md:px-10">
            <CommandMenu items={commandItems} className="mx-auto max-w-xl" />
          </div>
        ) : null}
        <main id="main-content" tabIndex={-1} className="flex-1 px-5 py-8 outline-none md:px-10">
          {children}
        </main>
        <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-surface text-center text-[11px] md:hidden">
          {primaryNav.slice(0, 4).map((link) => {
            const Icon = link.icon;
            const active =
              pathname.startsWith(link.match) || (link.match === "/overview" && pathname === "/overview");
            return (
              <Link
                key={link.href}
                href={link.href}
                className={tabClass(active)}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="mx-auto mb-0.5 h-4 w-4" aria-hidden />
                {link.label}
              </Link>
            );
          })}
          <button
            type="button"
            className={tabClass(moreOpen)}
            onClick={() => setMoreOpen((v) => !v)}
            aria-expanded={moreOpen}
            aria-controls="mobile-more-menu"
          >
            <MoreHorizontal className="mx-auto mb-0.5 h-4 w-4" aria-hidden />
            More
          </button>
        </nav>
        <Button
          type="button"
          size="icon"
          onClick={() => setAddOpen(true)}
          className="fixed bottom-16 right-4 z-30 h-12 w-12 rounded-full shadow-lg md:hidden"
          aria-label="Add"
        >
          <Plus className="h-5 w-5" />
        </Button>
        {moreOpen ? (
          <div id="mobile-more-menu" className="fixed inset-x-0 bottom-12 z-30 max-h-[70vh] overflow-y-auto border-t border-line bg-surface p-4 md:hidden">
            <div className="space-y-4 text-sm">
              {primaryNav.slice(1).map((group) => (
                <section key={group.href}>
                  <Link href={group.href} className="font-medium text-accent" onClick={() => setMoreOpen(false)}>{group.label}</Link>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    {(group.children ?? []).map((child) => (
                      <Link key={child.href} href={child.href} className="border border-line px-3 py-2" onClick={() => setMoreOpen(false)}>
                        {child.label}
                      </Link>
                    ))}
                  </div>
                </section>
              ))}
              <div className="grid grid-cols-2 gap-2">
              {moreLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="border border-line px-3 py-2"
                  onClick={() => setMoreOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
      <GlobalAddMenu open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}

function NavLink({
  href,
  active,
  children,
  nested = false,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
  nested?: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-2 rounded-md px-2 py-1.5",
        nested && "py-1 text-[13px]",
        active ? "bg-subtle font-medium text-accent" : "text-muted hover:bg-subtle/70 hover:text-ink",
      )}
    >
      {children}
    </Link>
  );
}

function tabClass(active: boolean) {
  return cn("px-1 py-2.5", active ? "text-accent" : "text-muted");
}
