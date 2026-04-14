/**
 * PptxGenJS-based PPTX export for the AI PPT Generator.
 * Converts editor slides → professional PPTX with rich formatting and slide transitions.
 */
import PptxGenJS from 'pptxgenjs'
import JSZip from 'jszip'

// ─── Transition name map (editor → PptxGenJS) ──────
const TRANSITION_MAP = {
  'fade': { effect: 'fade' },
  'slide-left': { effect: 'push', dir: 'l' },
  'slide-right': { effect: 'push', dir: 'r' },
  'slide-up': { effect: 'push', dir: 'u' },
  'slide-down': { effect: 'push', dir: 'd' },
  'zoom-in': { effect: 'zoom' },
  'scale-fade': { effect: 'fade' },
  'flip': { effect: 'fade' },
  'push': { effect: 'push', dir: 'l' },
  'dissolve': { effect: 'dissolve' },
  'wipe': { effect: 'wipe', dir: 'l' },
  'cover': { effect: 'cover', dir: 'l' },
  'none': { effect: 'none' },
}

// ─── Helpers ────────────────────────────────────────
function hexToRgb(hex) {
  if (!hex || typeof hex !== 'string') return '000000'
  const clean = hex.replace('#', '')
  if (clean.length === 6) return clean.toUpperCase()
  return '000000'
}

function parseColor(colorStr) {
  if (!colorStr) return { color: '000000', transparency: 0 }
  if (colorStr.startsWith('rgba')) {
    const m = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/)
    if (m) {
      const r = parseInt(m[1]).toString(16).padStart(2, '0')
      const g = parseInt(m[2]).toString(16).padStart(2, '0')
      const b = parseInt(m[3]).toString(16).padStart(2, '0')
      const a = m[4] !== undefined ? parseFloat(m[4]) : 1.0
      return { color: (r + g + b).toUpperCase(), transparency: Math.round((1 - a) * 100) }
    }
  }
  if (colorStr.startsWith('#')) {
    return { color: hexToRgb(colorStr), transparency: 0 }
  }
  return { color: '000000', transparency: 0 }
}

function pxToInches(px) { return px / 96 }
function canvasToInches(px, scale) { return px * scale }

function parseNumericStats(slideData) {
  const contentStats = slideData?.content?.stats
  if (!Array.isArray(contentStats)) return { labels: [], values: [] }
  const labels = []
  const values = []
  contentStats.slice(0, 6).forEach((s, idx) => {
    if (!s || typeof s !== 'object') return
    const label = String(s.label || `Metric ${idx + 1}`).trim()
    const raw = String(s.value || '').match(/-?\d+(\.\d+)?/)
    if (!raw) return
    const num = Number(raw[0])
    if (Number.isNaN(num)) return
    labels.push(label)
    values.push(num)
  })
  return { labels, values }
}

// ─── Alignment map ──────────────────────────────────
const ALIGN_MAP = { left: 'left', center: 'center', right: 'right' }

function toTransitionSpeed(duration) {
  if (duration <= 0.3) return 'fast'
  if (duration >= 1.5) return 'slow'
  return 'med'
}

function normalizeTransition(transition) {
  const fallback = { type: 'fade', duration: 0.5 }
  const tr = transition && typeof transition === 'object' ? transition : fallback
  const duration = Number.isFinite(tr.duration) ? tr.duration : fallback.duration
  const mapped = TRANSITION_MAP[tr.type] || TRANSITION_MAP.fade
  return {
    effect: mapped.effect,
    dir: mapped.dir,
    speed: toTransitionSpeed(duration),
  }
}

function stripTransitionXml(slideXml) {
  return slideXml
    .replace(/<p:transition\b[^>]*\/>/g, '')
    .replace(/<p:transition\b[^>]*>[\s\S]*?<\/p:transition>/g, '')
}

function buildTransitionXml(transition) {
  if (!transition || transition.effect === 'none') return ''
  const commonAttrs = `spd="${transition.speed}" advClick="1"`

  if (transition.effect === 'push') return `<p:transition ${commonAttrs}><p:push dir="${transition.dir || 'l'}"/></p:transition>`
  if (transition.effect === 'wipe') return `<p:transition ${commonAttrs}><p:wipe dir="${transition.dir || 'l'}"/></p:transition>`
  if (transition.effect === 'cover') return `<p:transition ${commonAttrs}><p:cover dir="${transition.dir || 'l'}"/></p:transition>`
  if (transition.effect === 'dissolve') return `<p:transition ${commonAttrs}><p:dissolve/></p:transition>`
  if (transition.effect === 'zoom') return `<p:transition ${commonAttrs}><p:zoom/></p:transition>`
  return `<p:transition ${commonAttrs}><p:fade/></p:transition>`
}

