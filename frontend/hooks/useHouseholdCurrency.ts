"use client";

import { useEffect, useState } from "react";
import { getCurrentHousehold } from "@/lib/api";

let cachedCurrency: string | undefined;
let currencyRequest: Promise<string> | undefined;

export function useHouseholdCurrency() {
  const [currency, setCurrency] = useState<string | undefined>(cachedCurrency);

  useEffect(() => {
    let active = true;
    const load = () => {
      if (!currencyRequest) {
        currencyRequest = getCurrentHousehold()
          .then((household) => {
            cachedCurrency = household.reporting_currency || household.base_currency;
            return cachedCurrency;
          })
          .catch((error) => {
            currencyRequest = undefined;
            throw error;
          });
      }
      currencyRequest.then((value) => {
        if (active) setCurrency(value);
      }).catch(() => undefined);
    };
    load();
    const handleHouseholdChange = () => {
      cachedCurrency = undefined;
      currencyRequest = undefined;
      setCurrency(undefined);
      load();
    };
    window.addEventListener("ipile:household-changed", handleHouseholdChange);
    return () => {
      active = false;
      window.removeEventListener("ipile:household-changed", handleHouseholdChange);
    };
  }, []);

  return currency;
}
