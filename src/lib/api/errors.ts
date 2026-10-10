// Typed API error class. Carries HTTP status for 401 interception.

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly statusText: string,
    message: string,
    public readonly details?: { field?: string; message?: string }[]
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError
}
