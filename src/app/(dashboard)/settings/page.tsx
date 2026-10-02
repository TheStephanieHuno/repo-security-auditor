"use client"

import { Suspense } from "react"
import { Settings } from "@/app/settings"

export default function SettingsPage() {
  return (
    <Suspense fallback={null}>
      <Settings />
    </Suspense>
  )
}
