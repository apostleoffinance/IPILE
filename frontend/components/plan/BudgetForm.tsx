"use client";

import { useEffect, useMemo } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { budgetSchema, type BudgetFormValues } from "@/lib/forms";
import type { Category, Member } from "@/lib/api";

export type BudgetDraft = {
  name: string;
  period_type?: string;
  start_date?: string;
  end_date?: string;
  member_id?: string;
  categories: { category_id: string; allocated_amount: string }[];
};

const PERIOD_OPTIONS = [
  { value: "monthly", label: "Monthly" },
  { value: "weekly", label: "Weekly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "annual", label: "Annual" },
  { value: "custom", label: "Custom" },
] as const;

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

  const {
    register,
    control,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<BudgetFormValues>({
    resolver: zodResolver(budgetSchema),
    defaultValues: {
      name: "",
      period_type: "monthly",
      start_date: "",
      end_date: "",
      member_id: defaultMemberId ?? "",
      categories: [{ category_id: usable[0]?.id ?? "", allocated_amount: "" }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "categories" });
  const periodType = watch("period_type");

  useEffect(() => {
    if (defaultMemberId) {
      reset((prev) => ({ ...prev, member_id: defaultMemberId }));
    }
  }, [defaultMemberId, reset]);

  return (
    <form
      onSubmit={handleSubmit(async (values) => {
        await onSubmit({
          name: values.name,
          period_type: values.period_type,
          start_date: values.start_date || undefined,
          end_date: values.end_date || undefined,
          member_id: values.member_id || undefined,
          categories: values.categories,
        });
        reset({
          name: "",
          period_type: "monthly",
          start_date: "",
          end_date: "",
          member_id: defaultMemberId ?? "",
          categories: [{ category_id: usable[0]?.id ?? "", allocated_amount: "" }],
        });
      })}
      className="grid gap-4 border border-line bg-surface p-5"
    >
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor="budget-name">Budget name</Label>
          <Input id="budget-name" className="mt-1" placeholder="Household essentials" {...register("name")} />
          {errors.name ? <p className="mt-1 text-xs text-critical">{errors.name.message}</p> : null}
        </div>
        <div>
          <Label htmlFor="budget-member">Member scope</Label>
          <select
            id="budget-member"
            className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
            {...register("member_id")}
          >
            <option value="">Whole household</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="budget-period">Period type</Label>
          <select
            id="budget-period"
            className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
            {...register("period_type")}
          >
            {PERIOD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        {(periodType === "weekly" || periodType === "custom") && (
          <>
            <div>
              <Label htmlFor="budget-start">Start date</Label>
              <Input id="budget-start" type="date" className="mt-1" {...register("start_date")} />
              {errors.start_date ? (
                <p className="mt-1 text-xs text-critical">{errors.start_date.message}</p>
              ) : null}
            </div>
            <div>
              <Label htmlFor="budget-end">End date</Label>
              <Input id="budget-end" type="date" className="mt-1" {...register("end_date")} />
              {errors.end_date ? <p className="mt-1 text-xs text-critical">{errors.end_date.message}</p> : null}
            </div>
          </>
        )}
      </div>
      <div className="space-y-3">
        {fields.map((field, index) => (
          <div key={field.id} className="grid gap-3 md:grid-cols-[1fr_160px_auto]">
            <select
              className="border border-line bg-input px-3 py-2 text-sm"
              {...register(`categories.${index}.category_id`)}
            >
              <option value="">Category</option>
              {usable.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <Input
              className="tabular"
              placeholder="250000.00"
              {...register(`categories.${index}.allocated_amount`)}
            />
            <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)} disabled={fields.length === 1}>
              Remove
            </Button>
            {errors.categories?.[index]?.category_id ? (
              <p className="text-xs text-critical md:col-span-3">
                {errors.categories[index]?.category_id?.message}
              </p>
            ) : null}
            {errors.categories?.[index]?.allocated_amount ? (
              <p className="text-xs text-critical md:col-span-3">
                {errors.categories[index]?.allocated_amount?.message}
              </p>
            ) : null}
          </div>
        ))}
      </div>
      {errors.categories?.root ? (
        <p className="text-xs text-critical">{errors.categories.root.message}</p>
      ) : null}
      <div className="flex items-center gap-4">
        <Button
          type="button"
          variant="link"
          className="h-auto p-0"
          onClick={() => append({ category_id: "", allocated_amount: "" })}
        >
          Add category
        </Button>
        <Button type="submit" disabled={pending}>
          {pending ? "Saving..." : "Create budget"}
        </Button>
      </div>
    </form>
  );
}
