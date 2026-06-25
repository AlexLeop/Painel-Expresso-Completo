/**
 * useApiQuery — Stale-While-Revalidate (SWR) hook customizado para NevesGo.
 *
 * Recursos:
 * - Cache global em memória compartilhado entre todos os componentes.
 * - Desduplicação: múltiplos componentes pedindo a mesma rota ao mesmo tempo
 *   disparam apenas 1 requisição HTTP real.
 * - Revalidação silenciosa em segundo plano (configurable via refreshInterval).
 * - Pausa automática quando a aba está inativa (document.hidden).
 * - Mutação programática de cache para atualizações otimistas.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { authFetch } from './api';

// ─── Tipos ────────────────────────────────────────────────────────────────────

interface CacheItem<T> {
  data: T;
  timestamp: number;
  error?: string;
}

type FetchStatus = 'idle' | 'loading' | 'revalidating' | 'error' | 'success';

interface UseApiQueryResult<T> {
  data: T | null;
  error: string | null;
  status: FetchStatus;
  isLoading: boolean;
  isValidating: boolean;
  mutate: (updater?: T | ((prev: T | null) => T)) => void;
  refresh: () => void;
}

interface UseApiQueryOptions {
  /** Intervalo em ms para revalidação silenciosa. 0 desativa. Default: 30000 */
  refreshInterval?: number;
  /** Se false, a query não é disparada (útil para dependências). Default: true */
  enabled?: boolean;
  /** Tempo máximo em ms para considerar o cache como válido. Default: 15000 */
  staleTime?: number;
  /** Revalida automaticamente ao focar a aba. Default: true */
  revalidateOnFocus?: boolean;
}

// ─── Cache e controle de requisições em andamento (singleton global) ──────────

const globalCache = new Map<string, CacheItem<unknown>>();
const inflightRequests = new Map<string, Promise<unknown>>();
const listeners = new Map<string, Set<() => void>>();

function notifyListeners(key: string) {
  listeners.get(key)?.forEach(cb => cb());
}

function subscribe(key: string, cb: () => void) {
  if (!listeners.has(key)) listeners.set(key, new Set());
  listeners.get(key)!.add(cb);
  return () => listeners.get(key)?.delete(cb);
}

// ─── Mutação pública (pode ser usada fora de componentes) ────────────────────

export function mutateCache<T>(key: string, updater: T | ((prev: T | null) => T)): void {
  const existing = globalCache.get(key);
  const prev = existing ? (existing.data as T) : null;
  const next = typeof updater === 'function' ? (updater as (p: T | null) => T)(prev) : updater;
  globalCache.set(key, { data: next, timestamp: Date.now() });
  notifyListeners(key);
}

// ─── Core do hook ─────────────────────────────────────────────────────────────

export function useApiQuery<T = unknown>(
  key: string | null,
  options: UseApiQueryOptions = {}
): UseApiQueryResult<T> {
  const {
    refreshInterval = 30_000,
    enabled = true,
    staleTime = 15_000,
    revalidateOnFocus = true,
  } = options;

  const [, forceRender] = useState(0);
  const statusRef = useRef<FetchStatus>('idle');
  const mountedRef = useRef(true);

  // Obter dados do cache compartilhado
  const cached = key ? (globalCache.get(key) as CacheItem<T> | undefined) : undefined;
  const data = cached?.data ?? null;
  const isStale = !cached || Date.now() - cached.timestamp > staleTime;

  const rerender = useCallback(() => {
    if (mountedRef.current) forceRender(n => n + 1);
  }, []);

  // Função de fetch com desduplicação
  const doFetch = useCallback(async (silent: boolean) => {
    if (!key || !enabled) return;

    const nextStatus: FetchStatus = silent ? 'revalidating' : 'loading';
    statusRef.current = nextStatus;
    if (!silent) rerender();

    // Desduplicação: reutiliza a Promise em andamento se já existir
    let request = inflightRequests.get(key);
    if (!request) {
      request = authFetch(key)
        .then(async res => {
          if (!res.ok) throw new Error(`API retornou ${res.status}`);
          return res.json();
        })
        .finally(() => {
          inflightRequests.delete(key);
        });
      inflightRequests.set(key, request);
    }

    try {
      const result = await request;
      globalCache.set(key, { data: result, timestamp: Date.now() });
      statusRef.current = 'success';
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro desconhecido';
      const fallback = globalCache.get(key);
      globalCache.set(key, {
        data: fallback?.data ?? null,
        timestamp: fallback?.timestamp ?? Date.now(),
        error: msg,
      });
      statusRef.current = 'error';
    } finally {
      notifyListeners(key!);
      rerender();
    }
  }, [key, enabled, rerender]);

  // Subscrição a mudanças no cache global (para mutações otimistas de fora)
  useEffect(() => {
    if (!key) return;
    const unsub = subscribe(key, rerender);
    return () => { unsub(); };
  }, [key, rerender]);

  // Disparar fetch inicial
  useEffect(() => {
    mountedRef.current = true;
    if (!key || !enabled) return;

    if (isStale) {
      doFetch(!!cached); // silent se já há dados em cache
    }

    return () => { mountedRef.current = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled]);

  // Revalidação periódica
  useEffect(() => {
    if (!key || !enabled || refreshInterval <= 0) return;

    const id = setInterval(() => {
      if (document.hidden) return; // Pausa quando a aba está inativa
      doFetch(true);
    }, refreshInterval);

    return () => clearInterval(id);
  }, [key, enabled, refreshInterval, doFetch]);

  // Revalidar ao focar a aba
  useEffect(() => {
    if (!revalidateOnFocus || !key || !enabled) return;

    const handleFocus = () => {
      const item = globalCache.get(key);
      const needsRevalidation = !item || Date.now() - item.timestamp > staleTime;
      if (needsRevalidation) doFetch(true);
    };

    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) handleFocus();
    });

    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, [key, enabled, staleTime, doFetch, revalidateOnFocus]);

  // Mutação local (atualiza cache e re-renderiza)
  const mutate = useCallback((updater?: T | ((prev: T | null) => T)) => {
    if (!key) return;
    if (updater !== undefined) {
      mutateCache(key, updater);
    } else {
      // Sem updater: invalida o cache e refaz a busca
      globalCache.delete(key);
      doFetch(false);
    }
  }, [key, doFetch]);

  const refresh = useCallback(() => {
    if (!key) return;
    doFetch(false);
  }, [key, doFetch]);

  const errorMsg = (cached as CacheItem<T> & { error?: string } | undefined)?.error ?? null;

  return {
    data,
    error: errorMsg,
    status: statusRef.current,
    isLoading: statusRef.current === 'loading',
    isValidating: statusRef.current === 'revalidating',
    mutate,
    refresh,
  };
}
