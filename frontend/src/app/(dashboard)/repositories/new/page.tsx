"use client"

import { Suspense } from "react"
import { AddRepository } from "@/app/repositories"

export default function NewRepositoryPage() {
  return (
    <Suspense fallback={null}>
      <AddRepository />
    </Suspense>
  )
}
