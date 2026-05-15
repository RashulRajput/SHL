import { BarChart3, Database, Gauge, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Recommendation } from "@/lib/types";

const typeLabels: Record<string, string> = {
  A: "Ability",
  B: "SJT",
  C: "Competency",
  D: "360",
  E: "Exercise",
  K: "Skills",
  P: "Personality",
  S: "Simulation"
};

export function InsightPanel({ recommendations }: { recommendations: Recommendation[] }) {
  const typeCounts = recommendations.reduce<Record<string, number>>((acc, item) => {
    item.test_type.split(/\s+/).forEach((code) => {
      if (!code) return;
      acc[code] = (acc[code] ?? 0) + 1;
    });
    return acc;
  }, {});

  return (
    <aside className="hidden min-h-0 w-80 shrink-0 border-l bg-card/58 backdrop-blur-xl lg:block">
      <div className="flex h-full flex-col gap-6 p-5">
        <div className="space-y-2">
          <Badge variant="secondary">Recruiter workspace</Badge>
          <h2 className="text-lg font-semibold">Assessment Intel</h2>
          <p className="text-sm leading-6 text-muted-foreground">
            {recommendations.length
              ? `${recommendations.length} catalog-backed options in the current shortlist.`
              : "Shortlist metrics appear once the assistant has enough hiring context."}
          </p>
        </div>

        <div className="grid gap-3">
          <Metric icon={Database} label="Catalog scope" value="Individual tests" />
          <Metric icon={ShieldCheck} label="URL guardrail" value="SHL only" />
          <Metric icon={Gauge} label="Target latency" value="< 30s" />
          <Metric icon={BarChart3} label="Shortlist cap" value="10 max" />
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Coverage Mix</h3>
          <div className="grid gap-2">
            {Object.keys(typeLabels).map((code) => (
              <div key={code} className="grid grid-cols-[86px_1fr_28px] items-center gap-2 text-xs">
                <span className="text-muted-foreground">{typeLabels[code]}</span>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-success"
                    style={{ width: `${Math.min(100, (typeCounts[code] ?? 0) * 18)}%` }}
                  />
                </div>
                <span className="text-right font-mono">{typeCounts[code] ?? 0}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function Metric({
  icon: Icon,
  label,
  value
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-background/55 p-3">
      <div className="flex size-9 items-center justify-center rounded-md bg-secondary">
        <Icon className="size-4 text-success" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}

