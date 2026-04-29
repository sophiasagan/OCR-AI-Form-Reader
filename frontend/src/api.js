// On Vercel both frontend and backend share the same domain, so relative URLs
// work without any env var. Set VITE_API_URL only if the backend is hosted
// separately (e.g. Railway). Dev uses the Vite proxy to localhost:8000.
const BASE = import.meta.env.VITE_API_URL ?? ''

export async function extractForm(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  // Simulate upload progress (XHR gives real upload progress;
  // fetch does not expose it, so we animate to 30% then wait for response)
  onProgress?.(10)
  const timer = setTimeout(() => onProgress?.(30), 400)

  const res = await fetch(`${BASE}/extract`, {
    method: 'POST',
    body: formData,
  })

  clearTimeout(timer)
  onProgress?.(90)

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Server error ${res.status}`)
  }

  const data = await res.json()
  onProgress?.(100)
  return data
}

export async function getFormTypes() {
  const res = await fetch(`${BASE}/form-types`)
  if (!res.ok) throw new Error('Failed to load form types')
  return res.json()
}
