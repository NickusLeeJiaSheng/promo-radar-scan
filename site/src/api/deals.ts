import { createServerFn } from "@tanstack/react-start";

import type { DbDeal } from "./deals.types";

export const fetchDealsFromDb = createServerFn({ method: "GET" }).handler(
  async (): Promise<DbDeal[]> => {
    const { queryAllDeals } = await import("./deals.server");
    return queryAllDeals();
  },
);
