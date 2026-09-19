"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CategorySelector } from "@/components/transactions/CategorySelector";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { transactionSchema, type TransactionFormValues } from "@/lib/forms";
import type { Account, Category, Member } from "@/lib/api";

export type TransactionDraft = {
  account_id: string;
  amount: string;
  type: string;
  date: string;
  counterparty_account_id?: string;
  category_id?: string;
  member_id?: string;
  description?: string;
};

export function TransactionForm({
  accounts,
  categories,
  members = [],
  onSubmit,
  pending,
}: {
  accounts: Account[];
  categories: Category[];
  members?: Member[];
  onSubmit: (draft: TransactionDraft) => Promise<void>;
  pending: boolean;
}) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<TransactionFormValues>({
    resolver: zodResolver(transactionSchema),
    defaultValues: {
      type: "expense",
      amount: "",
      account_id: accounts[0]?.id ?? "",
      counterparty_account_id: "",
      category_id: "",
      member_id: "",
      date: new Date().toISOString().slice(0, 10),
      description: "",
    },
  });

  const type = watch("type");
  const accountId = watch("account_id");
  const categoryId = watch("category_id") ?? "";

  useEffect(() => {
    if (!accountId && accounts[0]?.id) {
      setValue("account_id", accounts[0].id);
    }
  }, [accountId, accounts, setValue]);

  return (
    <form
      onSubmit={handleSubmit(async (values) => {
        await onSubmit({
          account_id: values.account_id,
          amount: values.amount,
          type: values.type,
          date: values.date,
          counterparty_account_id: values.type === "transfer" ? values.counterparty_account_id : undefined,
          category_id: values.category_id || undefined,
          member_id: values.member_id || undefined,
          description: values.description || undefined,
        });
        reset({
          type: values.type,
          amount: "",
          account_id: values.account_id,
          counterparty_account_id: "",
          category_id: "",
          member_id: values.member_id ?? "",
          date: values.date,
          description: "",
        });
      })}
      className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2"
    >
      <div>
        <Label htmlFor="tx-type">Type</Label>
        <Select id="tx-type" className="mt-1" {...register("type")}>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
          <option value="transfer">Transfer</option>
          <option value="giving">Giving</option>
          <option value="refund">Refund</option>
        </Select>
      </div>
      <div>
        <Label htmlFor="tx-amount">Amount</Label>
        <Input id="tx-amount" className="mt-1 tabular" placeholder="150000.00" {...register("amount")} />
        {errors.amount ? <p className="mt-1 text-xs text-critical">{errors.amount.message}</p> : null}
      </div>
      <div>
        <Label htmlFor="tx-account">Account</Label>
        <Select id="tx-account" className="mt-1" {...register("account_id")}>
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        {errors.account_id ? <p className="mt-1 text-xs text-critical">{errors.account_id.message}</p> : null}
      </div>
      {type === "transfer" ? (
        <div>
          <Label htmlFor="tx-counterparty">To account</Label>
          <Select id="tx-counterparty" className="mt-1" {...register("counterparty_account_id")}>
            <option value="">Select account</option>
            {accounts
              .filter((account) => account.id !== accountId)
              .map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
          </Select>
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
      {members.length > 0 ? (
        <div>
          <Label htmlFor="tx-member">Member</Label>
          <Select id="tx-member" className="mt-1" {...register("member_id")}>
            <option value="">Household</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </Select>
        </div>
      ) : null}
      <div>
        <Label htmlFor="tx-date">Date</Label>
        <Input id="tx-date" type="date" className="mt-1" {...register("date")} />
        {errors.date ? <p className="mt-1 text-xs text-critical">{errors.date.message}</p> : null}
      </div>
      <div>
        <Label htmlFor="tx-description">Description</Label>
        <Input id="tx-description" className="mt-1" {...register("description")} />
      </div>
      <div className="md:col-span-2">
        <Button type="submit" disabled={pending || !accounts.length}>
          {pending ? "Saving..." : "Record transaction"}
        </Button>
      </div>
    </form>
  );
}
