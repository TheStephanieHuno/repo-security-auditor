"use client"

import { Suspense } from "react"
import { Documentation } from "@/app/settings"

export default function HelpPage() {
  return (
    <Suspense fallback={null}>
      <Documentation />
    </Suspense>
  )
}
