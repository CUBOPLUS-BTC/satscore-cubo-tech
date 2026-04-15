import { auth } from '$lib/stores/auth.svelte';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const authHeader = auth.getAuthHeader();
  if (authHeader) headers['Authorization'] = authHeader;

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }

  return res.json();
}

export const api = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body: unknown) =>
    request<T>(url, { method: 'POST', body: JSON.stringify(body) }),
};
