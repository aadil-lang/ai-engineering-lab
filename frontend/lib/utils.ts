import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

export function getStatusColor(status: string) {
  switch (status) {
    case "PASSED":
      return {
        badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        dot: "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]",
        border: "border-emerald-500/40",
      };
    case "FAILED":
    case "ERROR":
      return {
        badge: "bg-rose-500/10 text-rose-400 border-rose-500/30",
        dot: "bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.6)]",
        border: "border-rose-500/40",
      };
    case "RUNNING":
      return {
        badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30 animate-pulse",
        dot: "bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]",
        border: "border-cyan-500/40",
      };
    case "QUEUED":
    case "PENDING":
      return {
        badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        dot: "bg-amber-400",
        border: "border-amber-500/40",
      };
    default:
      return {
        badge: "bg-slate-500/10 text-slate-400 border-slate-500/30",
        dot: "bg-slate-400",
        border: "border-slate-700",
      };
  }
}
