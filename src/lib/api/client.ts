import { ApiError } from "./errors"

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown
  params?: Record<string, string | number | boolean | undefined | null>
  timeout?: number
  responseType?: "json" | "blob"
}

let memoryToken: string | null = null

export const setAuthToken = (token: string | null, user?: any) => {
  memoryToken = token
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("rsa_jwt_token", token)
      localStorage.setItem("rsa-auth", "true")
      sessionStorage.setItem("rsa-auth", "true")
      document.cookie = `rsa_jwt_token=${token}; path=/; max-age=86400; SameSite=Lax`
      document.cookie = `token=${token}; path=/; max-age=86400; SameSite=Lax`
      if (user) {
        localStorage.setItem("rsa-profile", JSON.stringify({ name: user.name, email: user.email }))
      }
    } else {
      localStorage.removeItem("rsa_jwt_token")
      localStorage.removeItem("rsa-auth")
      localStorage.removeItem("rsa-profile")
      sessionStorage.removeItem("rsa-auth")
      document.cookie = "rsa_jwt_token=; path=/; max-age=0"
      document.cookie = "token=; path=/; max-age=0"
    }
  }
}

export const getAuthToken = (): string | null => {
  if (memoryToken) return memoryToken
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("rsa_jwt_token")
    if (saved) {
      memoryToken = saved
      return saved
    }
    const match = document.cookie.match(/(?:^|;\s*)(?:rsa_jwt_token|token)=([^;]*)/)
    if (match) {
      memoryToken = match[1]
      return match[1]
    }
  }
  return null
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api"
  const { body, params, timeout = 15_000, responseType = "json", ...rest } = options

  let url = `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`
  if (params) {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        // Map frontend page_size to backend pageSize
        const mappedKey = key === "page_size" ? "pageSize" : key
        query.append(mappedKey, String(val))
      }
    })
    const qs = query.toString()
    if (qs) url += `?${qs}`
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(rest.headers as Record<string, string> ?? {}),
  }

  const token = getAuthToken()
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const controller = new AbortController()
  const timerId = setTimeout(() => controller.abort(), timeout)

  let response: Response
  try {
    response = await fetch(url, {
      ...rest,
      signal: controller.signal,
      headers,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    })
  } catch (err) {
    clearTimeout(timerId)
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(408, "Request Timeout", "The request timed out.")
    }
    throw new ApiError(0, "Network Error", "Could not connect to backend server.")
  }

  clearTimeout(timerId)

  if (!response.ok) {
    let message = response.statusText
    try {
      const errBody = await response.json()
      if (errBody?.detail) {
        if (Array.isArray(errBody.detail)) {
          message = errBody.detail.map((e: any) => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg || JSON.stringify(e)}`).join(", ")
        } else if (typeof errBody.detail === "object") {
          message = JSON.stringify(errBody.detail)
        } else {
          message = String(errBody.detail)
        }
      } else if (errBody?.error?.message) {
        message = String(errBody.error.message)
      } else if (errBody?.message) {
        message = String(errBody.message)
      }
    } catch {
      // ignore
    }
    throw new ApiError(response.status, response.statusText, message)
  }

  if (response.status === 204) return undefined as T

  if (responseType === "blob") {
    return (await response.blob()) as unknown as T
  }

  const json = await response.json()

  // Auto-unwrap FastAPI response envelopes
  if (json && typeof json === "object" && "status" in json && "data" in json) {
    if ("pagination" in json) {
      return {
        data: json.data,
        items: json.data,
        pagination: json.pagination,
        total: json.pagination?.totalItems ?? json.data?.length ?? 0,
      } as unknown as T
    }
    return json.data as T
  }

  return json as T
}

export const apiClient = {
  get: <T>(path: string, options?: Omit<RequestOptions, "method">) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: Omit<RequestOptions, "method">) =>
    request<T>(path, { ...options, method: "DELETE" }),
  getBlob: async (path: string, options?: Omit<RequestOptions, "method">) =>
    request<Blob>(path, { ...options, method: "GET", responseType: "blob" }),
}
