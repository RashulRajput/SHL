"use client";

import { motion } from "framer-motion";
import { Bot, UserRound } from "lucide-react";

import { cn } from "@/lib/utils";

export function MessageBubble({
  role,
  content
}: {
  role: "user" | "assistant";
  content: string;
}) {
  const isUser = role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className={cn("flex gap-3", isUser && "justify-end")}
    >
      {!isUser && (
        <div className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-md border bg-secondary">
          <Bot className="size-4 text-success" aria-hidden="true" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[82%] rounded-lg border px-4 py-3 text-sm leading-6 shadow-sm",
          isUser
            ? "border-primary/20 bg-primary text-primary-foreground"
            : "border-border bg-card/88 backdrop-blur"
        )}
      >
        {content}
      </div>
      {isUser && (
        <div className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-md border bg-secondary">
          <UserRound className="size-4" aria-hidden="true" />
        </div>
      )}
    </motion.div>
  );
}

