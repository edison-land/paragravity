import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "success" | "destructive" | "outline" | "iris"
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-slate-100 text-slate-800 border-slate-200",
    secondary: "bg-indigo-50 text-indigo-700 border-indigo-200/70",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    destructive: "bg-rose-50 text-rose-700 border-rose-200",
    outline: "text-slate-600 border-slate-200",
    iris: "bg-indigo-50/80 text-indigo-700 border-indigo-200 font-semibold shadow-xs",
  }

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors",
        variants[variant],
        className
      )}
      {...props}
    />
  )
}
