const BASE = ''

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
