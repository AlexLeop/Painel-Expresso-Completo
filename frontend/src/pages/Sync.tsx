import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../lib/api";
import { StoreIntegration, updateStoreIntegration } from "../services/integrations";
import { ConfirmModal } from "../components/ConfirmModal";

interface SyncStatus {
  queried_at: string;
  window_minutes: number;
  metrics: Record<string, number>;
  last_event_at: string | null;
}

const eventLabels: Record<string, string> = {
  received: "Recebidos", processed: "Processados", failed: "Com falha",
  duplicate: "Duplicados", rejected: "Rejeitados",
};

export function Sync() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [integrations, setIntegrations] = useState<StoreIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [target, setTarget] = useState<{ integration: StoreIntegration; revoke: boolean } | null>(null);
  const [secret, setSecret] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [metrics, connectors] = await Promise.all([
        authFetch("/api/v1/integration/sync-status"),
        authFetch("/api/v1/integration/"),
      ]);
      if (!metrics.ok || !connectors.ok) throw new Error("Monitoramento temporariamente indisponível.");
      setStatus(await metrics.json());
      setIntegrations(await connectors.json());
    } catch (cause) {
      setStatus(null);
      setIntegrations([]);
      setError(cause instanceof Error ? cause.message : "Não foi possível consultar os serviços.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function updateCredential() {
    if (!target) return;
    const updated = await updateStoreIntegration(target.integration.id, {
      regenerate_secret: true,
      ...(target.revoke ? { active: false } : {}),
    });
    setSecret(target.revoke ? "" : updated.webhook_secret || "");
    setTarget(null);
    await load();
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Central de Sincronização</h1>
          <p className="text-sm text-zinc-600">Eventos observados e credenciais de integração.</p>
        </div>
        <button type="button" disabled={loading} onClick={() => void load()} className="rounded-lg border border-zinc-200 px-3 py-2 text-sm disabled:opacity-50">
          {loading ? "Consultando…" : "Atualizar"}
        </button>
      </header>
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-rose-800">{error}</p>}
      {status && !error && (
        <section aria-labelledby="sync-events" className="rounded-xl border border-zinc-200 bg-white p-4">
          <h2 id="sync-events" className="font-semibold">Webhooks dos últimos {status.window_minutes} minutos</h2>
          <p className="mt-1 text-sm text-zinc-600">
            Consulta em {new Date(status.queried_at).toLocaleString("pt-BR")} · Último evento {status.last_event_at ? new Date(status.last_event_at).toLocaleString("pt-BR") : "ainda não registrado"}.
          </p>
          <dl className="mt-4 flex flex-wrap gap-5">
            {Object.entries(eventLabels).map(([key, label]) => (
              <div key={key}><dt className="text-sm text-zinc-600">{label}</dt><dd className="font-semibold">{status.metrics[key] ?? 0}</dd></div>
            ))}
          </dl>
        </section>
      )}
      <section aria-labelledby="sync-credentials" className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4">
        <h2 id="sync-credentials" className="font-semibold">Credenciais dos conectores</h2>
        {status && integrations.length === 0 && <p className="text-sm text-zinc-600">Nenhum conector configurado.</p>}
        {integrations.map(integration => (
          <div key={integration.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 py-3 text-sm">
            <p>{integration.store_name} · {integration.connector_name} · {integration.active ? "Ativa" : "Desativada"}</p>
            <div className="flex gap-3">
              <button onClick={() => { setSecret(""); setTarget({ integration, revoke: false }); }}>Gerar nova chave</button>
              <button disabled={!integration.active} onClick={() => { setSecret(""); setTarget({ integration, revoke: true }); }}>Revogar</button>
            </div>
          </div>
        ))}
        {secret && (
          <div className="space-y-2">
            <label htmlFor="sync-new-secret" className="block text-sm font-medium">Chave nova. Copie para o parceiro autorizado.</label>
            <input id="sync-new-secret" value={secret} readOnly onFocus={event => event.currentTarget.select()} className="w-full rounded border p-2" />
            <button onClick={() => setSecret("")}>Fechar chave</button>
          </div>
        )}
      </section>
      <ConfirmModal
        isOpen={target !== null}
        title={target?.revoke ? "Revogar credencial do conector" : "Gerar outra credencial"}
        message={target?.revoke ? "A integração será desativada e a chave atual perderá a validade." : "A chave anterior perderá a validade. Atualize a credencial no parceiro."}
        onConfirm={updateCredential}
        onCancel={() => setTarget(null)}
      />
    </div>
  );
}
