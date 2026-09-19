"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CategorySelector } from "@/components/transactions/CategorySelector";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { recurringSchema, type RecurringFormValues } from "@/lib/forms";
import type { Account, Category, Member } from "@/lib/api";

export type RecurringDraft = {
  account_id: string;
  amount: string;
  type: string;
  frequency: string;
  next_date: string;
  category_id?: string;
  member_id?: string;
  counterparty_account_id?: string;
  description?: string;
};

export function RecurringForm({
  accounts,
  categories,
  members,
  onSubmit,
  pending,
}: {
  accounts: Account[];
  categories: Category[];
  members: Member[];
  onSubmit: (draft: RecurringDraft) => Promise<void>;
  pending: boolean;
}) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<RecurringFormValues>({
    resolver: zodResolver(recurringSchema),
    defaultValues: {
      type: "expense",
      amount: "",
      account_id: accounts[0]?.id ?? "",
      frequency: "monthly",
      next_date: new Date().toISOString().slice(0, 10),
      category_id: "",
      member_id: "",
      counterparty_account_id: "",
      description: "",
    },
  });

  const type = watch("type");
  const accountId = watch("account_id");
  const categoryId = watch("category_id") ?? "";

  useEffect(() => {
    if (!accountId && accounts[0]?.id) setValue("account_id", accounts[0].id);
  }, [accountId, accounts, setValue]);

  return (
    <form
      onSubmit={handleSubmit(async (values) => {
        await onSubmit({
          account_id: values.account_id,
          amount: values.amount,
          type: values.type,
          frequency: values.frequency,
          next_date: values.next_date,
          category_id: values.category_id || undefined,
          member_id: values.member_id || undefined,
          counterparty_account_id: values.type === "transfer" ? values.counterparty_account_id : undefined,
          description: values.description || undefined,
        });
        reset({
          type: values.type,
          amount: "",
          account_id: values.account_id,
          frequency: values.frequency,
          next_date: values.next_date,
          category_id: "",
          member_id: values.member_id ?? "",
          counterparty_account_id: "",
          description: "",
        });
      })}
      className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2"
    >
      <div>
        <Label htmlFor="recurring-type">Type</Label>
        <select
          id="recurring-type"
          className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
          {...register("type")}
        >
          <option value="expense">Expense</option>
          <option value="income">Income</option>
          <option value="transfer">Transfer</option>
          <option value="giving">Giving</option>
        </select>
      </div>
      <div>
        <Label htmlFor="recurring-amount">Amount</Label>
        <Input id="recurring-amount" className="mt-1 tabular" placeholder="40000.00" {...register("amount")} />
        {errors.amount ? <p className="mt-1 text-xs text-critical">{errors.amount.message}</p> : null}
      </div>
      <div>
        <Label htmlFor="recurring-account">Account</Label>
        <select
          id="recurring-account"
          className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
          {...register("account_id")}
        >
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </select>
        {errors.account_id ? <p className="mt-1 text-xs text-critical">{errors.account_id.message}</p> : null}
      </div>
      {type === "transfer" ? (
        <div>
          <Label htmlFor="recurring-counterparty">To account</Label>
          <select
            id="recurring-counterparty"
            className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
            {...register("counterparty_account_id")}
          >
            <option value="">Select account</option>
            {accounts
              .filter((account) => account.id !== accountId)
              .map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
          </select>
          {errors.counterparty_account_id ? (
            <p className="mt-1 text-xs text-critical">{errors.counterparty_account_id.message}</p>
          ) : null}
        </div>
      ) : (
        <div>
          <Label>Category</Label>
          <div className="mt-1">
            <CategorySelector
              categories={categories}
              value={categoryId}
              onChange={(value) => setValue("category_id", value, { shouldValidate: true })}
            />
          </div>
        </div>
      )}
      <div>
        <Label htmlFor="recurring-frequency">Frequency</Label>
        <select
          id="recurring-frequency"
          className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
          {...register("frequency")}
        >
          <option value="weekly">Weekly</option>
          <option value="biweekly">Every two weeks</option>
          <option value="monthly">Monthly</option>
          <option value="quarterly">Quarterly</option>
          <option value="annual">Annual</option>
        </select>
      </div>
      <div>
        <Label htmlFor="recurring-next">Next date</Label>
        <Input id="recurring-next" type="date" className="mt-1" {...register("next_date")} />
        {errors.next_date ? <p className="mt-1 text-xs text-critical">{errors.next_date.message}</p> : null}
      </div>
      {members.length > 0 ? (
        <div>
          <Label htmlFor="recurring-member">Member</Label>
          <select
            id="recurring-member"
            className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
            {...register("member_id")}
          >
            <option value="">Household</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      <div>
        <Label htmlFor="recurring-description">Description</Label>
        <Input id="recurring-description" className="mt-1" {...register("description")} />
      </div>
      <div className="md:col-span-2">
        <Button type="submit" disabled={pending || !accounts.length}>
          {pending ? "Saving..." : "Add recurring"}
        </Button>
      </div>
    </form>
  );
}
