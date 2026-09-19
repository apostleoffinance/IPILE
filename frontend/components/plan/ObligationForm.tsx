"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { obligationSchema, type ObligationFormValues } from "@/lib/forms";

export type ObligationDraft = ObligationFormValues;

export function ObligationForm({
  onSubmit,
  pending,
}: {
  onSubmit: (draft: ObligationDraft) => Promise<void>;
  pending: boolean;
}) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ObligationFormValues>({
    resolver: zodResolver(obligationSchema),
    defaultValues: {
      name: "",
      amount: "",
      frequency: "monthly",
      next_due_date: new Date().toISOString().slice(0, 10),
      sinking_fund: false,
    },
  });

  return (
    <form
      onSubmit={handleSubmit(async (values) => {
        await onSubmit(values);
        reset({
          name: "",
          amount: "",
          frequency: values.frequency,
          next_due_date: values.next_due_date,
          sinking_fund: false,
        });
      })}
      className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2"
    >
      <div>
        <Label htmlFor="ob-name">Name</Label>
        <Input id="ob-name" className="mt-1" {...register("name")} />
        {errors.name ? <p className="mt-1 text-xs text-critical">{errors.name.message}</p> : null}
      </div>
      <div>
        <Label htmlFor="ob-amount">Amount</Label>
        <Input id="ob-amount" className="mt-1 tabular" placeholder="450000.00" {...register("amount")} />
        {errors.amount ? <p className="mt-1 text-xs text-critical">{errors.amount.message}</p> : null}
      </div>
      <div>
        <Label htmlFor="ob-frequency">Frequency</Label>
        <select
          id="ob-frequency"
          className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
          {...register("frequency")}
        >
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="quarterly">Quarterly</option>
          <option value="annual">Annual</option>
          <option value="one_time">One time</option>
        </select>
      </div>
      <div>
        <Label htmlFor="ob-due">Next due</Label>
        <Input id="ob-due" type="date" className="mt-1" {...register("next_due_date")} />
        {errors.next_due_date ? (
          <p className="mt-1 text-xs text-critical">{errors.next_due_date.message}</p>
        ) : null}
      </div>
      <label className="flex items-center gap-2 text-sm md:col-span-2">
        <input type="checkbox" {...register("sinking_fund")} />
        Use sinking fund
      </label>
      <div className="md:col-span-2">
        <Button type="submit" disabled={pending}>
          {pending ? "Saving..." : "Add obligation"}
        </Button>
      </div>
    </form>
  );
}
