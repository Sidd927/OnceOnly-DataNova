export class ApiError extends Error {
  status: number;
  detail: any;
  constructor(status: number, message: string, detail: any) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Cannot reach the OnceOnly API. Is the backend running on port 8000?", null);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const msg = body?.error ?? (typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`);
    throw new ApiError(res.status, msg, body?.detail ?? body);
  }
  return body as T;
}

export const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const fmt = (n: number | null | undefined): string =>
  n == null ? "—" : n.toLocaleString("en-US");

export const short = (h: string | null | undefined, n = 10): string =>
  !h ? "—" : h.length > n * 2 ? `${h.slice(0, n)}…${h.slice(-6)}` : h;

export const pct = (x: number | null | undefined, decimals = 1): string =>
  x == null ? "—" : `${(x * 100).toFixed(decimals)}%`;
