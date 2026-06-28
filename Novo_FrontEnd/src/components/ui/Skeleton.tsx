import React from "react";
import { cn } from "../../lib/utils";

interface SkeletonProps extends React.ComponentProps<"div"> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-gray-200/50 dark:bg-gray-800/50", className)}
      {...props}
    />
  );
}
