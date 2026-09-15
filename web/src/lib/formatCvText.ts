export type CvTextBlock =
  | { type: 'header'; text: string }
  | { type: 'paragraph'; text: string }

const SECTION_KEYWORDS = [
  'experiencia', 'experiencia laboral', 'formación académica',
  'formación', 'educación', 'estudios', 'habilidades', 'competencias',
  'idiomas', 'certificaciones', 'perfil profesional',
  'objetivo profesional', 'resumen', 'contacto', 'referencias',
  'proyectos', 'logros', 'reconocimientos', 'voluntariado', 'cursos',
  'experience', 'education', 'skills', 'languages', 'certifications',
  'summary', 'profile', 'projects', 'achievements', 'references',
  'contact', 'objective', 'work experience', 'professional experience',
]

function isLikelyHeader(line: string): boolean {
  const trimmed = line.trim()
  if (trimmed.length < 2 || trimmed.length > 40) return false
  const lower = trimmed.toLowerCase().replace(/[:：]\s*$/, '')
  if (SECTION_KEYWORDS.includes(lower)) return true
  // Todo en mayúsculas (permitiendo espacios, acentos y algunos signos)
  const letters = trimmed.replace(/[^a-zA-ZÀ-ÿ]/g, '')
  if (letters.length >= 3 && letters === letters.toUpperCase() && letters !== letters.toLowerCase()) {
    return true
  }
  return false
}

export function formatCvText(raw: string): CvTextBlock[] {
  const lines = raw.split('\n')
  const blocks: CvTextBlock[] = []
  let currentParagraph: string[] = []

  function flushParagraph() {
    const text = currentParagraph.join('\n').trim()
    if (text) blocks.push({ type: 'paragraph', text })
    currentParagraph = []
  }

  for (const line of lines) {
    if (line.trim() === '') {
      flushParagraph()
      continue
    }
    if (isLikelyHeader(line)) {
      flushParagraph()
      blocks.push({ type: 'header', text: line.trim() })
    } else {
      currentParagraph.push(line)
    }
  }
  flushParagraph()
  return blocks
}
