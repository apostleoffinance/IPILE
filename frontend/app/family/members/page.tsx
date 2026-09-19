"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
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
      <ContentContainer>
        <PageHeader
          title="Members"
          description="Who is in this household? Dependents can have their own budgets."
        />
        {error ? <ErrorState message={error} /> : null}
        <SectionHeader title="Add member" />
        <form onSubmit={onSubmit} className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2">
          <div>
            <Label htmlFor="member-name">Display name</Label>
            <Input
              id="member-name"
              required
              className="mt-1"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="member-role">Role</Label>
            <Select
              id="member-role"
              className="mt-1"
              value={role}
              onChange={(event) => setRole(event.target.value)}
            >
              <option value="partner">Partner</option>
              <option value="member">Member</option>
              <option value="viewer">Viewer</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="member-relationship">Relationship</Label>
            <Select
              id="member-relationship"
              className="mt-1"
              value={relationship}
              onChange={(event) => setRelationship(event.target.value)}
            >
              <option value="spouse">Spouse</option>
              <option value="child">Child</option>
              <option value="parent">Parent</option>
              <option value="sibling">Sibling</option>
              <option value="other">Other</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="member-type">Member type</Label>
            <Select
              id="member-type"
              className="mt-1"
              value={memberType}
              onChange={(event) => setMemberType(event.target.value)}
            >
              <option value="adult">Adult</option>
              <option value="dependent">Dependent</option>
            </Select>
          </div>
          <div>
            <Button type="submit">Add member</Button>
          </div>
        </form>
        <SectionHeader title="Household" />
        {members.length === 0 ? (
          <EmptyState title="No members" body="A household always has an owner after registration." />
        ) : (
          <div className="overflow-x-auto border border-line bg-surface">
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
      </ContentContainer>
    </AppShell>
  );
}
