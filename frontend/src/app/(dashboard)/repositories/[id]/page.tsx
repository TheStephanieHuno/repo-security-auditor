"use client"

import { Suspense } from "react"
import { RepositoryDetail } from "@/app/repositories"

export default function RepositoryDetailPage() {
  return (
    <Suspense fallback={null}>
      <RepositoryDetail />
    </Suspense>
  )
}
