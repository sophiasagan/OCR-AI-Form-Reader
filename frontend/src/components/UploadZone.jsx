import { useCallback, useRef, useState } from 'react'

const ACCEPTED = {
  'application/pdf': 'PDF',
  'image/jpeg': 'JPG',
  'image/png': 'PNG',
  'image/tiff': 'TIFF',
  'image/webp': 'WEBP',
}
const MAX_BYTES = 10 * 1024 * 1024

function FileTypeChip({ label }) {
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-brand-100 text-brand-700 border border-brand-200">
      {label}
    </span>
  )
}

export default function UploadZone({ onResult, loading, setLoading }) {
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleFile = useCallback(
    async (file) => {
      setError(null)

      if (!ACCEPTED[file.type]) {
        setError(`Unsupported file type "${file.type}". Upload a PDF, JPG, or PNG.`)
        return
      }
      if (file.size > MAX_BYTES) {
        setError(`File is ${(file.size / 1_048_576).toFixed(1)} MB — maximum is 10 MB.`)
        return
      }

      setLoading(true)
      setProgress(0)

      try {
        const { extractForm } = await import('../api.js')
        const result = await extractForm(file, setProgress)
        onResult(result, file)
      } catch (err) {
        setError(err.message ?? 'Extraction failed. Please try again.')
      } finally {
        setLoading(false)
        setProgress(0)
      }
    },
    [onResult, setLoading]
  )

  const onDrop = useCallback(
    (e) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  const onInputChange = (e) => {
    const file = e.target.files[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload form — click or drag a file here"
        onClick={() => !loading && inputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && !loading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={[
          'relative flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed px-6 py-12 transition-colors',
          dragging
            ? 'border-brand-500 bg-brand-50'
            : 'border-brand-300 bg-white hover:border-brand-400 hover:bg-brand-50',
          loading ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        ].join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept={Object.keys(ACCEPTED).join(',')}
          className="hidden"
          onChange={onInputChange}
          disabled={loading}
        />

        {/* Upload icon */}
        <svg
          className="h-12 w-12 text-brand-400"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.2}
          stroke="currentColor"
          aria-hidden
        >
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M12 16V4m0 0L8 8m4-4 4 4M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1" />
        </svg>

        <div className="text-center">
          <p className="text-sm font-semibold text-brand-700">
            {loading ? 'Extracting…' : 'Drag & drop or click to upload'}
          </p>
          <p className="mt-1 text-xs text-slate-500">Credit union forms — max 10 MB</p>
        </div>

        <div className="flex gap-2">
          {Object.values(ACCEPTED).map((label) => (
            <FileTypeChip key={label} label={label} />
          ))}
        </div>
      </div>

      {/* Progress bar */}
      {loading && (
        <div className="h-2 w-full overflow-hidden rounded-full bg-brand-100">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3"
        >
          <svg className="mt-0.5 h-4 w-4 shrink-0 text-red-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden>
            <path fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm-.75-11.25a.75.75 0 011.5 0v4a.75.75 0 01-1.5 0v-4zm.75 7a1 1 0 100-2 1 1 0 000 2z"
              clipRule="evenodd" />
          </svg>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}
    </div>
  )
}
