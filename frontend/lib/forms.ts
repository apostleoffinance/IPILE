import { z } from "zod";

export const moneyString = z
  .string()
  .trim()
  .regex(/^\d+(\.\d{1,2})?$/, "Enter an amount like 150000.00");

export const transactionSchema = z
  .object({
    type: z.enum(["expense", "income", "transfer", "giving", "refund"]),
    amount: moneyString,
    account_id: z.string().min(1, "Choose an account"),
    counterparty_account_id: z.string().optional(),
    category_id: z.string().optional(),
    member_id: z.string().optional(),
    date: z.string().min(1, "Date is required"),
    description: z.string().optional(),
  })
  .superRefine((value, ctx) => {
    if (value.type === "transfer" && !value.counterparty_account_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Choose a destination account",
        path: ["counterparty_account_id"],
      });
    }
  });

export type TransactionFormValues = z.infer<typeof transactionSchema>;

export const budgetSchema = z
  .object({
    name: z.string().trim().min(1, "Name is required"),
    period_type: z.enum(["monthly", "weekly", "quarterly", "annual", "custom"]),
    start_date: z.string().optional(),
    end_date: z.string().optional(),
    member_id: z.string().optional(),
    categories: z
      .array(
        z.object({
          category_id: z.string().min(1, "Category required"),
          allocated_amount: moneyString,
        }),
      )
      .min(1, "Add at least one category"),
  })
  .superRefine((value, ctx) => {
    if (value.period_type === "custom") {
      if (!value.start_date) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Start date required", path: ["start_date"] });
      }
      if (!value.end_date) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "End date required", path: ["end_date"] });
      }
    }
  });

export type BudgetFormValues = z.infer<typeof budgetSchema>;

export const obligationSchema = z.object({
  name: z.string().trim().min(1, "Name is required"),
  amount: moneyString,
  frequency: z.enum(["weekly", "monthly", "quarterly", "annual", "one_time"]),
  next_due_date: z.string().min(1, "Due date is required"),
  sinking_fund: z.boolean(),
});

export type ObligationFormValues = z.infer<typeof obligationSchema>;

export const recurringSchema = z
  .object({
    type: z.enum(["expense", "income", "transfer", "giving"]),
    amount: moneyString,
    account_id: z.string().min(1, "Choose an account"),
    frequency: z.enum(["weekly", "biweekly", "monthly", "quarterly", "annual"]),
    next_date: z.string().min(1, "Next date is required"),
    category_id: z.string().optional(),
    member_id: z.string().optional(),
    counterparty_account_id: z.string().optional(),
    description: z.string().optional(),
  })
  .superRefine((value, ctx) => {
    if (value.type === "transfer" && !value.counterparty_account_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Choose a destination account",
        path: ["counterparty_account_id"],
      });
    }
  });

export type RecurringFormValues = z.infer<typeof recurringSchema>;
