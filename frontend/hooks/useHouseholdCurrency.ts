"use client";

import { useEffect, useState } from "react";
import { getCurrentHousehold } from "@/lib/api";

export function useHouseholdCurrency() {
  const [currency, setCurrency] = useState<string>();

  useEffect(() => {
    getCurrentHousehold()
      .then((household) => setCurrency(household.base_currency))
      .catch(() => undefined);
  }, []);

  return currency;
}