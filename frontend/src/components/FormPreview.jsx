export default function FormPreview({ file }) {
  if (!file) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm text-slate-400">
        No file selected
      </div>
    )
  }

  const url = URL.createObjectURL(file)
  const isPdf = file.type === 'application/pdf'

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2">
        <svg className="h-4 w-4 text-brand-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
        <span className="truncate text-xs font-medium text-slate-600">{file.name}</span>
        <span className="ml-auto text-xs text-slate-400">
          {(file.size / 1024).toFixed(0)} KB
        </span>
      </div>

      {isPdf ? (
        <iframe
          src={url}
          title="Form preview"
          className="h-80 w-full"
          aria-label="Uploaded PDF preview"
        />
      ) : (
        <img
          src={url}
          alt="Uploaded form preview"
          className="max-h-80 w-full object-contain p-2"
        />
      )}
    </div>
  )
}
