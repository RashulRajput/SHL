"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Recommendation } from "@/lib/types";

export function AssessmentCard({ item, index }: { item: Recommendation; index: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: index * 0.035 }}
      className="group grid min-h-32 gap-4 rounded-lg border bg-card/88 p-4 shadow-sm backdrop-blur transition duration-200 hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-glow"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <Badge variant="success">Catalog verified</Badge>
          <h3 className="text-sm font-semibold leading-5">{item.name}</h3>
        </div>
        <CheckCircle2 className="mt-1 size-4 text-success" aria-hidden="true" />
      </div>
      <div className="flex items-center justify-between gap-3">
        <Badge variant="outline" className="font-mono">
          {item.test_type}
        </Badge>
        <Button asChild variant="ghost" size="sm" className="px-2">
          <a href={item.url} target="_blank" rel="noreferrer">
            SHL <ArrowUpRight />
          </a>
        </Button>
      </div>
    </motion.article>
  );
}

