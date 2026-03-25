import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline";
}

const variantClasses = {
  default: "bg-zinc-900 text-zinc-50 border-transparent",
  secondary: "bg-zinc-800 text-zinc-50 border-transparent",
  destructive: "bg-red-600 text-zinc-50 border-transparent",
  outline: "text-zinc-50 border border-zinc-600",
};

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
