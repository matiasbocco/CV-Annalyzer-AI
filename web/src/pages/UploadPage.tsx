import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useExtractContact, useUploadCV } from '../api/hooks'
import type { ContactInfo, UploadResponse } from '../api/types'
import { cn, getErrorMessage } from '../lib/utils'
import LoadingScreen from '../components/LoadingScreen'

// ── Types ─────────────────────────────────────────────────────────────────────

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

const AVAILABILITY_LABELS: Record<string, string> = {
  available:   'Disponible activamente',
  open:        'Abierto a oportunidades',
  not_looking: 'No disponible',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function toContactInfo(draft: ContactDraft): Partial<ContactInfo> {
  const out: Partial<ContactInfo> = {}
  if (draft.full_name.trim())    out.full_name    = draft.full_name.trim()
  if (draft.email.trim())        out.email        = draft.email.trim()
  if (draft.phone.trim())        out.phone        = draft.phone.trim()
  if (draft.linkedin_url.trim()) out.linkedin_url = draft.linkedin_url.trim()
  if (draft.github_url.trim())   out.github_url   = draft.github_url.trim()
  if (draft.portfolio_url.trim())out.portfolio_url= draft.portfolio_url.trim()
  if (draft.location.trim())     out.location     = draft.location.trim()
  if (draft.availability)        out.availability = draft.availability as ContactInfo['availability']
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

// ── Step indicator ────────────────────────────────────────────────────────────

function StepIndicator({ step }: { step: 1 | 2 }) {
  return (
    <div className="flex items-center gap-2 mb-6">
      {[1, 2].map((n) => (
        <div key={n} className="flex items-center gap-2">
          <div className={cn(
            'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold',
            step === n
              ? 'bg-blue-600 text-white'
              : step > n
                ? 'bg-green-500 text-white'
                : 'bg-gray-200 text-gray-500',
          )}>
            {step > n ? '✓' : n}
          </div>
          <span className={cn(
            'text-sm',
            step === n ? 'text-gray-900 font-medium' : 'text-gray-400',
          )}>
            {n === 1 ? 'Seleccionar archivo' : 'Confirmar datos'}
          </span>
          {n < 2 && <span className="text-gray-300 mx-1">→</span>}
        </div>
      ))}
    </div>
  )
}

// ── Step 1 — File picker ──────────────────────────────────────────────────────

function FilePicker({ onFile }: { onFile: (f: File) => void }) {
  const [file, setFile] = useState<File | null>(null)

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
    },
    multiple: false,
  })

  return (
    <div className="space-y-5">
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400',
        )}
      >
        <input {...getInputProps()} />
        <p className="text-3xl mb-2">📄</p>
        <p className="text-sm font-medium text-gray-700">
          {isDragActive ? 'Soltá el archivo aquí…' : 'Arrastrá tu CV aquí, o hacé clic para seleccionar'}
        </p>
        <p className="text-xs text-gray-400 mt-1">PDF, DOCX, JPG, PNG o WEBP</p>
      </div>

      {file && (
        <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <span className="text-sm text-gray-700 truncate">{file.name}</span>
          <button
            type="button"
            onClick={() => setFile(null)}
            className="ml-3 text-gray-400 hover:text-red-500 flex-shrink-0 text-lg leading-none"
          >
            ×
          </button>
        </div>
      )}

      <button
        type="button"
        disabled={!file}
        onClick={() => file && onFile(file)}
        className="w-full bg-blue-600 text-white font-semibold py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Extraer datos del CV →
      </button>
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

  function field(
    key: keyof ContactDraft,
    label: string,
    placeholder?: string,
    required?: boolean,
  ) {
    const isMissing = missing.has(key)
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
          {isMissing && !draft[key] && (
            <span className="ml-2 text-xs font-normal text-amber-600">requerido</span>
          )}
        </label>
        <input
          type="text"
          value={draft[key]}
          onChange={e => onChange({ ...draft, [key]: e.target.value })}
          placeholder={placeholder}
          className={cn(
            'w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400',
            isMissing && !draft[key]
              ? 'border-amber-400 bg-amber-50'
              : 'border-gray-300',
          )}
        />
      </div>
    )
  }

  const canSubmit = draft.full_name.trim() && draft.email.trim()

  return (
    <div className="space-y-4">
      {missingFields.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
          Completá los campos marcados para que el sistema pueda contactarte.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {field('full_name',  'Nombre completo',  'Juan García',       true)}
        {field('email',      'Email',             'juan@ejemplo.com',  true)}
        {field('phone',      'Teléfono',          '+54 9 11 …')}
        {field('location',   'Ubicación',         'Buenos Aires, Argentina')}
        {field('linkedin_url', 'LinkedIn',        'https://linkedin.com/in/…')}
        {field('github_url',   'GitHub',          'https://github.com/…')}
        {field('portfolio_url','Portfolio / Sitio web', 'https://…')}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Disponibilidad
          {missing.has('availability') && !draft.availability && (
            <span className="ml-2 text-xs font-normal text-amber-600">requerido</span>
          )}
        </label>
        <select
          value={draft.availability}
          onChange={e => onChange({ ...draft, availability: e.target.value })}
          className={cn(
            'w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400 bg-white',
            missing.has('availability') && !draft.availability
              ? 'border-amber-400 bg-amber-50'
              : 'border-gray-300',
          )}
        >
          <option value="">Sin especificar</option>
          <option value="available">Disponible activamente</option>
          <option value="open">Abierto a oportunidades</option>
          <option value="not_looking">No disponible</option>
        </select>
      </div>

      {submitError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {submitError}
        </p>
      )}

      <div className="flex gap-3 pt-1">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 text-sm text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          ← Volver
        </button>
        <button
          type="button"
          disabled={!canSubmit || isSubmitting}
          onClick={onSubmit}
          className="flex-1 bg-blue-600 text-white font-semibold py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? 'Guardando…' : 'Guardar CV'}
        </button>
      </div>
    </div>
  )
}

