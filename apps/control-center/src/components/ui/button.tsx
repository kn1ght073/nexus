import React from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "destructive" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  disabled,
  children,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-50 cursor-pointer rounded-md";

  const variants = {
    primary: "bg-primary text-primary-foreground hover:bg-sky-400 font-semibold shadow-sm",
    secondary: "bg-secondary text-secondary-foreground hover:bg-slate-700/60 border border-white/10",
    danger: "bg-rose-500/15 text-rose-400 border border-rose-500/30 hover:bg-rose-500/25",
    destructive: "bg-rose-500/15 text-rose-400 border border-rose-500/30 hover:bg-rose-500/25",
    outline: "bg-transparent text-slate-300 border border-white/10 hover:bg-white/5 hover:text-white",
    ghost: "bg-transparent text-muted-foreground hover:bg-white/5 hover:text-foreground",
  };

  const sizes = {
    sm: "h-8 px-3 text-xs gap-1.5",
    md: "h-9 px-4 text-sm gap-2",
    lg: "h-11 px-6 text-base gap-2.5",
  };

  return (
    <button className={cn(base, variants[variant], sizes[size], className)} disabled={disabled} {...props}>
      {children}
    </button>
  );
}
