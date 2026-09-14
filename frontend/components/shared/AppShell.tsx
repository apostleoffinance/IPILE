"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Wordmark } from "@/components/brand/Wordmark";
import { GlobalAddMenu } from "@/components/shared/GlobalAddMenu";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, setHouseholdId, type HouseholdMembership, type User } from "@/lib/api";

const STORAGE_KEY = "ffos_household_id";

const primaryNav = [
  { href: "/overview", label: "Home" },
  { href: "/money/transactions", label: "Money", match: "/money" },
  { href: "/plan/budget", label: "Plan", match: "/plan" },
  { href: "/wealth", label: "Wealth", match: "/wealth" },
  { href: "/family/members", label: "Family", match: "/family" },
];

const moreLinks = [
  { href: "/business", label: "Businesses" },
  { href: "/insights", label: "Insights" },
  { href: "/reports", label: "Reports" },
  { href: "/simulate", label: "Simulator" },
  { href: "/inbox", label: "Inbox" },
  { href: "/plan/allocation", label: "Money plan" },
  { href: "/settings", label: "Settings" },
  { href: "/help", label: "Help" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [activeId, setActiveId] = useState<string | undefined>();
  const [addOpen, setAddOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

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
          {primaryNav.map((link) => (
            <NavLink
              key={link.href}
              href={link.href}
              active={
                link.match ? pathname.startsWith(link.match) : pathname === link.href
              }
            >
              {link.label}
            </NavLink>
          ))}
          <p className="pt-5 text-[11px] uppercase tracking-[0.18em] text-muted">More</p>
          {moreLinks.map((link) => (
            <NavLink key={link.href} href={link.href} active={pathname === link.href || pathname.startsWith(link.href + "/")}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="mt-4 w-full bg-accent px-3 py-2.5 text-sm text-white"
        >
          + Add
        </button>
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
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="hidden rounded-full bg-accent px-3 py-1.5 text-sm text-white md:inline"
              onClick={() => setAddOpen(true)}
            >
              + Add
            </button>
            <button
              type="button"
              className="text-sm text-muted underline"
              onClick={async () => {
                await api.logout();
                setHouseholdId(undefined);
                window.localStorage.removeItem(STORAGE_KEY);
                router.replace("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 px-5 py-8 md:px-10">{children}</main>
        <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-surface text-center text-[11px] md:hidden">
          {primaryNav.slice(0, 4).map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={tabClass(
                link.match ? pathname.startsWith(link.match) : pathname === link.href,
              )}
            >
              {link.label}
            </Link>
          ))}
          <button type="button" className={tabClass(moreOpen)} onClick={() => setMoreOpen((v) => !v)}>
            More
          </button>
        </nav>
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="fixed bottom-16 right-4 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-xl text-white shadow-lg md:hidden"
          aria-label="Add"
        >
          +
        </button>
        {moreOpen ? (
          <div className="fixed inset-x-0 bottom-12 z-30 border-t border-line bg-surface p-4 md:hidden">
            <div className="grid grid-cols-2 gap-2 text-sm">
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
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`block rounded-md px-2 py-1.5 ${active ? "bg-subtle font-medium text-accent" : "text-muted"}`}
    >
      {children}
    </Link>
  );
}

function tabClass(active: boolean) {
  return `px-1 py-3 ${active ? "text-accent" : "text-muted"}`;
}
