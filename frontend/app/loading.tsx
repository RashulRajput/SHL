import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <main className="min-h-screen p-6">
      <Skeleton className="mx-auto h-[82vh] max-w-7xl rounded-lg" />
    </main>
  );
}

