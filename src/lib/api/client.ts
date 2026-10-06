// Native fetch wrapper. No axios.
// Injects base URL, auth credentials, and handles errors uniformly.
// Intercepts 401s and redirects to /login preserving return URL.

import { ApiError } from "./errors"

const SKIP_AUTH_REDIRECT = ["/api/auth/login", "/api/auth/register", "/api/users/me"]

let inMemoryToken: string | null = null

export function setAuthToken(token: string | null) {
  inMemoryToken = token
}

export function getAuthToken(): string | null {
  return inMemoryToken
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown
  timeout?: number
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""
  const { body, timeout = 15_000, ...rest } = options

  const controller = new AbortController()
  const timerId = setTimeout(() => controller.abort(), timeout)

  const token = getAuthToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(rest.headers as Record<string, string> ?? {}),
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  let response: Response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...rest,
      credentials: "omit", // Using Authorization header instead of cookies
      signal: controller.signal,
      headers,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    })
  } catch (err) {
    clearTimeout(timerId)
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(408, "Request Timeout", "The request timed out.")
    }
    throw new ApiError(0, "Network Error", "A network error occurred.")
  }

  clearTimeout(timerId)

  if (!response.ok) {
    // Intercept 401: redirect to /login unless already there or checking session.
    if (
      response.status === 401 &&
      typeof window !== "undefined" &&
      !SKIP_AUTH_REDIRECT.some((p) => path.startsWith(p)) &&
      !window.location.pathname.startsWith("/login") &&
      !window.location.pathname.startsWith("/signup")
    ) {
      const returnUrl = encodeURIComponent(
        window.location.pathname + window.location.search,
      )
      window.location.href = `/login?redirect=${returnUrl}`
    }

    let message = response.statusText
    let details: any[] | undefined
    try {
      const errBody = await response.json()
      if (errBody?.error?.message) {
        message = errBody.error.message
        details = errBody.error.details
      } else {
        message = errBody?.detail ?? errBody?.message ?? message
      }
    } catch {
      // ignore parse errors — use statusText
    }
    throw new ApiError(response.status, response.statusText, message, details)
  }

  // 204 No Content — return undefined cast to T
  if (response.status === 204) return undefined as T

  const parsed = await response.json()
  
  if (parsed && typeof parsed === "object" && "status" in parsed && parsed.status === "success") {
    if ("pagination" in parsed) {
       return {
         items: parsed.data,
         total: parsed.pagination.totalItems,
         page: parsed.pagination.page,
         page_size: parsed.pagination.pageSize
       } as unknown as T
    }
    return parsed.data as T
  }

  return parsed as T
}

export const apiClient = {
  get: <T>(path: string, options?: Omit<RequestOptions, "method">) =>
    request<T>(path, { ...options, method: "GET" }),

  post: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, "method" | "body">,
  ) => request<T>(path, { ...options, method: "POST", body }),

  put: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, "method" | "body">,
  ) => request<T>(path, { ...options, method: "PUT", body }),

  patch: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, "method" | "body">,
  ) => request<T>(path, { ...options, method: "PATCH", body }),

  delete: <T>(path: string, options?: Omit<RequestOptions, "method">) =>
    request<T>(path, { ...options, method: "DELETE" }),

  getBlob: async (path: string, options?: Omit<RequestOptions, "method">) => {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""
    const token = getAuthToken()
    const headers: Record<string, string> = { ...(options?.headers as Record<string, string> ?? {}) }
    if (token) headers["Authorization"] = `Bearer ${token}`

    const response = await fetch(`${baseUrl}${path}`, { method: "GET", credentials: "omit", headers })
    if (!response.ok) throw new ApiError(response.status, response.statusText, "Could not download the PDF.")
    return response.blob()
  },
}
