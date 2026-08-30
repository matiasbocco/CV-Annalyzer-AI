import { useEffect, useState } from 'react'
import { BrainCircuit } from 'lucide-react'
import { getUser } from '../auth'

export default function WelcomeScreen() {
  const [visible, setVisible] = useState(false)
  const [fading, setFading] = useState(false)
  const user = getUser()

  // Key is scoped to the user ID so each user gets their own welcome screen
  // even if they log in on the same tab without closing it.
  const sessionKey = `welcome_shown_${user?.id ?? 'anon'}`

  useEffect(() => {
    if (sessionStorage.getItem(sessionKey)) return
    setVisible(true)
    const timer = setTimeout(() => dismiss(), 4000)
    return () => clearTimeout(timer)
  // sessionKey is stable within a mount — user is set before WelcomeScreen renders
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function dismiss() {
    setFading(true)
    setTimeout(() => {
      sessionStorage.setItem(sessionKey, '1')
      setVisible(false)
    }, 400)
  }

  if (!visible) return null

  // Prefer stored first_name; fall back to extracting from email
  const firstName = user?.first_name
    ?? (() => {
      const raw = user?.email?.split('@')[0]?.split('.')[0] ?? 'recruiter'
      return raw.charAt(0).toUpperCase() + raw.slice(1)
    })()

  return (
    <>
      <style>{`
        @keyframes ws-glow {
          0%, 100% { opacity: 0.35; transform: translate(-50%, -50%) scale(1); }
          50%       { opacity: 0.7;  transform: translate(-50%, -50%) scale(1.18); }
        }
        @keyframes ws-fadeup {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .ws-item {
          animation: ws-fadeup 0.55s ease both;
          opacity: 0;
        }
        .ws-overlay {
          transition: opacity 0.4s ease;
        }
      `}</style>

      <div
        className="ws-overlay"
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 9999,
          background: '#0f1117',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: fading ? 0 : 1,
        }}
      >
        {/* Pulsing radial glow */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: 340,
            height: 340,
            background: 'radial-gradient(circle, #3b82f628 0%, transparent 70%)',
            animation: 'ws-glow 3s ease-in-out infinite',
            pointerEvents: 'none',
            borderRadius: '50%',
          }}
        />

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 20,
            textAlign: 'center',
            padding: '0 24px',
          }}
        >
          {/* a) Logo icon */}
          <div className="ws-item" style={{ animationDelay: '0ms' }}>
            <div
              style={{
                width: 64,
                height: 64,
                background: 'linear-gradient(135deg, #1d4ed8, #0ea5e9)',
                borderRadius: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 40px #3b82f630',
              }}
            >
              <BrainCircuit size={32} color="white" />
            </div>
          </div>

          {/* b) App name */}
          <div className="ws-item" style={{ animationDelay: '200ms', marginTop: -4 }}>
            <p style={{ fontSize: 26, fontWeight: 500, color: '#e2e8f0', margin: 0 }}>
              CV Analyzer <span style={{ color: '#38bdf8' }}>AI</span>
            </p>
          </div>

          {/* c) Tagline */}
          <div className="ws-item" style={{ animationDelay: '400ms', marginTop: -12 }}>
            <p style={{ fontSize: 13, color: '#475569', margin: 0 }}>
              Screening inteligente de candidatos
            </p>
          </div>

          {/* d+e) Greeting + name */}
          <div
            className="ws-item"
            style={{
              animationDelay: '600ms',
              marginTop: 8,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <p style={{ fontSize: 15, color: '#94a3b8', margin: 0 }}>
              Bienvenido de vuelta,
            </p>
            <p style={{ fontSize: 28, fontWeight: 500, color: '#60a5fa', margin: 0 }}>
              {user?.last_name ? `${firstName} ${user.last_name}` : firstName}
            </p>
          </div>

          {/* f) Button */}
          <div className="ws-item" style={{ animationDelay: '800ms', marginTop: 8 }}>
            <button
              onClick={dismiss}
              style={{
                background: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: 10,
                padding: '10px 28px',
                fontSize: 14,
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'background 0.15s, transform 0.15s',
              }}
              onMouseEnter={e => {
                ;(e.currentTarget as HTMLButtonElement).style.background = '#1d4ed8'
                ;(e.currentTarget as HTMLButtonElement).style.transform = 'scale(1.02)'
              }}
              onMouseLeave={e => {
                ;(e.currentTarget as HTMLButtonElement).style.background = '#2563eb'
                ;(e.currentTarget as HTMLButtonElement).style.transform = 'scale(1)'
              }}
            >
              Ingresar al sistema →
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
