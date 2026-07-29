// Thin fetch wrapper that attaches the API key backend/lewtrade.auth expects.
// Baked in at build time via VITE_API_KEY — set it in frontend/.env before
// building for prod (matches LEWTRADE_API_KEY on the backend).
const API_KEY = import.meta.env.VITE_API_KEY || ''

export function apiFetch(path, options = {}) {
  if (!API_KEY) return fetch(path, options)
  return fetch(path, { ...options, headers: { ...options.headers, 'X-API-Key': API_KEY } })
}
