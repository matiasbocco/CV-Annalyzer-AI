import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useBulkUploadCVs, useExtractContact, useUploadCV } from '../api/hooks'
import type { BulkUploadResponse, ContactInfo, UploadResponse } from '../api/types'
import { cn, getErrorMessage } from '../lib/utils'
import LoadingScreen from '../components/LoadingScreen'

const MAX_FILES = 30

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/webp': ['.webp'],
}

type ContactDraft = {
  full_name: string
  email: string
  phone: string
  linkedin_url: string
  github_url: string
  portfolio_url: string
  location: string
  availability: string
}

function toContactInfo(draft: ContactDraft): Partial<ContactInfo> {
  const out: Partial<ContactInfo> = {}
  if (draft.full_name.trim())     out.full_name     = draft.full_name.trim()
  if (draft.email.trim())         out.email         = draft.email.trim()
  if (draft.phone.trim())         out.phone         = draft.phone.trim()
  if (draft.linkedin_url.trim())  out.linkedin_url  = draft.linkedin_url.trim()
  if (draft.github_url.trim())    out.github_url    = draft.github_url.trim()
  if (draft.portfolio_url.trim()) out.portfolio_url = draft.portfolio_url.trim()
  if (draft.location.trim())      out.location      = draft.location.trim()
  if (draft.availability)         out.availability  = draft.availability as ContactInfo['availability']
  return out
}

function extractedToContactDraft(extracted: Partial<ContactInfo>): ContactDraft {
  return {
    full_name:     extracted.full_name     ?? '',
    email:         extracted.email         ?? '',
    phone:         extracted.phone         ?? '',
    linkedin_url:  extracted.linkedin_url  ?? '',
    github_url:    extracted.github_url    ?? '',
    portfolio_url: extracted.portfolio_url ?? '',
    location:      extracted.location      ?? '',
    availability:  extracted.availability  ?? '',
  }
}

// ── Step indicator (single-file flow only) ────────────────────────────────────

