"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { api, type Member } from "@/lib/api";

export default function MembersPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("member");
  const [relationship, setRelationship] = useState("child");
  const [memberType, setMemberType] = useState("dependent");

  async function refresh() {
    setMembers(await api.members());
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.createMember({
        display_name: displayName,
        role,
        relationship,
        member_type: memberType,
      });
      setDisplayName("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add member.");
    }
  }

  return (
    <AppShell>
      <div className="space-y-6 pb-16">
        <div>
          <p className="text-sm text-muted">Who is in this household?</p>
          <h1 className="mt-1 text-3xl font-medium">Members</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        <form onSubmit={onSubmit} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
          <label className="block text-sm">
            Display name
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Role
            <select
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={role}
              onChange={(event) => setRole(event.target.value)}
            >
              <option value="partner">Partner</option>
              <option value="member">Member</option>
              <option value="viewer">Viewer</option>
            </select>
          </label>
          <label className="block text-sm">
            Relationship
            <select
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={relationship}
              onChange={(event) => setRelationship(event.target.value)}
            >
              <option value="spouse">Spouse</option>
              <option value="child">Child</option>
              <option value="parent">Parent</option>
              <option value="sibling">Sibling</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="block text-sm">
            Member type
            <select
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={memberType}
              onChange={(event) => setMemberType(event.target.value)}
            >
              <option value="adult">Adult</option>
              <option value="dependent">Dependent</option>
            </select>
          </label>
          <div>
            <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm text-white">
              Add member
            </button>
          </div>
        </form>
        {members.length === 0 ? (
          <EmptyState title="No members" body="A household always has an owner after registration." />
        ) : (
          <div className="overflow-x-auto rounded-md border border-line bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Role</th>
                  <th className="px-4 py-3 font-medium">Relationship</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3">{member.display_name}</td>
                    <td className="px-4 py-3 capitalize">{member.role}</td>
                    <td className="px-4 py-3 capitalize">{member.relationship}</td>
                    <td className="px-4 py-3 capitalize">
                      {member.member_type}
                      {member.member_type === "dependent" ? (
                        <Link
                          className="ml-2 text-xs text-accent underline"
                          href={`/plan/budget?member=${member.id}`}
                        >
                          Add budget
                        </Link>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
