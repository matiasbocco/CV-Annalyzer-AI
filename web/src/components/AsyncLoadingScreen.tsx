import { useEffect, useState } from 'react'
import { FileText, Search, Clock, MessageSquare, Database } from 'lucide-react'
import { cn } from '../lib/utils'

// ── Step definitions ──────────────────────────────────────────────────────────

const ANALYZE_STEPS = (fileCount: number) => [
  {
    icon: <FileText size={18} />,
    label: 'Extrayendo texto de los CVs',
    description: `${fileCount} archivo${fileCount !== 1 ? 's' : ''} procesado${fileCount !== 1 ? 's' : ''} correctamente`,
  },
  {
    icon: <Search size={18} />,
    label: 'Buscando candidatos similares en el banco',
    description: 'Comparando embeddings semánticos...',
  },
  {
    icon: <Clock size={18} />,
    label: 'Analizando con IA',
    description: 'Nuestra IA evaluará a los candidatos',
  },
  {
    icon: <MessageSquare size={18} />,
    label: 'Generando ranking y análisis',
    description: 'Scores, fortalezas y recomendaciones',
  },
  {
    icon: <Database size={18} />,
    label: 'Guardando resultados',
    description: 'Persistiendo en la base de datos',
  },
]

const MATCH_STEPS = [
  {
    icon: <FileText size={18} />,
    label: 'Procesando descripción del puesto',
    description: 'Generando embeddings semánticos...',
  },
  {
    icon: <Search size={18} />,
    label: 'Buscando en el banco de CVs',
    description: 'Comparando con todos los candidatos...',
  },
  {
    icon: <MessageSquare size={18} />,
    label: 'Generando ranking',
    description: 'Analizando compatibilidad...',
  },
]

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  mode: 'analyze' | 'match'
  fileCount?: number
}

export default function AsyncLoadingScreen({ mode, fileCount = 0 }: Props) {
  const steps = mode === 'analyze' ? ANALYZE_STEPS(fileCount) : MATCH_STEPS
  const totalSeconds = mode === 'analyze' ? 40 : 30

  const [step, setStep] = useState(0)
  const [seconds, setSeconds] = useState(totalSeconds)

  useEffect(() => {
    const stepTimer = setInterval(
      () => setStep(p => Math.min(p + 1, steps.length - 1)),
      8000,
    )
    return () => clearInterval(stepTimer)
  }, [steps.length])

  useEffect(() => {
    if (seconds <= 0) return
    const tick = setInterval(() => setSeconds(s => Math.max(0, s - 1)), 1000)
    return () => clearInterval(tick)
  }, [seconds])

  const progressPct = Math.round(((step + 1) / steps.length) * 100)

  return (
    <>
      <style>{`
        @keyframes als-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.5; transform: scale(0.85); }
        }
        .als-dot {
          animation: als-pulse 1s ease-in-out infinite;
        }
        .als-progress-bar {
          transition: width 0.8s ease;
        }
        @keyframes als-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>

      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-[#111118] border border-slate-800 rounded-2xl p-8 space-y-7">

          {/* Header */}
          <div className="text-center space-y-1.5">
            <p style={{ fontSize: 18, color: '#e2e8f0', fontWeight: 600, margin: 0 }}>
              {mode === 'analyze' ? 'Analizando candidatos...' : 'Buscando candidatos...'}
            </p>
            <p style={{ fontSize: 13, color: '#64748b', margin: 0 }}>
              Esto puede tomar entre {mode === 'analyze' ? '15 y 40' : '10 y 30'} segundos
            </p>
          </div>

          {/* Steps */}
          <div className="space-y-1">
            {steps.map((s, i) => {
              const isDone   = i < step
              const isActive = i === step
              const isPending = i > step

              return (
                <div key={i} className="flex gap-3">
                  {/* Left: icon + connector */}
                  <div className="flex flex-col items-center" style={{ width: 40, flexShrink: 0 }}>
                    {/* Icon circle */}
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        transition: 'all 0.4s ease',
                        ...(isDone
                          ? { background: '#1a3d2a', border: '1.5px solid #16a34a' }
                          : isActive
                          ? { background: '#1e3a5f', border: '1.5px solid #3b82f6' }
                          : { background: '#161b27', border: '1.5px solid #2a3447' }),
                      }}
                    >
                      <span
                        style={{
                          color: isDone ? '#4ade80' : isActive ? 'white' : '#334155',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'color 0.3s',
                        }}
                      >
                        {s.icon}
                      </span>
                    </div>
                    {/* Connector line */}
                    {i < steps.length - 1 && (
                      <div
                        style={{
                          width: 1.5,
                          flex: 1,
                          minHeight: 16,
                          marginTop: 4,
                          background: isDone ? '#16a34a40' : '#2a3447',
                          transition: 'background 0.4s',
                        }}
                      />
                    )}
                  </div>

                  {/* Right: text + status */}
                  <div
                    className={cn('flex-1 flex items-start justify-between pb-4', i === steps.length - 1 && 'pb-0')}
                    style={{ paddingTop: 8 }}
                  >
                    <div>
                      <p
                        style={{
                          fontSize: 14,
                          fontWeight: 500,
                          margin: 0,
                          transition: 'color 0.3s',
                          color: isDone ? '#4ade80' : isActive ? 'white' : '#334155',
                        }}
                      >
                        {s.label}
                      </p>
                      <p
                        style={{
                          fontSize: 12,
                          margin: '3px 0 0',
                          color: isDone ? '#16a34a80' : isActive ? '#64748b' : '#1e2a3a',
                          transition: 'color 0.3s',
                        }}
                      >
                        {s.description}
                      </p>
                    </div>

                    {/* Status indicator */}
                    <div style={{ paddingTop: 10, paddingLeft: 8, flexShrink: 0 }}>
                      {isDone && (
                        <span style={{ color: '#4ade80', fontSize: 16, fontWeight: 700 }}>✓</span>
                      )}
                      {isActive && (
                        <span
                          className="als-dot"
                          style={{
                            display: 'block',
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: '#3b82f6',
                          }}
                        />
                      )}
                      {isPending && (
                        <span
                          style={{
                            display: 'block',
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            background: '#2a3447',
                          }}
                        />
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <div
              style={{
                height: 4,
                background: '#1e293b',
                borderRadius: 9999,
                overflow: 'hidden',
              }}
            >
              <div
                className="als-progress-bar"
                style={{
                  height: '100%',
                  width: `${progressPct}%`,
                  background: 'linear-gradient(90deg, #2563eb, #0ea5e9)',
                  borderRadius: 9999,
                }}
              />
            </div>
            <div className="flex justify-between">
              <span style={{ fontSize: 11, color: '#475569' }}>
                Paso {step + 1} de {steps.length}
              </span>
              <span style={{ fontSize: 11, color: '#475569' }}>
                ~{seconds} segundo{seconds !== 1 ? 's' : ''} restante{seconds !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
