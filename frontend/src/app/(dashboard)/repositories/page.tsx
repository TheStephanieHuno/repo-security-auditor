"use client"

import { Suspense } from "react"
import { RepositoryList } from "@/app/repositories"

export default function RepositoriesPage() {
  return (
    <Suspense fallback={null}>
      <RepositoryList />
    </Suspense>
  )
}
