import { useState } from 'react'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FORM_TYPE_LABELS = {
  loan_application: 'Loan Application',
  membership_application: 'Membership Application',
  beneficiary_designation: 'Beneficiary Designation',
  change_of_address: 'Change of Address',
  unknown: 'Unknown Form',
}

// Fields that are internal metadata, not displayed to the user
const META_FIELDS = new Set([
  'form_type',
  'extraction_confidence',
  'missing_required_fields',
  'validation_errors',
])

// Logical section groupings per form type
const SECTION_MAP = {
  loan_application: {
    'Applicant Info': ['applicant_name', 'ssn_last4', 'date_of_birth', 'address'],
    'Employment & Financial': ['employer', 'annual_income', 'loan_amount_requested', 'loan_purpose'],
    'Co-Applicant': ['co_applicant'],
  },
  membership_application: {
    'Personal Info': ['first_name', 'last_name', 'ssn_last4', 'date_of_birth'],
    'Contact': ['address', 'phone', 'email'],
    'Identification': ['id_type', 'id_number'],
    'Financial': ['initial_deposit'],
  },
  beneficiary_designation: {
    'Member Info': ['member_name', 'account_number'],
    'Beneficiaries': ['beneficiaries'],
  },
  change_of_address: {
    'Member Info': ['member_name', 'account_number'],
    'Previous Address': ['old_address'],
    'New Address': ['new_address'],
    'Details': ['effective_date'],
  },
}

function formatLabel(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatValue(value) {
  if (value === null || value === undefined) return null
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  if (typeof value === 'number') return value.toLocaleString()
  return String(value)
}

function confidenceColor(score) {
  if (score >= 0.9) return 'text-emerald-600 bg-emerald-50 border-emerald-200'
  if (score >= 0.7) return 'text-amber-600 bg-amber-50 border-amber-200'
  return 'text-red-600 bg-red-50 border-red-200'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function EditableField({ fieldKey, value, isMissing, isError, isLowConf, onChange }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(formatValue(value) ?? '')

  const rowClass = [
    'group flex items-start gap-3 rounded-lg px-3 py-2 transition-colors',
    isMissing || isError
      ? 'bg-red-50 border border-red-200'
      : isLowConf
      ? 'bg-amber-50 border border-amber-200'
      : 'border border-transparent hover:bg-slate-50',
  ].join(' ')

  const commit = () => {
    setEditing(false)
    onChange(fieldKey, draft)
  }

  const displayValue = formatValue(value)

  return (
    <div className={rowClass}>
      <span className="w-40 shrink-0 text-xs font-medium text-slate-500 pt-1">
        {formatLabel(fieldKey)}
      </span>

      <div className="flex-1 min-w-0">
        {editing ? (
          <input
            autoFocus
            className="w-full rounded border border-brand-400 bg-white px-2 py-0.5 text-sm text-slate-800 outline-none focus:ring-2 focus:ring-brand-300"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit()
              if (e.key === 'Escape') setEditing(false)
            }}
          />
        ) : (
          <span
            className={[
              'block text-sm break-words',
              displayValue === null ? 'italic text-slate-400' : 'text-slate-800',
            ].join(' ')}
          >
            {displayValue ?? 'Not extracted'}
          </span>
        )}

        {isMissing && (
          <span className="mt-0.5 block text-xs text-red-600">Required field missing</span>
        )}
      </div>

      {!editing && (
        <button
          aria-label={`Edit ${formatLabel(fieldKey)}`}
          onClick={() => { setDraft(displayValue ?? ''); setEditing(true) }}
          className="shrink-0 rounded p-1 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:bg-brand-100 hover:text-brand-600"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
          </svg>
        </button>
      )}
    </div>
  )
}

