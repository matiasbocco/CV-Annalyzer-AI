import { useEffect, useRef, useState } from 'react'
import { X, Copy } from 'lucide-react'
import { useCvText } from '../api/hooks'
import { formatCvText } from '../lib/formatCvText'
import { T, useLang } from '../LangContext'

interface Props {
  cvId: string
  filename: string
  onClose: () => void
}

export default function CvTextModal({ cvId, filename, onClose }: Props) {
  const t = T[useLang()]
  const { data, isLoading, isError } = useCvText(cvId)
  const [copied, setCopied] = useState(false)
  const backdropRef = useRef<HTMLDivElement>(null)

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  // Prevent body scroll while modal is open
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [])

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === backdropRef.current) onClose()
  }

  async function handleCopy() {
    if (!data?.text_content) return
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(data.text_content)
      } else {
        const el = document.createElement('textarea')
        el.value = data.text_content
        el.style.cssText = 'position:fixed;opacity:0;pointer-events:none'
        document.body.appendChild(el)
        el.focus()
        el.select()
        document.execCommand('copy')
        document.body.removeChild(el)
      }
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard unavailable */ }
  }

  const blocks = data ? formatCvText(data.text_content) : []

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdropClick}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        style={{
          background: '#111118',
          border: '1px solid #1e293b',
          borderRadius: 16,
          width: '100%',
          maxWidth: 680,
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.25rem',
            borderBottom: '1px solid #1e293b',
            flexShrink: 0,
          }}
        >
          <div>
            <p style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0', margin: 0 }}>
              {t.viewCv}
            </p>
            <p style={{ fontSize: 11, color: '#475569', margin: '2px 0 0', fontFamily: 'monospace' }}>
              {filename}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {data && (
              <button
                type="button"
                onClick={handleCopy}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '5px 12px',
                  borderRadius: 9999,
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: 'pointer',
                  background: copied ? '#14532d' : '#1e2a3d',
                  border: `1px solid ${copied ? '#16a34a40' : '#2a3447'}`,
                  color: copied ? '#4ade80' : '#94a3b8',
                  transition: 'all 0.15s',
                }}
              >
                <Copy size={13} strokeWidth={1.75} />
                {copied ? t.copiedText : t.copyFullText}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label={t.closeModal}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 30,
                height: 30,
                borderRadius: '50%',
                background: 'transparent',
                border: '1px solid #2a3447',
                color: '#64748b',
                cursor: 'pointer',
              }}
            >
              <X size={15} strokeWidth={2} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ overflowY: 'auto', padding: '1.25rem', flex: 1 }}>
          {isLoading && (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: '#475569' }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  border: '2.5px solid #1e293b',
                  borderTopColor: '#38bdf8',
                  borderRadius: '50%',
                  animation: 'cvmodal-spin 0.7s linear infinite',
                  margin: '0 auto 12px',
                }}
              />
              <style>{`@keyframes cvmodal-spin { to { transform: rotate(360deg); } }`}</style>
              <p style={{ fontSize: 13, margin: 0 }}>Cargando CV…</p>
            </div>
          )}

          {isError && (
            <div
              style={{
                background: '#1c1215',
                border: '1px solid #7f1d1d40',
                borderRadius: 10,
                padding: '1rem',
                color: '#f87171',
                fontSize: 13,
              }}
            >
              {t.cvLoadError}
            </div>
          )}

          {!isLoading && !isError && blocks.length === 0 && (
            <p style={{ fontSize: 13, color: '#475569', textAlign: 'center', padding: '2rem 0' }}>
              {t.cvLoadError}
            </p>
          )}

          {blocks.map((block, i) =>
            block.type === 'header' ? (
              <h4
                key={i}
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#38bdf8',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  margin: i === 0 ? '0 0 10px' : '22px 0 10px',
                }}
              >
                {block.text}
              </h4>
            ) : (
              <p
                key={i}
                style={{
                  fontSize: 13,
                  color: '#cbd5e1',
                  lineHeight: 1.65,
                  whiteSpace: 'pre-wrap',
                  margin: '0 0 12px',
                }}
              >
                {block.text}
              </p>
            ),
          )}
        </div>
      </div>
    </div>
  )
}
