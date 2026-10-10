import { Skeleton } from "@/components/ui/skeleton"

export default function RouteLoading() {
  return (
    <div
      role="status"
      aria-label="Loading application"
      className="min-h-screen bg-canvas p-6 md:p-10"
    >
      <div className="mx-auto max-w-screen-xl space-y-6">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-80 max-w-full" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-80" />
        <span className="sr-only">Loading application…</span>
      </div>
    </div>
  )
}
