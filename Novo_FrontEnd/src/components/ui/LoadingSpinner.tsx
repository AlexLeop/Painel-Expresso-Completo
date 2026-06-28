import React from "react";
import { cn } from "../../lib/utils";
import { Loader2 } from "lucide-react";
import { motion } from "framer-motion";

interface LoadingSpinnerProps {
  className?: string;
  size?: number;
  text?: string;
}

export function LoadingSpinner({ className, size = 20, text }: LoadingSpinnerProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2", className)}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
      >
        <Loader2 size={size} className="text-zinc-500" />
      </motion.div>
      {text && <span className="text-sm text-zinc-500 font-medium">{text}</span>}
    </div>
  );
}
