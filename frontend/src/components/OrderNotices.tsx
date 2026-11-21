import { useEffect, useRef, useState } from "react";
import { Bell, X } from "lucide-react";
import { authFetch } from "../lib/api";

interface OrderNotice {
  id: string;
  status: "COMPLETED" | "CANCELED" | "RETURNED";
  date: string | null;
  read: boolean;
}

const labels = {
  COMPLETED: "Corrida concluída",
  CANCELED: "Corrida cancelada",
  RETURNED: "Devolução concluída",
};

export function OrderNotices() {
  const [open, setOpen] = useState(false);
  const [notices, setNotices] = useState<OrderNotice[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const unread = notices.filter(notice => !notice.read).length;

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await authFetch("/api/v1/db/order-notices");
      if (!response.ok) throw new Error("Não foi possível consultar as notificações.");
      setNotices(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao consultar as corridas recentes.");
    } finally { setLoading(false); }
  }

  async function markRead(id: string) {
    setSaving(id);
    setError("");
    try {
      const response = await authFetch(`/api/v1/db/order-notices/${id}/read`, { method: "POST" });
      if (!response.ok) throw new Error("Não foi possível marcar a notificação como lida.");
      setNotices(previous => previous.map(notice => notice.id === id ? { ...notice, read: true } : notice));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao atualizar a notificação.");
    } finally { setSaving(null); }
  }

  useEffect(() => { if (open) closeButton.current?.focus(); }, [open]);

  function close() {
    setOpen(false);
    trigger.current?.focus();
  }

  return (
    <div className="relative">
      <button
        ref={trigger}
        type="button"
        aria-label={unread ? `Notificações, ${unread} não lidas` : "Notificações"}
        aria-expanded={open}
        aria-controls="order-notices"
        className="relative rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 focus-visible:ring-2"
        onClick={() => { if (open) close(); else { setOpen(true); void load(); } }}
      >
        <Bell className="h-4 w-4" aria-hidden="true" />
        {unread > 0 && <span aria-hidden="true" className="absolute right-1 top-1 h-2 w-2 rounded-full bg-rose-600" />}
      </button>
      {open && (
        <section
          id="order-notices"
          aria-label="Notificações recentes de corridas"
          onKeyDown={event => { if (event.key === "Escape") close(); }}
          className="absolute right-0 top-full z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-zinc-200 bg-white p-3 shadow-lg"
        >
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-semibold">Corridas recentes</h2>
            <button ref={closeButton} onClick={close} aria-label="Fechar notificações" className="p-2"><X className="h-4 w-4" /></button>
          </div>
          {loading && <p role="status" className="text-sm">Consultando notificações…</p>}
          {error && <p role="alert" className="text-sm text-rose-700">{error} <button className="underline" onClick={() => void load()}>Tentar novamente</button></p>}
          {!loading && !error && notices.length === 0 && <p className="text-sm text-zinc-600">Nenhuma corrida concluída, cancelada ou devolvida recentemente.</p>}
          <ul className="max-h-80 divide-y divide-zinc-100 overflow-y-auto">
            {notices.map(notice => (
              <li key={notice.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                <div><p className="font-medium">{labels[notice.status]}</p><p className="text-xs text-zinc-600">#{notice.id.slice(0, 8)} {notice.date && new Date(notice.date).toLocaleString("pt-BR")}</p></div>
                {!notice.read && <button type="button" disabled={saving !== null} className="underline" onClick={() => void markRead(notice.id)}>Marcar como lida</button>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