function injectTransitionXml(slideXml, transitionXml) {
  const cleanedXml = stripTransitionXml(slideXml)
  if (!transitionXml) return cleanedXml
  if (cleanedXml.includes('<p:clrMapOvr>')) {
    return cleanedXml.replace('<p:clrMapOvr>', `${transitionXml}<p:clrMapOvr>`)
  }
  if (cleanedXml.includes('</p:sld>')) {
    return cleanedXml.replace('</p:sld>', `${transitionXml}</p:sld>`)
  }
  return cleanedXml
}

async function applyNativeTransitions(pptxArrayBuffer, slides) {
  const zip = await JSZip.loadAsync(pptxArrayBuffer)
  let anyPatched = false

  for (let i = 0; i < slides.length; i++) {
    const slidePath = `ppt/slides/slide${i + 1}.xml`
    const slideFile = zip.file(slidePath)
    if (!slideFile) continue

    const xml = await slideFile.async('string')
    const transition = normalizeTransition(slides[i]?.transition)
    const transitionXml = buildTransitionXml(transition)
    const updatedXml = injectTransitionXml(xml, transitionXml)

    if (updatedXml !== xml) {
      zip.file(slidePath, updatedXml)
      anyPatched = true
    }
  }

  if (!anyPatched) {
    return new Blob([pptxArrayBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })
  }
  return zip.generateAsync({
    type: 'blob',
    mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  })
}