function StepIndicator({ step }: { step: 1 | 2 }) {
  const steps = ['Seleccionar archivo', 'Confirmar datos']
  return (
    <div className="flex items-center gap-2 mb-6">
      {steps.map((label, idx) => {
        const n = idx + 1
        const isActive = step === n
        const isDone   = step > n
        return (
          <div key={n} className="flex items-center gap-2">
            <div className={cn(
              'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all',
              isDone   ? 'bg-emerald-500 text-white' :
              isActive ? 'bg-gradient-to-br from-blue-600 to-sky-500 text-white' :
                         'bg-slate-800 text-slate-500 border border-slate-700',
            )}>
              {isDone ? '✓' : n}
            </div>
            <span className={cn(
              'text-sm transition-colors',
              isActive ? 'text-slate-200 font-medium' : 'text-slate-600',
            )}>
              {label}
            </span>
            {n < steps.length && (
              <span className="text-slate-700 mx-1">→</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Input helper ──────────────────────────────────────────────────────────────

function Field({
  label,
  value,
  onChange,
  placeholder,
  required,
  highlight,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  required?: boolean
  highlight?: boolean
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
        {highlight && !value && (
          <span className="ml-2 text-amber-400 font-normal">requerido</span>
        )}
      </label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          'w-full rounded-lg px-3 py-2 text-sm bg-slate-800/50 text-slate-200 placeholder-slate-600',
          'border focus:outline-none focus:ring-1 transition-colors',
          highlight && !value
            ? 'border-amber-500/60 focus:border-amber-500 focus:ring-amber-500/20'
            : 'border-slate-700 focus:border-sky-500 focus:ring-sky-500/20',
        )}
      />
    </div>
  )
}

// ── File picker (multi-file) ──────────────────────────────────────────────────

function MultiFilePicker({
  files,
  onFiles,
}: {
  files: File[]
  onFiles: (files: File[]) => void
}) {
  const onDrop = useCallback((accepted: File[]) => {
    onFiles((prev: File[]) => {
      const names = new Set(prev.map(f => f.name))
      const merged = [...prev, ...accepted.filter(f => !names.has(f.name))]
      return merged.slice(0, MAX_FILES)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple: true,
  })

  function removeFile(name: string) {
    onFiles((prev: File[]) => prev.filter(f => f.name !== name))
  }

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all',
          isDragActive
            ? 'border-sky-500 bg-sky-500/5'
            : 'border-slate-700 hover:border-slate-600',
        )}
      >
        <input {...getInputProps()} />
        <p className="text-3xl mb-2">📄</p>
        <p className="text-sm text-slate-400">
          {isDragActive
            ? 'Soltá los archivos aquí…'
            : 'Arrastrá CVs aquí, o hacé clic para seleccionar'}
        </p>
        <p className="text-xs text-slate-600 mt-1">
          PDF · DOCX · JPG · PNG · WEBP · hasta {MAX_FILES} archivos
        </p>
      </div>

      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map(f => (
            <span
              key={f.name}
              className="inline-flex items-center gap-1.5 bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded-lg px-3 py-1.5 max-w-[220px]"
            >
              <span className="truncate">{f.name}</span>
              <button
                type="button"
                onClick={() => removeFile(f.name)}
                className="flex-shrink-0 text-slate-500 hover:text-red-400 transition-colors leading-none text-base"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {files.length >= MAX_FILES && (
        <p className="text-xs text-amber-400">
          Límite de {MAX_FILES} archivos alcanzado.
        </p>
      )}
    </div>
  )
}

// ── Step 2 — Contact form ─────────────────────────────────────────────────────

function ContactForm({
  draft,
  missingFields,
  onChange,
  onSubmit,
  onBack,
  isSubmitting,
  submitError,
}: {
  draft: ContactDraft
  missingFields: string[]
  onChange: (d: ContactDraft) => void
  onSubmit: () => void
  onBack: () => void
  isSubmitting: boolean
  submitError: string | null
}) {
  const missing = new Set(missingFields)
  const canSubmit = draft.full_name.trim() && draft.email.trim()

  function set(key: keyof ContactDraft) {
    return (v: string) => onChange({ ...draft, [key]: v })
  }

  return (
    <div className="space-y-4">
      {missingFields.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-sm text-amber-300">
          Completá los campos marcados para que el sistema pueda contactarte.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field label="Nombre completo" value={draft.full_name}    onChange={set('full_name')}    placeholder="Juan García"              required highlight={missing.has('full_name')} />
        <Field label="Email"           value={draft.email}        onChange={set('email')}        placeholder="juan@ejemplo.com"         required highlight={missing.has('email')} />
        <Field label="Teléfono"        value={draft.phone}        onChange={set('phone')}        placeholder="+54 9 11 …" />
        <Field label="Ubicación"       value={draft.location}     onChange={set('location')}     placeholder="Buenos Aires" />
        <Field label="LinkedIn"        value={draft.linkedin_url} onChange={set('linkedin_url')} placeholder="linkedin.com/in/…" />
        <Field label="GitHub"          value={draft.github_url}   onChange={set('github_url')}   placeholder="github.com/…" />
        <Field label="Portfolio"       value={draft.portfolio_url}onChange={set('portfolio_url')}placeholder="https://…" />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1">
          Disponibilidad
          {missing.has('availability') && !draft.availability && (
            <span className="ml-2 text-amber-400 font-normal">requerido</span>
          )}
        </label>
        <select
          value={draft.availability}
          onChange={e => onChange({ ...draft, availability: e.target.value })}
          className={cn(
            'w-full rounded-lg px-3 py-2 text-sm bg-slate-800/50 text-slate-200',
            'border focus:outline-none focus:ring-1 transition-colors',
            missing.has('availability') && !draft.availability
              ? 'border-amber-500/60 focus:border-amber-500 focus:ring-amber-500/20'
              : 'border-slate-700 focus:border-sky-500 focus:ring-sky-500/20',
          )}
        >
          <option value="" className="bg-slate-900">Sin especificar</option>
          <option value="available"   className="bg-slate-900">Disponible activamente</option>
          <option value="open"        className="bg-slate-900">Abierto a oportunidades</option>
          <option value="not_looking" className="bg-slate-900">No disponible</option>
        </select>
      </div>

      {submitError && (
        <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5">
          {submitError}
        </p>
      )}

      <div className="flex gap-3 pt-1">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 text-sm text-slate-400 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 hover:text-slate-200 transition-colors"
        >
          ← Volver
        </button>
        <button
          type="button"
          disabled={!canSubmit || isSubmitting}
          onClick={onSubmit}
          className="flex-1 bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600 text-white font-semibold py-2.5 rounded-xl disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed transition-all"
        >
          {isSubmitting ? 'Guardando…' : 'Guardar CV'}
        </button>
      </div>
    </div>
  )
}

// ── Success card (single file) ────────────────────────────────────────────────

function SuccessCard({ result, onReset }: { result: UploadResponse; onReset: () => void }) {
  const isDuplicate = result.status === 'duplicate'
  return (
    <div className="text-center space-y-5 py-6">
      <div className={cn(
        'w-16 h-16 rounded-full flex items-center justify-center text-3xl mx-auto',
        isDuplicate
          ? 'bg-amber-500/20 border border-amber-500/30'
          : 'bg-emerald-500/20 border border-emerald-500/30',
      )}>
        {isDuplicate ? '⚠️' : '✅'}
      </div>
      <div>
        <p className="text-base font-semibold text-slate-100">
          {isDuplicate ? 'CV ya registrado' : '¡CV agregado al banco!'}
        </p>
        <p className="text-sm text-slate-500 mt-1">{result.message}</p>
      </div>
      <button
        type="button"
        onClick={onReset}
        className="bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-all"
      >
        Cargar otro CV
      </button>
    </div>
  )
}

// ── Success card (bulk upload) ────────────────────────────────────────────────

function BulkSuccessCard({ result, onReset }: { result: BulkUploadResponse; onReset: () => void }) {
  const total = result.added + result.duplicates + result.failed
  return (
    <div className="text-center space-y-5 py-6">
      <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-3xl mx-auto">
        ✅
      </div>
      <div>
        <p className="text-base font-semibold text-slate-100">
          {total === 1 ? '1 archivo procesado' : `${total} archivos procesados`}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl py-3">
          <p className="text-2xl font-bold text-emerald-400">{result.added}</p>
          <p className="text-xs text-slate-500 mt-0.5">agregados</p>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl py-3">
          <p className="text-2xl font-bold text-amber-400">{result.duplicates}</p>
          <p className="text-xs text-slate-500 mt-0.5">duplicados</p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl py-3">
          <p className="text-2xl font-bold text-red-400">{result.failed}</p>
          <p className="text-xs text-slate-500 mt-0.5">fallidos</p>
        </div>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-all"
      >
        Cargar más CVs
      </button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const [files, setFiles]                   = useState<File[]>([])
  const [draft, setDraft]                   = useState<ContactDraft | null>(null)
  const [missingFields, setMissingFields]   = useState<string[]>([])
  const [hash, setHash]                     = useState('')

  const extract    = useExtractContact()
  const upload     = useUploadCV()
  const bulkUpload = useBulkUploadCVs()

  // Called when the user clicks "Extraer datos" in single-file mode.
  function handleExtract() {
    if (files.length !== 1) return
    extract.mutate(files[0], {
      onSuccess(data) {
        setDraft(extractedToContactDraft(data.extracted_contact))
        setMissingFields(data.missing_fields)
        setHash(data.extracted_text_hash)
      },
    })
  }

  // Called when the user confirms contact data in single-file mode.
  function handleSingleSubmit() {
    if (!files[0] || !draft) return
    upload.mutate({ file: files[0], contactInfo: toContactInfo(draft), expectedHash: hash })
  }

  // Called when the user clicks "Subir CVs" in multi-file mode.
  function handleBulkSubmit() {
    if (files.length < 2) return
    bulkUpload.mutate(files)
  }

  function resetAll() {
    setFiles([])
    setDraft(null)
    setMissingFields([])
    setHash('')
    extract.reset()
    upload.reset()
    bulkUpload.reset()
  }

  // ── Loading screens ──────────────────────────────────────────────────────────
  if (extract.isPending)    return <LoadingScreen text="Analizando CV…" />
  if (upload.isPending)     return <LoadingScreen text="Guardando CV…" />
  if (bulkUpload.isPending) return <LoadingScreen text={`Subiendo ${files.length} CVs…`} />

  // ── Success screens ──────────────────────────────────────────────────────────
  if (upload.isSuccess) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
        <div className="max-w-lg mx-auto bg-[#111118] border border-slate-800 rounded-2xl p-8">
          <SuccessCard result={upload.data} onReset={resetAll} />
        </div>
      </div>
    )
  }

  if (bulkUpload.isSuccess) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
        <div className="max-w-lg mx-auto bg-[#111118] border border-slate-800 rounded-2xl p-8">
          <BulkSuccessCard result={bulkUpload.data} onReset={resetAll} />
        </div>
      </div>
    )
  }

  // ── Extract error ────────────────────────────────────────────────────────────
  if (extract.isError) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-[#111118] border border-red-500/30 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-red-400">No se pudo leer el archivo</h2>
          <p className="text-sm text-slate-400">{getErrorMessage(extract.error)}</p>
          <button
            onClick={resetAll}
            className="text-sm bg-slate-800 text-slate-300 border border-slate-700 px-4 py-2 rounded-lg hover:bg-slate-700 transition-colors"
          >
            ← Volver
          </button>
        </div>
      </div>
    )
  }

  // ── Determine current state ──────────────────────────────────────────────────
  const isSingleFlow = files.length === 1
  const isMultiFlow  = files.length > 1
  const step: 1 | 2  = isSingleFlow && draft ? 2 : 1

  return (
    <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-xl font-bold text-slate-100 mb-6">Cargar CV al banco</h1>

        <div className="bg-[#111118] border border-slate-800 rounded-2xl p-6">
          {/* Step indicator only shows in single-file flow */}
          {isSingleFlow && <StepIndicator step={step} />}

          {/* Step 1: file picker (always shown unless in single-file step 2) */}
          {step === 1 && (
            <div className="space-y-4">
              <MultiFilePicker files={files} onFiles={setFiles as (files: File[] | ((prev: File[]) => File[])) => void} />

              {/* Single-file CTA */}
              {isSingleFlow && (
                <button
                  type="button"
                  onClick={handleExtract}
                  className="w-full bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600 text-white font-semibold py-2.5 rounded-xl transition-all"
                >
                  Extraer datos del CV →
                </button>
              )}

              {/* Multi-file CTA */}
              {isMultiFlow && (
                <button
                  type="button"
                  onClick={handleBulkSubmit}
                  className="w-full bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600 text-white font-semibold py-2.5 rounded-xl transition-all"
                >
                  Subir {files.length} CVs
                </button>
              )}

              {/* No files selected */}
              {files.length === 0 && (
                <button
                  type="button"
                  disabled
                  className="w-full bg-slate-700 text-slate-500 font-semibold py-2.5 rounded-xl cursor-not-allowed"
                >
                  Seleccioná archivos para continuar
                </button>
              )}

              {bulkUpload.isError && (
                <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5">
                  {getErrorMessage(bulkUpload.error)}
                </p>
              )}
            </div>
          )}

          {/* Step 2: contact form (single-file flow only) */}
          {step === 2 && draft && (
            <ContactForm
              draft={draft}
              missingFields={missingFields}
              onChange={setDraft}
              onSubmit={handleSingleSubmit}
              onBack={resetAll}
              isSubmitting={upload.isPending}
              submitError={upload.isError ? getErrorMessage(upload.error) : null}
            />
          )}
        </div>
      </div>
    </div>
  )
}
