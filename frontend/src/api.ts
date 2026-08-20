import type {
  CSVImportResult,
  ProductList,
  SalesBoostProduct,
  TaskAccepted,
  TaskState,
} from "./types";

const TOKEN_KEY = "lemon-brothers-token";

export const authStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = authStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  if (response.status === 401) authStore.clear();
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  async login(username: string, password: string): Promise<void> {
    const body = new URLSearchParams({ username, password });
    const response = await request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    authStore.set(response.access_token);
  },
  products: () => request<ProductList>("/api/products"),
  runAmazon: () => request<TaskAccepted>("/api/scraping/amazon", { method: "POST" }),
  runTrends: () => request<TaskAccepted>("/api/trends/collect", { method: "POST" }),
  task: (id: string) => request<TaskState>(`/api/tasks/${id}`),
  salesBoost: () => request<SalesBoostProduct[]>("/api/sales-boost"),
  addSalesBoost: (payload: { title: string; category: string; keywords: string[] }) =>
    request<SalesBoostProduct>("/api/sales-boost", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  importSalesBoost: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<CSVImportResult>("/api/sales-boost/import", { method: "POST", body });
  },
};
