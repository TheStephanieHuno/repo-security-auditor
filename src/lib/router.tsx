"use client"

import React, { useMemo, useCallback } from "react"
import NextLink, { type LinkProps as NextLinkProps } from "next/link"
import {
  useRouter as useNextRouter,
  usePathname as useNextPathname,
  useSearchParams as useNextSearchParams,
  useParams as useNextParams,
} from "next/navigation"

export interface LinkProps
  extends Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  to?: string
  href?: string
  replace?: boolean
}

export function Link({ to, href, children, ...props }: LinkProps) {
  const target = to || href || "#"
  return (
    <NextLink href={target} {...props}>
      {children}
    </NextLink>
  )
}

export interface NavLinkProps
  extends Omit<
    React.AnchorHTMLAttributes<HTMLAnchorElement>,
    "href" | "className" | "children"
  > {
  to?: string
  href?: string
  className?: string | ((props: { isActive: boolean }) => string)
  children?:
    | React.ReactNode
    | ((props: { isActive: boolean }) => React.ReactNode)
}

export function NavLink({
  to,
  href,
  className,
  children,
  ...props
}: NavLinkProps) {
  const pathname = useNextPathname()
  const target = to || href || "#"
  const isActive =
    pathname === target ||
    (target !== "/" && target !== "/dashboard" && pathname?.startsWith(target))

  const computedClassName =
    typeof className === "function" ? className({ isActive: !!isActive }) : className
  const computedChildren =
    typeof children === "function" ? children({ isActive: !!isActive }) : children

  return (
    <NextLink href={target} className={computedClassName} {...props}>
      {computedChildren}
    </NextLink>
  )
}

export function useNavigate() {
  const router = useNextRouter()
  return useCallback(
    (to: string | number, options?: { replace?: boolean }) => {
      if (typeof to === "number") {
        if (to < 0) router.back()
        else router.forward()
        return
      }
      if (options?.replace) {
        router.replace(to)
      } else {
        router.push(to)
      }
    },
    [router],
  )
}

export function useLocation() {
  const pathname = useNextPathname()
  const searchParams = useNextSearchParams()
  const search = searchParams ? `?${searchParams.toString()}` : ""
  return {
    pathname: pathname || "/",
    search,
    hash: typeof window !== "undefined" ? window.location.hash : "",
    state: null,
    key: "default",
  }
}

export function useParams<
  T extends Record<string, string | string[] | undefined> = Record<string, string>,
>(): T {
  const params = useNextParams()
  return (params || {}) as T
}

export function useSearchParams(): [
  URLSearchParams,
  (
    nextInit:
      | Record<string, string | number | boolean | null | undefined>
      | URLSearchParams,
  ) => void,
] {
  const nextSearchParams = useNextSearchParams()
  const router = useNextRouter()
  const pathname = useNextPathname()

  const params = useMemo(() => {
    return new URLSearchParams(
      nextSearchParams ? nextSearchParams.toString() : "",
    )
  }, [nextSearchParams])

  const setParams = useCallback(
    (
      nextInit:
        | Record<string, string | number | boolean | null | undefined>
        | URLSearchParams,
    ) => {
      const sp = new URLSearchParams()
      if (nextInit instanceof URLSearchParams) {
        nextInit.forEach((v, k) => sp.set(k, v))
      } else {
        Object.entries(nextInit).forEach(([k, v]) => {
          if (v !== undefined && v !== null && v !== "") {
            sp.set(k, String(v))
          }
        })
      }
      const qs = sp.toString()
      router.replace(qs ? `${pathname}?${qs}` : pathname)
    },
    [pathname, router],
  )

  return [params, setParams]
}

export function Navigate({ to, replace }: { to: string; replace?: boolean }) {
  const router = useNextRouter()
  React.useEffect(() => {
    if (replace) {
      router.replace(to)
    } else {
      router.push(to)
    }
  }, [to, replace, router])
  return null
}

export function Outlet() {
  return null
}
