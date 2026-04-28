import { useState } from 'react'
import UploadZone from './components/UploadZone'
import FormPreview from './components/FormPreview'
import ExtractedDataCard from './components/ExtractedDataCard'

export default function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleResult = (extractionResult, uploadedFile) => {
    setResult(extractionResult)
    setFile(uploadedFile)
  }

  const handleClear = () => {
    setResult(null)
    setFile(null)
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      {/* Top nav */}
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-screen-xl items-center gap-3 px-6 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
            <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25M9 16.5v.75m3-3v3M15 12v5.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-900 leading-tight">CU Form Reader</h1>
            <p className="text-xs text-slate-500">AI-powered credit union form extraction</p>
          </div>

          {loading && (
            <div className="ml-auto flex items-center gap-2 text-xs text-brand-600">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-brand-400 border-t-brand-700" />
              Extracting with Claude…
            </div>
          )}
        </div>
      </header>

      {/* Main two-panel layout */}
      <main className="mx-auto flex w-full max-w-screen-xl flex-1 gap-6 px-6 py-6">
        {/* Left panel — 40% */}
        <aside className="flex w-2/5 shrink-0 flex-col gap-4">
          <UploadZone
            onResult={handleResult}
            loading={loading}
            setLoading={setLoading}
          />
          <FormPreview file={file} />
        </aside>

        {/* Right panel — 60% */}
        <section className="flex flex-1 flex-col">
          {result ? (
            <ExtractedDataCard result={result} onClear={handleClear} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-slate-300 bg-white text-center">
              <svg className="h-14 w-14 text-slate-200" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
              </svg>
              <div>
                <p className="font-semibold text-slate-400">No form extracted yet</p>
                <p className="mt-1 text-sm text-slate-400">
                  Upload a credit union form on the left to begin
                </p>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
