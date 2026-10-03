"use client"

import { Suspense } from "react"
import { WorkspaceFindings } from "@/app/findings"

export default function FindingsPage() {
  return (
    <Suspense fallback={null}>
      <WorkspaceFindings />
    </Suspense>
  )
}
