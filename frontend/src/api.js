// Thin fetch wrapper that attaches the API key backend/lewtrade.auth expects.
// Baked in at build time via VITE_API_KEY — set it in frontend/.env before
// building for prod (matches LEWTRADE_API_KEY on the backend).
const API_KEY = import.meta.env.VITE_API_KEY || ''

export function apiFetch(path, options = {}) {
  if (!API_KEY) return fetch(path, options)
  return fetch(path, { ...options, headers: { ...options.headers, 'X-API-Key': API_KEY } })
}

// Cloudflare (this site is proxied through it) sometimes substitutes its own
// plain-text/HTML error page for a response instead of relaying the origin's
// real body — res.json() then throws a confusing "Unexpected token" parse
// error. Always fall back to a status-based message instead of leaking that.
export async function apiFetchJson(path, options = {}) {
  const res = await apiFetch(path, options)
  let data = null
  try {
    data = await res.json()
  } catch {
    // non-JSON body (upstream error page) — data stays null, handled below
  }
  if (!res.ok) throw new Error(data?.detail || `Request failed (HTTP ${res.status})`)
  return data
}