// ── Success card ──────────────────────────────────────────────────────────────

function SuccessCard({
  result,
  onReset,
}: {
  result: UploadResponse
  onReset: () => void
}) {
  const isDuplicate = result.status === 'duplicate'
  return (
    <div className="text-center space-y-4 py-6">
      <div className={cn(
        'w-16 h-16 rounded-full flex items-center justify-center text-3xl mx-auto',
        isDuplicate ? 'bg-yellow-100' : 'bg-green-100',
      )}>
        {isDuplicate ? '⚠️' : '✅'}
      </div>
      <div>
        <p className="text-lg font-semibold text-gray-900">
          {isDuplicate ? 'CV ya registrado' : '¡CV agregado al banco!'}
        </p>
        <p className="text-sm text-gray-500 mt-1">{result.message}</p>
      </div>
      <button
        type="button"
        onClick={onReset}
        className="bg-blue-600 text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-700"
      >
        Cargar otro CV
      </button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const [file, setFile]         = useState<File | null>(null)
  const [draft, setDraft]       = useState<ContactDraft | null>(null)
  const [missingFields, setMissingFields] = useState<string[]>([])
  const [hash, setHash]         = useState('')

  const extract = useExtractContact()
  const upload  = useUploadCV()

  function handleFile(f: File) {
    setFile(f)
    extract.mutate(f, {
      onSuccess(data) {
        setDraft(extractedToContactDraft(data.extracted_contact))
        setMissingFields(data.missing_fields)
        setHash(data.extracted_text_hash)
      },
    })
  }

  function handleSubmit() {
    if (!file || !draft) return
    upload.mutate({ file, contactInfo: toContactInfo(draft), expectedHash: hash })
  }

  function resetAll() {
    setFile(null)
    setDraft(null)
    setMissingFields([])
    setHash('')
    extract.reset()
    upload.reset()
  }

  // ── Loading states ─────────────────────────────────────────────────────────

  if (extract.isPending) return <LoadingScreen text="Analizando CV…" />
  if (upload.isPending)  return <LoadingScreen text="Guardando CV…" />

  // ── Success ────────────────────────────────────────────────────────────────

  if (upload.isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-lg mx-auto bg-white border border-gray-200 rounded-lg p-8">
          <SuccessCard result={upload.data} onReset={resetAll} />
        </div>
      </div>
    )
  }

  // ── Error on extract ───────────────────────────────────────────────────────

  if (extract.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white border border-red-200 rounded-lg p-6 space-y-4">
          <h2 className="text-lg font-semibold text-red-700">No se pudo leer el archivo</h2>
          <p className="text-sm text-gray-600">{getErrorMessage(extract.error)}</p>
          <button
            onClick={resetAll}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            ← Volver
          </button>
        </div>
      </div>
    )
  }

  // ── Main shell ─────────────────────────────────────────────────────────────

  const step: 1 | 2 = draft ? 2 : 1

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Cargar CV al banco</h1>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <StepIndicator step={step} />

          {step === 1 && <FilePicker onFile={handleFile} />}

          {step === 2 && draft && (
            <ContactForm
              draft={draft}
              missingFields={missingFields}
              onChange={setDraft}
              onSubmit={handleSubmit}
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
