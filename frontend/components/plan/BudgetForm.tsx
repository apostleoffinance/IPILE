import { FormEvent, useMemo, useState } from "react";
import type { Category, Member } from "@/lib/api";

export type BudgetDraft = {
  name: string;
  member_id?: string;
  categories: { category_id: string; allocated_amount: string }[];
};

type Line = { category_id: string; allocated_amount: string };

export function BudgetForm({
  categories,
  members,
  defaultMemberId,
  onSubmit,
  pending,
}: {
  categories: Category[];
  members: Member[];
  defaultMemberId?: string;
  onSubmit: (draft: BudgetDraft) => Promise<void>;
  pending: boolean;
}) {
  const usable = useMemo(
    () => categories.filter((category) => category.kind === "expense" || category.kind === "giving"),
    [categories],
  );
  const [name, setName] = useState("");
  const [memberId, setMemberId] = useState(defaultMemberId ?? "");
  const [lines, setLines] = useState<Line[]>([{ category_id: usable[0]?.id ?? "", allocated_amount: "" }]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await onSubmit({
      name,
      member_id: memberId || undefined,
      categories: lines.filter((line) => line.category_id && line.allocated_amount),
    });
    setName("");
    setLines([{ category_id: usable[0]?.id ?? "", allocated_amount: "" }]);
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 rounded-md border border-line bg-surface p-5">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-sm">
          Budget name
          <input
            required
            className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Household essentials"
          />
        </label>
        <label className="block text-sm">
          Member scope
          <select
            className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
            value={memberId}
            onChange={(event) => setMemberId(event.target.value)}
          >
            <option value="">Whole household</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="space-y-3">
        {lines.map((line, index) => (
          <div key={`${line.category_id}-${index}`} className="grid gap-3 md:grid-cols-[1fr_160px_auto]">
            <select
              required
              className="rounded-md border border-line bg-canvas px-3 py-2 text-sm"
              value={line.category_id}
              onChange={(event) => {
                const next = [...lines];
                next[index] = { ...line, category_id: event.target.value };
                setLines(next);
              }}
            >
              <option value="">Category</option>
              {usable.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <input
              required
              className="rounded-md border border-line bg-canvas px-3 py-2 text-sm tabular"
              value={line.allocated_amount}
              onChange={(event) => {
                const next = [...lines];
                next[index] = { ...line, allocated_amount: event.target.value };
                setLines(next);
              }}
              placeholder="250000.00"
            />
            <button
              type="button"
              className="text-sm text-muted underline"
              onClick={() => setLines(lines.filter((_, lineIndex) => lineIndex !== index))}
              disabled={lines.length === 1}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4">
        <button
          type="button"
          className="text-sm text-accent underline"
          onClick={() => setLines([...lines, { category_id: "", allocated_amount: "" }])}
        >
          Add category
        </button>
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-accent px-4 py-2 text-sm text-white disabled:opacity-60"
        >
          {pending ? "Saving…" : "Create budget"}
        </button>
      </div>
    </form>
  );
}
