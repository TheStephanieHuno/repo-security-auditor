"use client"

import { Suspense } from "react"
import { RepositoryDetail } from "@/app/repositories"

export default function RepositoryScanPage() {
  return (
    <Suspense fallback={null}>
      <RepositoryDetail start />
    </Suspense>
  )
}
