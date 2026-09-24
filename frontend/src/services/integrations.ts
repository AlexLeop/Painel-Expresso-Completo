import { authFetch } from "../lib/api";

export interface Connector {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  icon_url: string | null;
  auth_type: string;
  config_schema: Record<string, any>;
  capabilities: string[];
  status: "active" | "beta" | "deprecated" | "disabled";
  documentation_url: string | null;
  version: string;
}

export interface StoreIntegration {
  id: string;
  store_id: string;
  store_name: string;
  connector_slug: string;
  connector_name: string;
  connector_icon_url: string | null;
  auth_type: string;
  active: boolean;
  auto_create_order: boolean;
  webhook_url: string;
  webhook_secret: string | null;
  config: Record<string, any>;
  last_webhook_at: string | null;
  error_count: number;
  error_message: string | null;
  created_at: string;
}

export interface WebhookLogItem {
  id: string;
  connector_slug: string;
  status: "received" | "processed" | "failed" | "duplicate" | "rejected";
  order_id: string | null;
  error_detail: string | null;
  processing_ms: number | null;
  created_at: string;
}

export interface WebhookLogsResponse {
  total: number;
  logs: WebhookLogItem[];
}

export interface StoreOption {
  id: string;
  name: string;
}

export async function fetchConnectors(): Promise<Connector[]> {
  try {
    const res = await authFetch("/api/v1/integration/connectors");
    if (!res.ok) throw new Error("Falha ao carregar conectores.");
    return await res.json();
  } catch (err) {
    console.error("fetchConnectors error:", err);
    return [];
  }
}

export async function fetchStoreIntegrations(): Promise<StoreIntegration[]> {
  try {
    const res = await authFetch("/api/v1/integration/");
    if (!res.ok) throw new Error("Falha ao carregar integrações.");
    return await res.json();
  } catch (err) {
    console.error("fetchStoreIntegrations error:", err);
    return [];
  }
}

export async function fetchOperatorStores(): Promise<StoreOption[]> {
  try {
    const res = await authFetch("/api/v1/integration/stores");
    if (!res.ok) throw new Error("Falha ao carregar lojas.");
    return await res.json();
  } catch (err) {
    console.error("fetchOperatorStores error:", err);
    return [];
  }
}

export async function createStoreIntegration(data: {
  store_id: string;
  connector_slug: string;
  config?: Record<string, any>;
  auto_create_order?: boolean;
}): Promise<StoreIntegration> {
  const res = await authFetch("/api/v1/integration/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Erro ao criar integração." }));
    throw new Error(err.error || "Erro ao criar integração.");
  }
  return await res.json();
}

export async function updateStoreIntegration(
  id: string,
  data: {
    active?: boolean;
    auto_create_order?: boolean;
    config?: Record<string, any>;
    regenerate_secret?: boolean;
  }
): Promise<StoreIntegration> {
  const res = await authFetch(`/api/v1/integration/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Erro ao atualizar integração." }));
    throw new Error(err.error || "Erro ao atualizar integração.");
  }
  return await res.json();
}

export async function deleteStoreIntegration(id: string): Promise<boolean> {
  const res = await authFetch(`/api/v1/integration/${id}`, {
    method: "DELETE",
  });
  return res.ok;
}

export async function fetchIntegrationLogs(
  id: string,
  params?: { status?: string; limit?: number; offset?: number }
): Promise<WebhookLogsResponse> {
  try {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await authFetch(`/api/v1/integration/${id}/logs?${query.toString()}`);
    if (!res.ok) throw new Error("Falha ao buscar logs de webhook.");
    return await res.json();
  } catch (err) {
    console.error("fetchIntegrationLogs error:", err);
    return { total: 0, logs: [] };
  }
}
