"use client"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useSession } from "@/lib/api/hooks"
export default function RootPage() { const { data, isPending } = useSession(); const router = useRouter(); useEffect(() => { if (!isPending) router.replace(data ? "/dashboard" : "/login") }, [data, isPending, router]); return null }
