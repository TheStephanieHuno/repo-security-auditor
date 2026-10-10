"use client"

import { Shell } from "@/app/shell"
import { useEffect } from "react"
import { usePathname } from "next/navigation"
import { useRouter } from "next/navigation"
import { Skeleton } from "@/components/ui/skeleton"
import { useSession } from "@/lib/api/hooks"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { data, isPending } = useSession()
  const router = useRouter()
  const pathname = usePathname()
  useEffect(() => { if (!isPending && !data) router.replace(`/login?redirect=${encodeURIComponent(pathname || "/dashboard")}`) }, [data, isPending, pathname, router])
  if (isPending || !data) return <div className="space-y-6 p-8"><Skeleton className="h-8 w-48" /><Skeleton className="h-32 w-full" /></div>
  return <Shell>{children}</Shell>
}
