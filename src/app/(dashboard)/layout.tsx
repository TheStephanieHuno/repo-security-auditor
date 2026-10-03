"use client"

import { Shell } from "@/app/shell"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <Shell>{children}</Shell>
}
