export async function authFetch(url: string, options: RequestInit = {}) {
  const sessionString = localStorage.getItem('nevesgo:session');
  
  if (!sessionString) {
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('Usuário não está autenticado');
  }
  
  let session: Record<string, any>;
  try {
    session = JSON.parse(sessionString);
  } catch {
    // Session data corrupted — clear and redirect to login
    localStorage.removeItem('nevesgo:session');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('Sessão corrompida. Redirecionando para login.');
  }
  const headers = new Headers(options.headers || {});

  if (session.basicAuth) {
    headers.set('Authorization', `Basic ${session.basicAuth}`);
  }

  if (session.user?.company_id) {
    headers.set('X-Tenant-Id', String(session.user.company_id));
  }
  if (session.user?.role) {
    headers.set('X-User-Role', session.user.role);
  }
  if (session.user?.email) {
    headers.set('X-User-Email', session.user.email);
  }

  if (options.body && (!options.headers || !(options.headers as Record<string, string>)['Content-Type'])) {
    headers.set('Content-Type', 'application/json');
  }

  // When deployed together, frontend and backend are on the same domain — use relative URLs
  const BASE_URL = import.meta.env.VITE_API_URL || '';
  
  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (response.status === 401) {
    localStorage.removeItem('nevesgo:session');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('Sessão expirada ou acesso negado (401).');
  }

  return response;
}

/**
 * Returns the parsed session object from localStorage, or null if not authenticated.
 */
export function getSession(): { basicAuth: string; user: Record<string, unknown> } | null {
  const sessionString = localStorage.getItem('nevesgo:session');
  if (!sessionString) return null;
  try {
    return JSON.parse(sessionString);
  } catch {
    return null;
  }
}