function Section({ title, fields, data, missingFields, errorFields, confidence, onFieldChange }) {
  if (fields.length === 0) return null

  const visibleFields = fields.filter((k) => !META_FIELDS.has(k))
  if (visibleFields.length === 0) return null

  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-brand-600">
        {title}
      </h3>
      <div className="flex flex-col gap-1">
        {visibleFields.map((key) => (
          <EditableField
            key={key}
            fieldKey={key}
            value={data[key]}
            isMissing={missingFields.includes(key)}
            isError={errorFields.some((e) => e.toLowerCase().includes(key.replace(/_/g, ' ')))}
            isLowConf={confidence < 0.7}
            onChange={onFieldChange}
          />
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// CSV export
// ---------------------------------------------------------------------------

function flattenForCsv(data, prefix = '') {
  const rows = []
  for (const [k, v] of Object.entries(data)) {
    if (META_FIELDS.has(k)) continue
    const label = prefix ? `${prefix} > ${formatLabel(k)}` : formatLabel(k)
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      rows.push(...flattenForCsv(v, label))
    } else if (Array.isArray(v)) {
      v.forEach((item, i) => {
        if (typeof item === 'object' && item !== null) {
          rows.push(...flattenForCsv(item, `${label} [${i + 1}]`))
        } else {
          rows.push([`${label} [${i + 1}]`, String(item ?? '')])
        }
      })
    } else {
      rows.push([label, String(v ?? '')])
    }
  }
  return rows
}

function exportCsv(data, formType) {
  const rows = flattenForCsv(data)
  const csv = ['Field,Value', ...rows.map(([f, v]) => `"${f}","${v.replace(/"/g, '""')}"`)].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${formType}_extraction.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ExtractedDataCard({ result, onClear }) {
  const [data, setData] = useState(result.extracted_data ?? {})
  const [copied, setCopied] = useState(false)

  const formType = result.form_type
  const confidence = data.extraction_confidence ?? result.extracted_data?.extraction_confidence ?? 0
  const missingFields = data.missing_required_fields ?? []
  const validationErrors = result.validation?.errors ?? []
  const validationWarnings = result.validation?.warnings ?? []
  const processingMs = result.processing_time_ms

  const sections = SECTION_MAP[formType] ?? { 'Extracted Fields': Object.keys(data).filter(k => !META_FIELDS.has(k)) }

  const handleFieldChange = (key, newValue) => {
    setData((prev) => ({ ...prev, [key]: newValue }))
  }

  const handleCopyJson = async () => {
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (formType === 'unknown') {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50 p-10 text-center">
        <p className="font-semibold text-red-700">Form type could not be identified</p>
        <p className="text-sm text-red-600">
          Ensure the uploaded document is one of: Loan Application, Membership Application,
          Beneficiary Designation, or Change of Address.
        </p>
        <button onClick={onClear} className="mt-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">
          Try another file
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 bg-slate-50 px-5 py-4">
        <span className="rounded-full bg-brand-600 px-3 py-1 text-xs font-semibold text-white">
          {FORM_TYPE_LABELS[formType] ?? formType}
        </span>

        <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${confidenceColor(confidence)}`}>
          <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden>
            <path fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414L8.414 15 3.293 9.879a1 1 0 011.414-1.415L8.414 12.172l6.879-6.879a1 1 0 011.414 0z"
              clipRule="evenodd" />
          </svg>
          Confidence {Math.round(confidence * 100)}%
        </div>

        <span className="text-xs text-slate-400">{processingMs} ms</span>

        {missingFields.length > 0 && (
          <span className="ml-auto rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
            {missingFields.length} missing field{missingFields.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Validation banners */}
      {validationErrors.length > 0 && (
        <div className="border-b border-red-200 bg-red-50 px-5 py-3">
          <p className="mb-1 text-xs font-semibold text-red-700">Validation errors</p>
          <ul className="list-disc pl-4 space-y-0.5">
            {validationErrors.map((e, i) => (
              <li key={i} className="text-xs text-red-600">{e}</li>
            ))}
          </ul>
        </div>
      )}

      {validationWarnings.length > 0 && (
        <div className="border-b border-amber-200 bg-amber-50 px-5 py-3">
          <p className="mb-1 text-xs font-semibold text-amber-700">Warnings</p>
          <ul className="list-disc pl-4 space-y-0.5">
            {validationWarnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-600">{w}</li>
            ))}
          </ul>
        </div>
      )}

      {confidence < 0.7 && (
        <div className="border-b border-amber-200 bg-amber-50 px-5 py-2">
          <p className="text-xs font-semibold text-amber-700">
            Low confidence — flagged for human review
          </p>
        </div>
      )}

      {/* Field sections */}
      <div className="flex flex-col gap-6 overflow-y-auto px-5 py-5" style={{ maxHeight: 'calc(100vh - 280px)' }}>
        {Object.entries(sections).map(([sectionTitle, fields]) => (
          <Section
            key={sectionTitle}
            title={sectionTitle}
            fields={fields}
            data={data}
            missingFields={missingFields}
            errorFields={validationErrors}
            confidence={confidence}
            onFieldChange={handleFieldChange}
          />
        ))}
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 bg-slate-50 px-5 py-3">
        <button
          onClick={handleCopyJson}
          className="flex items-center gap-1.5 rounded-lg border border-brand-200 bg-white px-3 py-1.5 text-xs font-medium text-brand-700 transition hover:bg-brand-50"
        >
          {copied ? (
            <>
              <svg className="h-3.5 w-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
              </svg>
              Copy as JSON
            </>
          )}
        </button>

        <button
          onClick={() => exportCsv(data, formType)}
          className="flex items-center gap-1.5 rounded-lg border border-brand-200 bg-white px-3 py-1.5 text-xs font-medium text-brand-700 transition hover:bg-brand-50"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Export to CSV
        </button>

        <button
          onClick={onClear}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-red-50 hover:border-red-200 hover:text-red-600"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Clear
        </button>
      </div>
    </div>
  )
}