function downloadBlob(blob, fileName) {
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

function toAbsoluteUrl(src) {
  try {
    return new URL(src, window.location.origin).toString()
  } catch {
    return src
  }
}

function isSameOriginUrl(src) {
  try {
    const u = new URL(src, window.location.origin)
    return u.origin === window.location.origin
  } catch {
    return false
  }
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

async function resolveImageSource(src) {
  if (!src || typeof src !== 'string') return null
  if (src.startsWith('data:')) return { data: src }

  const absolute = toAbsoluteUrl(src)
  const sameOrigin = isSameOriginUrl(absolute)

  // Prefer embedding as data URL so export does not fail on remote image fetch at write time.
  try {
    const response = await fetch(absolute, {
      mode: sameOrigin ? 'same-origin' : 'cors',
      credentials: sameOrigin ? 'include' : 'omit',
    })
    if (response.ok) {
      const blob = await response.blob()
      const dataUrl = await blobToDataUrl(blob)
      if (typeof dataUrl === 'string' && dataUrl.startsWith('data:')) {
        return { data: dataUrl }
      }
    }
  } catch {
    // Ignore and try a safe fallback below.
  }

  // For same-origin images, path fallback is usually safe.
  if (sameOrigin || src.startsWith('/')) {
    return { path: absolute }
  }

  // Skip external images that cannot be fetched due CORS/network.
  return null
}

// ─── Main export function ───────────────────────────
export async function exportToPptx(slides, title, theme) {
  const pptx = new PptxGenJS()
  pptx.author = 'AI PPT Generator'
  pptx.title = title || 'Presentation'
  pptx.subject = title || 'AI Generated Presentation'

  // Set slide dimensions (960×540 canvas → 13.333×7.5 inches)
  pptx.defineLayout({ name: 'WIDESCREEN_16_9', width: 13.333, height: 7.5 })
  pptx.layout = 'WIDESCREEN_16_9'

  const SCALE_X = 13.333 / 960
  const SCALE_Y = 7.5 / 540

  for (let i = 0; i < slides.length; i++) {
    const slideData = slides[i]
    const slide = pptx.addSlide()

    // ── Background ──
    const bgColor = slideData.background || theme?.palette?.background || '#1a1a2e'
    slide.background = { color: hexToRgb(bgColor) }

    // Background image
    if (slideData.backgroundImage) {
      const resolvedBg = await resolveImageSource(slideData.backgroundImage)
      if (resolvedBg) {
        try {
          slide.addImage({
            x: 0,
            y: 0,
            w: 13.333,
            h: 7.5,
            ...resolvedBg,
          })
        } catch {
          // Keep solid background if image cannot be embedded.
        }
      }
    }

    // ── Render elements ──
    const elements = slideData.elements || []
    for (const el of elements) {
      try {
        if (el.type === 'text') {
          renderTextElement(slide, el, SCALE_X, SCALE_Y)
        } else if (el.type === 'image') {
          await renderImageElement(slide, el, SCALE_X, SCALE_Y)
        } else if (el.type === 'shape') {
          renderShapeElement(slide, el, SCALE_X, SCALE_Y)
        }
      } catch (err) {
        console.warn('Failed to render element:', el.id, err)
      }
    }

    // Native PPT chart for stats-heavy slides (keeps vector quality in Office apps).
    const stats = parseNumericStats(slideData)
    if (stats.values.length >= 2) {
      try {
        slide.addChart(pptx.ChartType.bar, [
          { name: 'Values', labels: stats.labels, values: stats.values },
        ], {
          x: 0.85,
          y: 4.75,
          w: 11.6,
          h: 2.2,
          barDir: 'col',
          catAxisLabelRotate: 0,
          showLegend: false,
          chartColors: ['4F7BFF'],
          valAxisMinVal: 0,
          valAxisTitle: '',
          catAxisTitle: '',
          showValue: false,
        })
      } catch {
        // Ignore chart errors and keep exported slide content.
      }
    }
  }

  // ── Download ──
  const filename = (title || 'presentation').replace(/[^a-zA-Z0-9_\- ]/g, '').trim()
  const pptxBuffer = await pptx.write({ outputType: 'arraybuffer' })
  const pptxBlob = await applyNativeTransitions(pptxBuffer, slides)
  downloadBlob(pptxBlob, `${filename || 'presentation'}.pptx`)
  return true
}

// ─── Element renderers ──────────────────────────────

function renderTextElement(slide, el, scaleX, scaleY) {
  const x = canvasToInches(el.x || 0, scaleX)
  const y = canvasToInches(el.y || 0, scaleY)
  const w = canvasToInches(el.width || 300, scaleX)
  const h = canvasToInches(Math.max(el.height || 50, 30), scaleY)

  // Optional text background rectangle
  const bgColor = el.backgroundColor || ''
  const bgOpacity = el.backgroundOpacity
  if (bgColor) {
    const parsed = parseColor(bgColor)
    const trans = typeof bgOpacity === 'number'
      ? Math.round((1 - bgOpacity) * 100)
      : parsed.transparency
    slide.addShape('rect', {
      x, y, w, h,
      fill: { color: parsed.color, transparency: trans },
      line: { color: parsed.color, width: 0, transparency: 100 },
    })
  }

  const text = el.text || ''
  const lines = text.split('\n')
  const textParts = lines.map(line => {
    const clean = line.replace(/^[▸•\-\s]+/, '').trim()
    return {
      text: clean || line,
      options: {
        fontSize: el.fontSize || 24,
        fontFace: el.fontFamily || 'Inter',
        bold: el.fontWeight === 'bold',
        italic: el.fontStyle === 'italic',
        underline: el.underline ? { style: 'sng' } : undefined,
        color: hexToRgb(el.fill || '#ffffff'),
        align: ALIGN_MAP[el.textAlign] || 'left',
        breakType: 'break',
      },
    }
  })

  slide.addText(textParts, {
    x, y, w, h,
    valign: 'top',
    wrap: true,
    shrinkText: true,
    lineSpacing: Math.round((el.lineHeight || 1.3) * (el.fontSize || 24)),
    transparency: el.opacity != null ? Math.round((1 - el.opacity) * 100) : 0,
    rotate: el.rotation || 0,
  })
}

async function renderImageElement(slide, el, scaleX, scaleY) {
  const src = el.src || ''
  if (!src) return

  const x = canvasToInches(el.x || 0, scaleX)
  const y = canvasToInches(el.y || 0, scaleY)
  const w = canvasToInches(el.width || 300, scaleX)
  const h = canvasToInches(el.height || 200, scaleY)

  const imgOpts = {
    x, y, w, h,
    transparency: el.opacity != null ? Math.round((1 - el.opacity) * 100) : 0,
    rotate: el.rotation || 0,
    rounding: el.borderRadius ? true : false,
  }

  const resolved = await resolveImageSource(src)
  if (!resolved) return
  Object.assign(imgOpts, resolved)

  try {
    slide.addImage(imgOpts)
  } catch {
    // Skip if image fails to load
  }
}

function renderShapeElement(slide, el, scaleX, scaleY) {
  const x = canvasToInches(el.x || 0, scaleX)
  const y = canvasToInches(el.y || 0, scaleY)
  const w = canvasToInches(el.width || 200, scaleX)
  const h = canvasToInches(el.height || 200, scaleY)

  const shapeType = el.shapeType || 'rect'
  const shapeMap = {
    rect: 'roundRect',
    circle: 'ellipse',
    triangle: 'triangle',
    diamond: 'diamond',
    arrow: 'rightArrow',
    hexagon: 'hexagon',
    line: 'rect',
  }
  const pptxShape = shapeMap[shapeType] || 'rect'

  const fillParsed = parseColor(el.fill || 'rgba(108, 99, 255, 0.3)')
  const strokeParsed = parseColor(el.stroke || '#6c63ff')

  const shapeOpts = {
    x, y, w, h,
    fill: { color: fillParsed.color, transparency: fillParsed.transparency },
    line: {
      color: strokeParsed.color,
      width: el.strokeWidth || 2,
      transparency: strokeParsed.transparency,
    },
    transparency: el.opacity != null ? Math.round((1 - el.opacity) * 100) : 0,
    rotate: el.rotation || 0,
  }

  // Handle fully transparent backgrounds
  if (fillParsed.transparency >= 95) {
    shapeOpts.fill = { type: 'none' }
  }

  // Handle transparent lines
  if (strokeParsed.transparency >= 95 || el.stroke === 'transparent') {
    shapeOpts.line = { type: 'none' }
  }

  slide.addShape(pptxShape, shapeOpts)
}
