import * as React from "react"
import { motion, type HTMLMotionProps } from "framer-motion"
import { cn } from "@/lib/utils"

export interface ButtonProps extends HTMLMotionProps<"button"> {
  variant?: "default" | "secondary" | "outline" | "destructive" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer"
    
    const variants = {
      default: "bg-indigo-600 text-white shadow-sm hover:bg-indigo-700 active:bg-indigo-800 shadow-indigo-100 hover:shadow-indigo-200",
      secondary: "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 active:bg-indigo-200 border border-indigo-100",
      outline: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-sm",
      destructive: "bg-rose-50 text-rose-600 border border-rose-200 hover:bg-rose-100 active:bg-rose-200",
      ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
      link: "text-indigo-600 underline-offset-4 hover:underline",
    }

    const sizes = {
      default: "h-9.5 px-4 text-xs tracking-tight",
      sm: "h-8 px-3 text-[11px] rounded-lg",
      lg: "h-11 px-5 text-sm rounded-xl",
      icon: "h-9 w-9 p-0 rounded-xl",
    }

    return (
      <motion.button
        ref={ref}
        whileTap={{ scale: 0.97 }}
        whileHover={{ scale: 1.01 }}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"
