import { createContext, useContext } from "react";
import type { GmailFetchParams } from "./types";

/** Things any screen can trigger: pick a CSV, start a run, reopen past work. */
export interface Actions {
  choose: () => void;
  start: (source: File | "sample") => Promise<void>;
  /** Pull emails from Gmail by subject keywords and dates, then run them. */
  startGmail: (params: GmailFetchParams) => Promise<void>;
  openPast: (id: string) => Promise<void>;
}

export const ActionsCtx = createContext<Actions | null>(null);

export function useActions(): Actions {
  const value = useContext(ActionsCtx);
  if (!value) throw new Error("useActions must be used inside <Shell>");
  return value;
}
