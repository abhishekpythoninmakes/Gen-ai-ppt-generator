import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const CANVAS = Object.freeze({
  width: 960,
  height: 540,
  safeMargin: 60,
  gutter: 24,
})

// ─── Unique ID generator ────────────────────────────
let _uid = 0
function uid() { return `el_${Date.now()}_${++_uid}` }

// ─── Default element factories ──────────────────────
export function createTextElement(overrides = {}) {
  return {
    id: uid(),
    type: 'text',
    x: 60,
    y: 80,
    width: 840,
    height: 60,
    rotation: 0,
    text: 'Double-click to edit',
    fontSize: 32,
    fontFamily: 'Inter',
    fontWeight: 'normal',
    fontStyle: 'normal',
    underline: false,
    fill: '#ffffff',
    backgroundColor: '',
    backgroundOpacity: 0.6,
    textAlign: 'left',
    lineHeight: 1.3,
    opacity: 1,
    locked: false,
    ...overrides,
  }
}

export function createImageElement(overrides = {}) {
  return {
    id: uid(),
    type: 'image',
    x: 500,
    y: 60,
    width: 400,
    height: 280,
    rotation: 0,
    src: '',
    opacity: 1,
    borderRadius: 8,
    shadow: false,
    locked: false,
    ...overrides,
  }
}

export function createShapeElement(overrides = {}) {
  return {
    id: uid(),
    type: 'shape',
    x: 100,
    y: 200,
    width: 200,
    height: 200,
    rotation: 0,
    shapeType: 'rect', // rect, circle, triangle, arrow, line, diamond, hexagon
    fill: 'rgba(108, 99, 255, 0.3)',
    stroke: '#6c63ff',
    strokeWidth: 2,
    opacity: 1,
    locked: false,
    ...overrides,
  }
}

// ─── Default slide factory ──────────────────────────
export function createDefaultSlide(overrides = {}) {
  return {
    id: uid(),
    background: '#1a1a2e',
    backgroundImage: '',
    transition: { type: 'fade', duration: 0.5 },
    elements: [],
    ...overrides,
  }
}

// ─── Theme system ───────────────────────────────────────────
const THEME_LIBRARY = [
  {
    id: 'corporate-blue',
    mode: 'dark',
    palette: {
      background: '#093A57',
      surface: '#0d537a',
      primary: '#0F70A5',
      secondary: '#169bd8',
      accent: '#2f9e44',
      text: '#ffffff',
      muted: '#a8d8ea',
    },
    fonts: { heading: 'Inter', body: 'Inter' },
  },
  {
    id: 'dynamic-orange',
    mode: 'light',
    palette: {
      background: '#ffffff',
      surface: '#f4f6f8',
      primary: '#f26a21',
      secondary: '#ffb020',
      accent: '#1D2A44',
      text: '#2b3445',
      muted: '#637381',
    },
    fonts: { heading: 'Space Grotesk', body: 'Inter' },
  },
  {
    id: 'midnight-rose',
    mode: 'dark',
    palette: {
      background: '#0b0b1f',
      surface: '#1a162f',
      primary: '#ff6b7a',
      secondary: '#6c63ff',
      accent: '#ffa94d',
      text: '#f8f7ff',
      muted: '#b4b2d1',
    },
    fonts: { heading: 'Space Grotesk', body: 'Inter' },
  },
  {
    id: 'ocean-ink',
    mode: 'dark',
    palette: {
      background: '#061524',
      surface: '#0f2436',
      primary: '#00b4d8',
      secondary: '#48cae4',
      accent: '#ff9f1c',
      text: '#e8f1ff',
      muted: '#9db2ce',
    },
    fonts: { heading: 'Sora', body: 'Inter' },
  },
  {
    id: 'saffron-light',
    mode: 'light',
    palette: {
      background: '#f8f6f1',
      surface: '#ffffff',
      primary: '#0f2a5f',
      secondary: '#e63946',
      accent: '#f4a261',
      text: '#121826',
      muted: '#5b6475',
    },
    fonts: { heading: 'Manrope', body: 'DM Sans' },
  },
  {
    id: 'emerald-night',
    mode: 'dark',
    palette: {
      background: '#071a14',
      surface: '#0f2a22',
      primary: '#2dd4bf',
      secondary: '#34d399',
      accent: '#f59e0b',
      text: '#ecfdf5',
      muted: '#9bb8ae',
    },
    fonts: { heading: 'Space Grotesk', body: 'Inter' },
  },
  {
    id: 'studio-paper',
    mode: 'light',
    palette: {
      background: '#f7f4ee',
      surface: '#ffffff',
      primary: '#1f2937',
      secondary: '#8b5cf6',
      accent: '#f97316',
      text: '#111827',
      muted: '#6b7280',
    },
    fonts: { heading: 'Playfair Display', body: 'DM Sans' },
  },
  {
    id: 'graphite-teal',
    mode: 'dark',
    palette: {
      background: '#0f141a',
      surface: '#1b242d',
      primary: '#7aa2f7',
      secondary: '#2ac3de',
      accent: '#bb9af7',
      text: '#e6edf3',
      muted: '#9aa5b1',
    },
    fonts: { heading: 'Sora', body: 'Inter' },
  },
  {
    id: 'sandstone',
    mode: 'light',
    palette: {
      background: '#f6f3ef',
      surface: '#ffffff',
      primary: '#2b2f36',
      secondary: '#c07f45',
      accent: '#2f6f67',
      text: '#1b1f24',
      muted: '#6b7280',
    },
    fonts: { heading: 'Manrope', body: 'DM Sans' },
  },
]

const SAFE_FONTS = new Set(['Inter', 'Space Grotesk', 'Manrope', 'Sora', 'DM Sans', 'Playfair Display'])

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function hashString(input) {
  if (!input) return 0
  let hash = 0
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 31 + input.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

function sanitizeColor(value, fallback) {
  if (typeof value !== 'string') return fallback
  if (/^#([0-9a-fA-F]{6})$/.test(value)) return value
  return fallback
}

function withAlpha(hex, alpha = 0.2) {
  const clean = (hex || '').replace('#', '')
  if (clean.length !== 6) return `rgba(255,255,255,${alpha})`
  const r = parseInt(clean.slice(0, 2), 16)
  const g = parseInt(clean.slice(2, 4), 16)
  const b = parseInt(clean.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${clamp(alpha, 0, 1)})`
}

function surfaceFill(theme, lightAlpha = 0.08, darkAlpha = 0.6) {
  if (theme.mode === 'light') {
    return withAlpha(theme.palette.primary, lightAlpha)
  }
  return withAlpha(theme.palette.surface, darkAlpha)
}

function hexToRgb(hex) {
  const clean = (hex || '').replace('#', '')
  if (clean.length !== 6) return null
  const r = parseInt(clean.slice(0, 2), 16)
  const g = parseInt(clean.slice(2, 4), 16)
  const b = parseInt(clean.slice(4, 6), 16)
  return { r, g, b }
}

function luminance(hex) {
  const rgb = hexToRgb(hex)
  if (!rgb) return 0
  const toLinear = (v) => {
    const s = v / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  const r = toLinear(rgb.r)
  const g = toLinear(rgb.g)
  const b = toLinear(rgb.b)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrastRatio(hexA, hexB) {
  const l1 = luminance(hexA)
  const l2 = luminance(hexB)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

function isPaletteUsable(palette) {
  if (!palette) return false
  const bg = palette.background
  const text = palette.text
  if (!bg || !text) return false
  const ratio = contrastRatio(bg, text)
  return ratio >= 4.2
}

function pickThemeByMode(mode, seed = '') {
  const candidates = THEME_LIBRARY.filter(t => t.mode === mode)
  if (!candidates.length) return THEME_LIBRARY[hashString(seed) % THEME_LIBRARY.length]
  return candidates[hashString(seed) % candidates.length]
}

export function resolveTheme(rawTheme, seed = '') {
  if (rawTheme && typeof rawTheme === 'string') {
    const byId = THEME_LIBRARY.find(t => t.id === rawTheme)
    if (byId) return byId
  }

  if (rawTheme && typeof rawTheme === 'object') {
    const palette = rawTheme.palette || rawTheme.colors || {}
    const fonts = rawTheme.fonts || {}
    const mode = rawTheme.mode || 'dark'
    const base = pickThemeByMode(mode, seed)

    const safePalette = {
      background: sanitizeColor(palette.background, base.palette.background),
      surface: sanitizeColor(palette.surface, base.palette.surface),
      primary: sanitizeColor(palette.primary, base.palette.primary),
      secondary: sanitizeColor(palette.secondary, base.palette.secondary),
      accent: sanitizeColor(palette.accent, base.palette.accent),
      text: sanitizeColor(palette.text, base.palette.text),
      muted: sanitizeColor(palette.muted, base.palette.muted),
    }

    const paletteToUse = isPaletteUsable(safePalette) ? safePalette : base.palette

    return {
      id: rawTheme.name || base.id,
      mode: base.mode,
      palette: paletteToUse,
      fonts: {
        heading: SAFE_FONTS.has(fonts.heading) ? fonts.heading : base.fonts.heading,
        body: SAFE_FONTS.has(fonts.body) ? fonts.body : base.fonts.body,
      },
    }
  }

  return THEME_LIBRARY[hashString(seed) % THEME_LIBRARY.length]
}

// ─── Layout engine: positions AI content intelligently ─
function buildIconElements(iconNames, opts = {}) {
  if (!iconNames || !iconNames.length) return []
  const size = opts.size || 56
  const gap = opts.gap || 10
  const y = opts.y ?? 450
  const startX = opts.startX ?? (CANVAS.width - 40 - size)
  const color = opts.color || '#ffffff'
  const colorParam = encodeURIComponent(color)
  const elements = []
  iconNames.slice(0, 3).forEach((name, idx) => {
    const x = startX - idx * (size + gap)
    elements.push(createShapeElement({
      x: x - (size * 0.2),
      y: y - (size * 0.2),
      width: size * 1.4,
      height: size * 1.4,
      shapeType: 'circle',
      fill: withAlpha(color, 0.1),
      stroke: 'transparent',
      strokeWidth: 0,
    }))
    elements.push(createImageElement({
      x,
      y,
      width: size,
      height: size,
      src: `https://api.iconify.design/${name}.svg?color=${colorParam}&width=128`,
      borderRadius: 0,
      isIcon: true,
      iconName: name,
      iconColor: color,
    }))
  })
  return elements
}

function normalizeContent(slideData = {}) {
  const content = slideData.content || {}
  return {
    heading: content.heading || slideData.heading || slideData.title || '',
    subheading: content.subheading || slideData.description || '',
    bulletPoints: content.bullet_points || slideData.points || [],
    steps: content.steps || [],
    stats: content.stats || [],
  }
}

function scaleFont(base, text, min = 18) {
  if (!text) return base
  const len = text.length
  if (len > 70) return clamp(base - 16, min, base)
  if (len > 50) return clamp(base - 10, min, base)
  if (len > 36) return clamp(base - 6, min, base)
  return base
}

function estimateLines(text, boxWidth, fontSize) {
  const charsPerLine = Math.max(1, Math.floor(boxWidth / (fontSize * 0.55)))
  return Math.ceil((text || '').length / charsPerLine)
}

function fitFontSize(text, boxWidth, boxHeight, baseSize, minSize = 12, lineHeight = 1.3) {
  let size = baseSize
  while (size > minSize) {
    const lines = estimateLines(text, boxWidth, size)
    const height = lines * size * lineHeight
    if (height <= boxHeight) break
    size -= 1
  }
  return size
}

function pickShapeType(shapeList, fallback) {
  if (!Array.isArray(shapeList) || !shapeList.length) return fallback
  const lowered = shapeList.map(s => (s || '').toLowerCase())
  if (lowered.includes('hexagon')) return 'hexagon'
  if (lowered.includes('circle')) return 'circle'
  if (lowered.includes('diamond')) return 'diamond'
  if (lowered.includes('triangle')) return 'triangle'
  if (lowered.includes('arrow')) return 'arrow'
  if (lowered.includes('line')) return 'line'
  return fallback
}

function buildBulletText(points) {
  return points.map(p => `•  ${p}`).join('\n')
}

function createHeadingElement(text, theme, opts = {}) {
  return createTextElement({
    text,
    fontFamily: theme.fonts.heading,
    fontWeight: 'bold',
    fill: theme.palette.text,
    ...opts,
  })
}

function createBodyElement(text, theme, opts = {}) {
  return createTextElement({
    text,
    fontFamily: theme.fonts.body,
    fontWeight: 'normal',
    fill: theme.palette.text,
    ...opts,
  })
}

// ─── Dynamic Layout Engine (no-overlap, CSS-flexbox-style stacking) ───

/**
 * Estimate the rendered height of a text block.
 * Accounts for word wrapping based on available width and font size.
 */
function estimateTextHeight(text, boxWidth, fontSize, lineHeight = 1.3) {
  if (!text) return 0
  const charsPerLine = Math.max(1, Math.floor(boxWidth / (fontSize * 0.52)))
  const words = text.split(/\s+/)
  let lines = 1
  let currentLineLen = 0
  for (const word of words) {
    if (currentLineLen + word.length + 1 > charsPerLine && currentLineLen > 0) {
      lines++
      currentLineLen = word.length
    } else {
      currentLineLen += (currentLineLen > 0 ? 1 : 0) + word.length
    }
  }
  // Also account for explicit newlines
  const explicitNewlines = (text.match(/\n/g) || []).length
  lines += explicitNewlines
  return Math.ceil(lines * fontSize * lineHeight)
}

/**
 * Dynamic vertical stacker: places elements top-to-bottom with proper gaps.
 * Returns the final Y position after the last element.
 */
function stackVertically(elements, items, startY, gap = 16) {
  let currentY = startY
  for (const item of items) {
    if (!item) continue
    const el = { ...item, y: currentY }
    const height = item._estimatedHeight || item.height || 40
    el.height = height
    delete el._estimatedHeight
    elements.push(el)
    currentY += height + gap
  }
  return currentY
}

/**
 * Auto-scale font size to fit text within available height.
 * More aggressive than fitFontSize — used for the stacking layout.
 */
function autoFitFont(text, boxWidth, maxHeight, baseSize, minSize = 12, lineHeight = 1.3) {
  let size = baseSize
  while (size > minSize) {
    const h = estimateTextHeight(text, boxWidth, size, lineHeight)
    if (h <= maxHeight) break
    size -= 1
  }
  return size
}

function estimateTextDensity(heading = '', subheading = '', bulletPoints = []) {
  const pointText = Array.isArray(bulletPoints) ? bulletPoints.join(' ') : ''
  const score = (heading.length * 1.0) + (subheading.length * 0.65) + (pointText.length * 0.35)
  return clamp(score / 260, 0.2, 1)
}

function computeTextImageZones({
  hasImage = false,
  imageSide = 'right',
  heading = '',
  subheading = '',
  bulletPoints = [],
} = {}) {
  const safeLeft = CANVAS.safeMargin
  const safeRight = CANVAS.width - CANVAS.safeMargin
  const availableW = Math.max(0, safeRight - safeLeft)

  if (!hasImage) {
    return {
      safeLeft,
      safeRight,
      gap: 0,
      contentX: safeLeft,
      contentW: availableW,
      imageX: safeLeft,
      imageW: 0,
    }
  }

  const density = estimateTextDensity(heading, subheading, bulletPoints)
  const baseGap = Math.round(availableW * (0.02 + density * 0.03))
  const gap = clamp(baseGap, Math.round(CANVAS.gutter * 0.75), CANVAS.safeMargin)

  const textRatio = clamp(0.48 + density * 0.14, 0.48, 0.62)
  const contentW = Math.round((availableW - gap) * textRatio)
  const imageW = Math.max(0, availableW - gap - contentW)

  if (imageSide === 'left') {
    const imageX = safeLeft
    const contentX = imageX + imageW + gap
    return { safeLeft, safeRight, gap, contentX, contentW, imageX, imageW }
  }

  const contentX = safeLeft
  const imageX = contentX + contentW + gap
  return { safeLeft, safeRight, gap, contentX, contentW, imageX, imageW }
}

function layoutHero(slideData, theme, layout) {
  const elements = []
  const { heading, subheading, bulletPoints } = normalizeContent(slideData)
  const hasImage = slideData.image_url && slideData.image_url.trim()
  const flip = layout === 'left-right'

  // --- Content/image zones: computed dynamically from canvas + content density ---
  const zones = computeTextImageZones({
    hasImage: !!hasImage,
    imageSide: flip ? 'left' : 'right',
    heading,
    subheading,
    bulletPoints,
  })
  const contentX = zones.contentX
  const contentW = zones.contentW
  const imageX = zones.imageX
  const imageW = zones.imageW
  const safeTop = CANVAS.safeMargin
  const safeBottom = CANVAS.height - Math.round(CANVAS.safeMargin * 0.83)
  const availableHeight = safeBottom - safeTop

  // --- Dynamic font sizing based on text length ---
  let titleSize = heading.length > 60 ? 32 : heading.length > 40 ? 38 : heading.length > 25 ? 44 : 52
  const titleHeight = estimateTextHeight(heading || 'Untitled', contentW, titleSize, 1.15)
  
  let currentY = safeTop

  // --- Decorative accent bar ---
  elements.push(createShapeElement({
    x: contentX, y: currentY,
    width: 48, height: 5,
    shapeType: 'rect',
    fill: theme.palette.primary,
    stroke: 'transparent', strokeWidth: 0,
  }))
  currentY += 20

  // --- Heading ---
  const headingEl = createHeadingElement(heading || 'Untitled', theme, {
    x: contentX, y: currentY,
    width: contentW, height: titleHeight,
    fontSize: titleSize,
    textAlign: hasImage ? 'left' : 'center',
    lineHeight: 1.15,
  })
  elements.push(headingEl)
  currentY += titleHeight + 16

  // --- Subheading ---
  if (subheading) {
    const subSize = 18
    const subHeight = estimateTextHeight(subheading, contentW, subSize, 1.35)
    elements.push(createBodyElement(subheading, theme, {
      x: contentX, y: currentY,
      width: contentW, height: subHeight,
      fontSize: subSize,
      fill: theme.palette.muted,
      textAlign: hasImage ? 'left' : 'center',
      fontStyle: 'italic',
      lineHeight: 1.35,
    }))
    currentY += subHeight + 20
  }

  // --- Bullet points (fill remaining space) ---
  if (bulletPoints && bulletPoints.length) {
    const bulletText = buildBulletText(bulletPoints.slice(0, 5))
    const remainingH = Math.max(60, safeBottom - currentY - 20)
    const bulletFont = autoFitFont(bulletText, contentW, remainingH, 17, 13, 1.55)
    const bulletH = estimateTextHeight(bulletText, contentW, bulletFont, 1.55)
    elements.push(createBodyElement(bulletText, theme, {
      x: contentX, y: currentY,
      width: contentW, height: Math.min(bulletH, remainingH),
      fontSize: bulletFont,
      fill: theme.palette.text,
      lineHeight: 1.55,
    }))
  }

  // --- Image (right/left side) ---
  if (hasImage) {
    const framePad = Math.max(1, Math.round((zones.gap || CANVAS.gutter) * 0.35))

    // Decorative background card
    elements.push(createShapeElement({
      x: imageX - framePad, y: safeTop - framePad,
      width: imageW + (framePad * 2), height: availableHeight + (framePad * 2),
      shapeType: 'rect',
      fill: withAlpha(theme.palette.primary, 0.06),
      stroke: 'transparent', strokeWidth: 0,
      borderRadius: 16,
    }))
    elements.push(createImageElement({
      x: imageX, y: safeTop,
      width: imageW, height: availableHeight,
      src: slideData.image_url,
      borderRadius: 16,
    }))
  }

  return elements
}

function layoutProcess(slideData, theme, layout) {
  const elements = []
  const { heading, steps, bulletPoints } = normalizeContent(slideData)
  const items = (steps && steps.length ? steps : bulletPoints).slice(0, 5)
  const iconNames = slideData.icon_names || []

  // --- Heading ---
  const headingSize = heading.length > 40 ? 28 : 34
  const headingH = estimateTextHeight(heading || 'Process', 840, headingSize, 1.15)
  elements.push(createHeadingElement(heading || 'Process', theme, {
    x: 60, y: 36, width: 840, height: headingH,
    fontSize: headingSize,
  }))

  const count = Math.max(3, items.length || 3)
  const usable = items.length ? items : ['Step One', 'Step Two', 'Step Three']
  const hasImage = !!slideData.image_url

  if (layout === 'grid') {
    // --- Grid layout: 2x2 cards ---
    const cols = 2
    const cellW = 380
    const cellH = 140
    const gridStartX = 60
    const gridStartY = headingH + 60
    const gapX = 40
    const gapY = 30

    for (let i = 0; i < Math.min(count, 4); i += 1) {
      const row = Math.floor(i / cols)
      const col = i % cols
      const x = gridStartX + col * (cellW + gapX)
      const y = gridStartY + row * (cellH + gapY)
      const label = usable[i] || `Step ${i + 1}`

      // Card background
      elements.push(createShapeElement({
        x, y, width: cellW, height: cellH,
        shapeType: 'rect',
        fill: surfaceFill(theme, 0.08, 0.5),
        stroke: withAlpha(theme.palette.secondary, 0.35),
        strokeWidth: 1.5,
      }))

      // Step number badge
      elements.push(createTextElement({
        x: x + 16, y: y + 14,
        width: 36, height: 28,
        text: `${i + 1}`,
        fontSize: 20, fontWeight: 'bold',
        fontFamily: theme.fonts.heading,
        fill: theme.palette.primary,
      }))

      // Step label
      const fitSize = autoFitFont(label, cellW - 60, cellH - 50, 15, 12)
      elements.push(createBodyElement(label, theme, {
        x: x + 56, y: y + 14,
        width: cellW - 76, height: cellH - 28,
        fontSize: fitSize,
        lineHeight: 1.4,
      }))
    }
  } else {
    // --- Zigzag/flow layout: horizontal timeline ---
    const timelineY = 220
    const contentZoneW = hasImage ? 560 : 840
    const startX = 80
    const endX = contentZoneW
    const gap = count > 1 ? (endX - startX) / (count - 1) : 0

    // Horizontal connector line
    elements.push(createShapeElement({
      x: startX - 10, y: timelineY,
      width: (endX - startX) + 20, height: 3,
      shapeType: 'rect',
      fill: withAlpha(theme.palette.muted, 0.25),
      stroke: 'transparent', strokeWidth: 0,
    }))

    for (let i = 0; i < count; i += 1) {
      const label = usable[i] || `Step ${i + 1}`
      const px = startX + i * gap
      const isTop = i % 2 === 0

      // Node dot
      elements.push(createShapeElement({
        x: px - 12, y: timelineY - 12,
        width: 24, height: 24,
        shapeType: 'circle',
        fill: theme.palette.primary,
        stroke: theme.palette.background,
        strokeWidth: 3,
      }))

      // Step number
      const numY = isTop ? timelineY - 70 : timelineY + 30
      elements.push(createTextElement({
        x: px - 16, y: numY,
        width: 32, height: 28,
        text: `${i + 1}`,
        fontSize: 20, fontWeight: 'bold',
        fill: theme.palette.primary,
        textAlign: 'center',
      }))

      // Step text — auto-fit to column width
      const colW = Math.max(gap * 0.85, 80)
      const textY = isTop ? numY + 28 : numY + 28
      const fitSize = autoFitFont(label, colW, 60, 13, 11, 1.3)
      elements.push(createBodyElement(label, theme, {
        x: px - colW / 2, y: textY,
        width: colW, height: 60,
        fontSize: fitSize,
        textAlign: 'center',
        lineHeight: 1.3,
      }))
    }

    // Side image
    if (hasImage) {
      elements.push(createImageElement({
        x: 610, y: 80, width: 300, height: 380,
        src: slideData.image_url,
        borderRadius: 16,
      }))
    }
  }

  return elements
}

function layoutTimeline(slideData, theme) {
  const elements = []
  const { heading, steps, bulletPoints } = normalizeContent(slideData)
  const items = (steps && steps.length ? steps : bulletPoints).slice(0, 5)
  const hasImage = !!slideData.image_url

  // --- Heading ---
  const headingSize = heading.length > 40 ? 28 : 34
  const headingH = estimateTextHeight(heading || 'Timeline', 840, headingSize, 1.15)
  elements.push(createHeadingElement(heading || 'Timeline', theme, {
    x: 60, y: 36, width: 840, height: headingH,
    fontSize: headingSize,
  }))

  const count = Math.max(3, items.length || 3)
  const usable = items.length ? items : ['Phase One', 'Phase Two', 'Phase Three']
  const cardW = 150
  const cardH = 70
  const contentEndX = hasImage ? 600 : 900
  const startX = (cardW / 2) + 40
  const endX = contentEndX - (cardW / 2)
  const lineY = headingH + 140
  const gap = count > 1 ? (endX - startX) / (count - 1) : 0

  // Horizontal timeline line
  elements.push(createShapeElement({
    x: startX, y: lineY,
    width: endX - startX, height: 3,
    shapeType: 'line',
    fill: theme.palette.secondary,
    stroke: theme.palette.secondary,
    strokeWidth: 2,
  }))

  for (let i = 0; i < count; i += 1) {
    const x = startX + i * gap
    const isTop = i % 2 === 0
    const cardX = x - cardW / 2
    const cardY = isTop ? lineY - cardH - 30 : lineY + 28
    const label = usable[i] || `Milestone ${i + 1}`
    const labelFont = autoFitFont(label, cardW - 20, cardH - 16, 13, 10, 1.3)

    // Dot
    elements.push(createShapeElement({
      x: x - 8, y: lineY - 8,
      width: 16, height: 16,
      shapeType: 'circle',
      fill: theme.palette.primary,
      stroke: withAlpha(theme.palette.primary, 0.5),
      strokeWidth: 2,
    }))

    // Card background
    elements.push(createShapeElement({
      x: cardX, y: cardY,
      width: cardW, height: cardH,
      shapeType: 'rect',
      fill: surfaceFill(theme, 0.08, 0.55),
      stroke: withAlpha(theme.palette.primary, 0.3),
      strokeWidth: 1,
    }))

    // Card text
    elements.push(createBodyElement(label, theme, {
      x: cardX + 10, y: cardY + 10,
      width: cardW - 20, height: cardH - 16,
      fontSize: labelFont,
      fill: theme.palette.text,
      textAlign: 'center',
      lineHeight: 1.3,
    }))
  }

  // Side image
  if (hasImage) {
    elements.push(createImageElement({
      x: 620, y: headingH + 60, width: 300, height: 340,
      src: slideData.image_url,
      borderRadius: 12,
    }))
  }

  return elements
}

function layoutInfographic(slideData, theme, layout) {
  const elements = []
  const { heading, bulletPoints } = normalizeContent(slideData)
  const items = bulletPoints.slice(0, 5)
  const usable = items.length ? items : ['Key Point 1', 'Key Point 2', 'Key Point 3', 'Key Point 4']
  const hasImage = !!slideData.image_url

  const headingSize = heading.length > 40 ? 26 : 32
  const headingH = estimateTextHeight(heading || 'Infographic', 840, headingSize, 1.15)
  elements.push(createHeadingElement(heading || 'Infographic', theme, {
    x: 60, y: 30, width: 840, height: headingH,
    fontSize: headingSize,
    textAlign: 'center',
  }))

  if (layout === 'grid') {
    // 2x2 grid
    const cols = 2
    const cellW = 380
    const cellH = 130
    const gridStartX = 60
    const gridStartY = headingH + 60
    const gapX = 40
    const gapY = 25

    for (let i = 0; i < Math.min(usable.length, 4); i += 1) {
      const row = Math.floor(i / cols)
      const col = i % cols
      const x = gridStartX + col * (cellW + gapX)
      const y = gridStartY + row * (cellH + gapY)
      const label = usable[i]
      const fitSize = autoFitFont(label, cellW - 40, cellH - 24, 15, 11)

      elements.push(createShapeElement({
        x, y, width: cellW, height: cellH,
        shapeType: 'rect',
        fill: surfaceFill(theme, 0.08, 0.5),
        stroke: withAlpha(theme.palette.secondary, 0.35),
        strokeWidth: 1.5,
      }))
      elements.push(createBodyElement(label, theme, {
        x: x + 20, y: y + 14,
        width: cellW - 40, height: cellH - 28,
        fontSize: fitSize,
        lineHeight: 1.4,
      }))
    }
  } else {
    // Circular/radial layout
    const centerX = hasImage ? 280 : 480
    const centerY = headingH + 200
    const radius = 150

    // Central circle
    elements.push(createShapeElement({
      x: centerX - 65, y: centerY - 65,
      width: 130, height: 130,
      shapeType: 'circle',
      fill: withAlpha(theme.palette.primary, 0.12),
      stroke: theme.palette.primary,
      strokeWidth: 2,
    }))
    const coreText = heading ? heading.split(' ').slice(0, 2).join(' ') : 'Core'
    elements.push(createTextElement({
      x: centerX - 55, y: centerY - 16,
      width: 110, height: 32,
      text: coreText,
      fontSize: 14, fontFamily: theme.fonts.heading,
      fontWeight: 'bold', fill: theme.palette.text, textAlign: 'center',
    }))

    const count = Math.min(usable.length, 5)
    for (let i = 0; i < count; i += 1) {
      const angle = (Math.PI * 2 * i) / count - Math.PI / 2
      const x = centerX + Math.cos(angle) * radius
      const y = centerY + Math.sin(angle) * radius
      const label = usable[i]
      const fitSize = autoFitFont(label, 100, 50, 12, 10, 1.25)

      elements.push(createShapeElement({
        x: x - 55, y: y - 55,
        width: 110, height: 110,
        shapeType: pickShapeType(slideData.visual_elements?.shape_type, 'hexagon'),
        fill: withAlpha(theme.palette.secondary, 0.15),
        stroke: theme.palette.secondary,
        strokeWidth: 1.5,
      }))
      elements.push(createBodyElement(label, theme, {
        x: x - 48, y: y - 20,
        width: 96, height: 46,
        fontSize: fitSize,
        textAlign: 'center',
        lineHeight: 1.25,
      }))
    }

    if (hasImage) {
      elements.push(createImageElement({
        x: 600, y: headingH + 60, width: 310, height: 360,
        src: slideData.image_url,
        borderRadius: 16,
      }))
    }
  }

  return elements
}

function parseStatValue(value) {
  if (value === null || value === undefined) return null
  const str = String(value)
  const match = str.match(/-?\d+(\.\d+)?/)
  return match ? parseFloat(match[0]) : null
}

function layoutStats(slideData, theme) {
  const elements = []
  const { heading, stats, bulletPoints } = normalizeContent(slideData)

  const rawStats = Array.isArray(stats) && stats.length
    ? stats
    : bulletPoints.slice(0, 4).map((bp, idx) => ({
      label: bp, value: '', unit: '', note: '', _fallbackIndex: idx,
    }))

  // --- Heading ---
  const headingSize = heading.length > 40 ? 26 : 32
  const headingH = estimateTextHeight(heading || 'Key Stats', 840, headingSize, 1.15)
  elements.push(createHeadingElement(heading || 'Key Stats', theme, {
    x: 60, y: 30, width: 840, height: headingH,
    fontSize: headingSize,
  }))

  // --- Stat cards ---
  const cardCount = Math.min(3, rawStats.length || 3)
  const totalGap = 30 * (cardCount - 1)
  const cardWidth = Math.floor((840 - totalGap) / cardCount)
  const cardHeight = 110
  const cardY = headingH + 50
  const startX = 60

  for (let i = 0; i < cardCount; i += 1) {
    const stat = rawStats[i] || { label: `Metric ${i + 1}`, value: '', unit: '' }
    const x = startX + i * (cardWidth + 30)

    // Card bg
    elements.push(createShapeElement({
      x, y: cardY,
      width: cardWidth, height: cardHeight,
      shapeType: 'rect',
      fill: surfaceFill(theme, 0.12, 0.35),
      stroke: withAlpha(theme.palette.primary, 0.35),
      strokeWidth: 1.5,
    }))

    // Value
    const valueText = `${stat.value || '—'}${stat.unit || ''}`
    elements.push(createTextElement({
      x: x + 16, y: cardY + 14,
      width: cardWidth - 32, height: 40,
      text: valueText,
      fontSize: 28, fontWeight: 'bold',
      fontFamily: theme.fonts.heading,
      fill: theme.palette.primary,
    }))

    // Label
    const labelFont = autoFitFont(stat.label || '', cardWidth - 32, 40, 13, 10)
    elements.push(createBodyElement(stat.label || `Metric ${i + 1}`, theme, {
      x: x + 16, y: cardY + 60,
      width: cardWidth - 32, height: 40,
      fontSize: labelFont,
      fill: theme.palette.muted,
    }))
  }

  // --- Simple bar chart if numeric data exists ---
  const numericStats = rawStats
    .map(s => parseStatValue(s.value))
    .filter(v => typeof v === 'number' && !Number.isNaN(v))

  if (numericStats.length >= 2) {
    const chartY = cardY + cardHeight + 40
    const chartH = Math.min(160, CANVAS.height - chartY - 40)
    const chartW = 840
    const maxVal = Math.max(...numericStats, 1)
    const barCount = Math.min(numericStats.length, 5)
    const barGap = 16
    const barWidth = (chartW - barGap * (barCount - 1)) / barCount

    // Baseline
    elements.push(createShapeElement({
      x: 60, y: chartY + chartH - 2,
      width: chartW, height: 2,
      shapeType: 'line',
      fill: theme.palette.muted,
      stroke: theme.palette.muted,
      strokeWidth: 2,
    }))

    for (let i = 0; i < barCount; i += 1) {
      const val = numericStats[i]
      const barHeight = clamp((val / maxVal) * (chartH - 20), 20, chartH - 10)
      const bx = 60 + i * (barWidth + barGap)
      const by = chartY + chartH - barHeight
      elements.push(createShapeElement({
        x: bx, y: by,
        width: barWidth, height: barHeight,
        shapeType: 'rect',
        fill: withAlpha(theme.palette.accent, 0.7),
        stroke: withAlpha(theme.palette.accent, 0.9),
        strokeWidth: 1,
      }))
    }
  }

  return elements
}

function layoutComparison(slideData, theme) {
  const elements = []
  const { heading, bulletPoints, subheading } = normalizeContent(slideData)
  const leftPoints = bulletPoints.filter((_, i) => i % 2 === 0)
  const rightPoints = bulletPoints.filter((_, i) => i % 2 === 1)

  // --- Heading ---
  const headingSize = heading.length > 40 ? 26 : 32
  const headingH = estimateTextHeight(heading || 'Comparison', 840, headingSize, 1.15)
  elements.push(createHeadingElement(heading || 'Comparison', theme, {
    x: 60, y: 30, width: 840, height: headingH,
    fontSize: headingSize,
    textAlign: 'center',
  }))

  const colTop = headingH + 60
  const colHeight = CANVAS.height - colTop - 30
  const colWidth = 400

  // Left panel
  elements.push(createShapeElement({
    x: 50, y: colTop,
    width: colWidth, height: colHeight,
    shapeType: 'rect',
    fill: surfaceFill(theme, 0.06, 0.4),
    stroke: withAlpha(theme.palette.primary, 0.2),
    strokeWidth: 1,
  }))
  // Right panel
  elements.push(createShapeElement({
    x: 510, y: colTop,
    width: colWidth, height: colHeight,
    shapeType: 'rect',
    fill: surfaceFill(theme, 0.06, 0.4),
    stroke: withAlpha(theme.palette.secondary, 0.2),
    strokeWidth: 1,
  }))

  // Divider
  elements.push(createShapeElement({
    x: 478, y: colTop,
    width: 4, height: colHeight,
    shapeType: 'rect',
    fill: withAlpha(theme.palette.muted, 0.25),
    stroke: 'transparent', strokeWidth: 0,
  }))

  // Column headings
  const leftHeading = subheading || 'Option A'
  elements.push(createTextElement({
    x: 70, y: colTop + 12,
    width: 360, height: 30,
    text: leftHeading,
    fontSize: 18, fontWeight: 'bold',
    fontFamily: theme.fonts.heading,
    fill: theme.palette.primary,
  }))
  elements.push(createTextElement({
    x: 530, y: colTop + 12,
    width: 360, height: 30,
    text: 'Option B',
    fontSize: 18, fontWeight: 'bold',
    fontFamily: theme.fonts.heading,
    fill: theme.palette.secondary,
  }))

  // Content - auto-fit
  const contentH = colHeight - 60
  if (leftPoints.length) {
    const leftText = buildBulletText(leftPoints.slice(0, 5))
    const leftFont = autoFitFont(leftText, 340, contentH, 15, 11, 1.5)
    elements.push(createBodyElement(leftText, theme, {
      x: 70, y: colTop + 50,
      width: 340, height: contentH,
      fontSize: leftFont,
      lineHeight: 1.5,
    }))
  }
  if (rightPoints.length) {
    const rightText = buildBulletText(rightPoints.slice(0, 5))
    const rightFont = autoFitFont(rightText, 340, contentH, 15, 11, 1.5)
    elements.push(createBodyElement(rightText, theme, {
      x: 530, y: colTop + 50,
      width: 340, height: contentH,
      fontSize: rightFont,
      lineHeight: 1.5,
    }))
  }

  return elements
}

function layoutStructuredSlide(slideData, index, totalSlides, theme, options = {}) {
  const type = (slideData.slide_type || '').toLowerCase()
  const rawLayout = (slideData.layout || '').toLowerCase()
  const isTemplate = options.template === true
  let elements = []

  // Overlay for background images
  const overlayOpacity = parseFloat(slideData.overlay_opacity || 0)
  if (overlayOpacity > 0 && slideData.bg_image) {
    const overlayColor = theme.mode === 'light'
      ? `rgba(255, 255, 255, ${overlayOpacity})`
      : `rgba(0, 0, 0, ${overlayOpacity})`
    elements.push(createShapeElement({
      x: 0, y: 0, width: CANVAS.width, height: CANVAS.height,
      shapeType: 'rect',
      fill: overlayColor,
      stroke: 'transparent',
      strokeWidth: 0,
    }))
  }

  const layout = (() => {
    if (type === 'process') return ['zigzag', 'grid'].includes(rawLayout) ? rawLayout : 'zigzag'
    if (type === 'timeline') return ['left-right', 'split', 'zigzag'].includes(rawLayout) ? rawLayout : 'left-right'
    if (type === 'infographic') return ['circular', 'grid'].includes(rawLayout) ? rawLayout : 'circular'
    if (type === 'stats') return ['grid', 'split'].includes(rawLayout) ? rawLayout : 'split'
    if (type === 'comparison') return ['split', 'left-right'].includes(rawLayout) ? rawLayout : 'split'
    if (type === 'hero') return ['split', 'left-right'].includes(rawLayout) ? rawLayout : 'split'
    return rawLayout || 'split'
  })()

  if (type === 'hero' || index === 0) {
    elements.push(...layoutHero(slideData, theme, layout))
  } else if (type === 'process') {
    elements.push(...layoutProcess(slideData, theme, layout))
  } else if (type === 'timeline') {
    elements.push(...layoutTimeline(slideData, theme))
  } else if (type === 'infographic') {
    elements.push(...layoutInfographic(slideData, theme, layout))
  } else if (type === 'stats') {
    elements.push(...layoutStats(slideData, theme))
  } else if (type === 'comparison') {
    elements.push(...layoutComparison(slideData, theme))
  } else {
    // Content/summary/generic — use the universal stacking layout
    const fallback = layoutAISlide(slideData, index, totalSlides, theme)
    elements.push(...(fallback.elements || fallback))
  }

  if (elements.length <= (overlayOpacity > 0 ? 1 : 0)) {
    const fallback = layoutAISlide(slideData, index, totalSlides, theme)
    elements.push(...(fallback.elements || fallback))
  }

  // Icons in top-right
  const iconNames = slideData.icon_names || slideData.icons || []
  elements.push(...buildIconElements(iconNames, {
    y: 40, size: 40,
    color: theme.palette.secondary,
    startX: 880,
  }))

  return elements
}

/**
 * Universal content slide layout — dynamic vertical stacking, no overlaps.
 * Used for "content", "summary", and any unrecognized slide types.
 */
export function layoutAISlide(slideData, index, totalSlides, themeOverride) {
  const theme = themeOverride || resolveTheme(slideData?.theme, slideData?.heading || '')
  const elements = []
  const isTitle = index === 0
  const isConclusion = index === totalSlides - 1
  const hasImage = slideData.image_url && slideData.image_url.trim()
  const points = Array.isArray(slideData.points) ? slideData.points : []
  const headingText = slideData.heading || slideData.title || 'Slide'
  const desc = slideData.description || ''

  // --- Zone dimensions ---
  const zones = computeTextImageZones({
    hasImage: !!hasImage,
    imageSide: 'right',
    heading: headingText,
    subheading: desc,
    bulletPoints: points,
  })
  const contentX = zones.contentX
  const contentW = zones.contentW
  const safeTop = Math.round(CANVAS.safeMargin * 0.83)
  const safeBottom = CANVAS.height - 40
  const availableH = safeBottom - safeTop

  let currentY = safeTop

  // --- Decorative accent line for non-title slides ---
  if (!isTitle) {
    elements.push(createShapeElement({
      x: contentX, y: currentY,
      width: 40, height: 4,
      shapeType: 'rect',
      fill: theme.palette.primary,
      stroke: 'transparent', strokeWidth: 0,
    }))
    currentY += 14
  }

  // --- Heading ---
  let headingSize = isTitle ? 44 : 30
  if (headingText.length > 50) headingSize = Math.max(headingSize - 10, 22)
  else if (headingText.length > 35) headingSize = Math.max(headingSize - 6, 24)

  const headingH = estimateTextHeight(headingText, contentW, headingSize, 1.15)
  elements.push(createTextElement({
    x: contentX, y: currentY,
    width: contentW, height: headingH,
    text: headingText,
    fontSize: headingSize, fontWeight: 'bold',
    fontFamily: theme.fonts.heading,
    textAlign: isTitle && !hasImage ? 'center' : 'left',
    fill: theme.palette.text,
    lineHeight: 1.15,
  }))
  currentY += headingH + 12

  // --- Description/subheading ---
  if (desc) {
    const descSize = 16
    const descH = estimateTextHeight(desc, contentW, descSize, 1.35)
    elements.push(createTextElement({
      x: contentX, y: currentY,
      width: contentW, height: descH,
      text: desc,
      fontSize: descSize, fontWeight: 'normal',
      fill: theme.palette.muted,
      fontStyle: 'italic',
      textAlign: isTitle && !hasImage ? 'center' : 'left',
      lineHeight: 1.35,
    }))
    currentY += descH + 16
  }

  // --- Bullet points ---
  if (points.length > 0) {
    const bulletText = points.map(p => `▸  ${p}`).join('\n')
    const remainingH = Math.max(40, safeBottom - currentY - (isConclusion ? 40 : 10))
    const bulletFont = autoFitFont(bulletText, contentW, remainingH, 16, 12, 1.55)
    const bulletH = Math.min(estimateTextHeight(bulletText, contentW, bulletFont, 1.55), remainingH)

    elements.push(createTextElement({
      x: contentX, y: currentY,
      width: contentW, height: bulletH,
      text: bulletText,
      fontSize: bulletFont, fontWeight: 'normal',
      fill: theme.palette.text,
      textAlign: 'left',
      lineHeight: 1.55,
    }))
    currentY += bulletH + 10
  }

  // --- Image ---
  if (hasImage) {
    const imgW = zones.imageW
    const imgH = Math.min(availableH, Math.round(CANVAS.height * 0.74))
    const framePad = Math.max(1, Math.round((zones.gap || CANVAS.gutter) * 0.3))
    elements.push(createShapeElement({
      x: zones.imageX - framePad, y: safeTop - framePad,
      width: imgW + (framePad * 2), height: imgH + (framePad * 2),
      shapeType: 'rect',
      fill: withAlpha(theme.palette.primary, 0.05),
      stroke: 'transparent', strokeWidth: 0,
      borderRadius: 16,
    }))
    elements.push(createImageElement({
      x: zones.imageX, y: safeTop,
      width: imgW, height: imgH,
      src: slideData.image_url,
      borderRadius: 14,
    }))
  } else if (!isTitle) {
    // Subtle decorative shape when no image
    elements.push(createShapeElement({
      x: CANVAS.width - 200, y: CANVAS.height - 200,
      width: 160, height: 160,
      shapeType: 'circle',
      fill: withAlpha(theme.palette.primary, 0.06),
      stroke: 'transparent', strokeWidth: 0,
    }))
  }

  // --- Conclusion call-to-action accent ---
  if (isConclusion && currentY < safeBottom - 30) {
    elements.push(createShapeElement({
      x: contentX, y: safeBottom - 6,
      width: 80, height: 4,
      shapeType: 'rect',
      fill: theme.palette.accent,
      stroke: 'transparent', strokeWidth: 0,
    }))
  }

  return elements
}

// ─── Template layout: dynamic stacking, no overlaps ──
export function layoutTemplateSlide(slideData, index, totalSlides, themeOverride) {
  const theme = themeOverride || resolveTheme(slideData?.theme, slideData?.heading || '')
  const elements = []
  const hasImage = slideData.image_url && slideData.image_url.trim()
  const isTitle = index === 0

  const overlayOpacity = parseFloat(slideData.overlay_opacity || 0)
  if (overlayOpacity > 0 && slideData.bg_image) {
    const overlayColor = theme.mode === 'light'
      ? `rgba(255, 255, 255, ${overlayOpacity})`
      : `rgba(0, 0, 0, ${overlayOpacity})`
    elements.push(createShapeElement({
      x: 0, y: 0, width: CANVAS.width, height: CANVAS.height,
      shapeType: 'rect', fill: overlayColor,
      stroke: 'transparent', strokeWidth: 0,
    }))
  }

  const headingText = slideData.heading || (isTitle ? 'Template Title' : `Slide ${index + 1}`)
  const points = Array.isArray(slideData.points) ? slideData.points : []
  const description = slideData.description || ''
  const zones = computeTextImageZones({
    hasImage: !!hasImage,
    imageSide: 'right',
    heading: headingText,
    subheading: description,
    bulletPoints: points,
  })

  const contentX = zones.contentX
  const safeTop = isTitle ? 60 : 45
  const safeBottom = CANVAS.height - 40
  const contentW = zones.contentW

  // Dynamic heading size
  let headingSize = isTitle ? 38 : 28
  if (headingText.length > 60) headingSize = Math.max(headingSize - 10, 20)
  else if (headingText.length > 40) headingSize = Math.max(headingSize - 6, 22)

  let currentY = safeTop

  // Accent bar
  if (!isTitle) {
    elements.push(createShapeElement({
      x: contentX, y: currentY,
      width: 36, height: 4,
      shapeType: 'rect', fill: theme.palette.primary,
      stroke: 'transparent', strokeWidth: 0,
    }))
    currentY += 14
  }

  // Heading — dynamic height
  const headingH = estimateTextHeight(headingText, contentW, headingSize, 1.2)
  elements.push(createTextElement({
    x: contentX, y: currentY,
    width: contentW, height: headingH,
    text: headingText,
    fontSize: headingSize, fontWeight: 'bold',
    fontFamily: theme.fonts.heading,
    fill: slideData.text_color || theme.palette.text,
    lineHeight: 1.2,
  }))
  currentY += headingH + 12

  // Description
  if (description) {
    const descSize = 14
    const descH = estimateTextHeight(description, contentW, descSize, 1.4)
    elements.push(createTextElement({
      x: contentX, y: currentY,
      width: contentW, height: descH,
      text: description,
      fontSize: descSize, fontStyle: 'italic',
      fill: theme.palette.muted,
      lineHeight: 1.4,
    }))
    currentY += descH + 14
  }

  // Bullet points — auto-fit to remaining space
  if (points.length > 0) {
    const maxLines = Math.min(8, points.length)
    const pointsText = points.slice(0, maxLines).map(p => `•  ${p}`).join('\n')
    const remainingH = Math.max(40, safeBottom - currentY - 10)
    const pointsFont = autoFitFont(pointsText, contentW, remainingH, 15, 12, 1.5)
    const pointsH = Math.min(estimateTextHeight(pointsText, contentW, pointsFont, 1.5), remainingH)
    elements.push(createTextElement({
      x: contentX, y: currentY,
      width: contentW, height: pointsH,
      text: pointsText,
      fontSize: pointsFont,
      fill: theme.palette.text,
      lineHeight: 1.5,
    }))
  }

  // Image
  if (hasImage) {
    const imageHeight = safeBottom - safeTop
    elements.push(createImageElement({
      x: zones.imageX, y: safeTop,
      width: zones.imageW, height: imageHeight,
      src: slideData.image_url,
      borderRadius: 12,
    }))
  }

  const iconNames = slideData.icon_names || slideData.icons || []
  elements.push(...buildIconElements(iconNames, { y: 455, color: theme.palette.accent }))

  return {
    id: uid(),
    background: slideData.bg_color || theme.palette.background,
    backgroundImage: slideData.bg_image || '',
    elements,
  }
}

// ─── Convert new format back to legacy for backend compatibility ─
export function slidesToLegacyFormat(slides, title, themeOverride) {
  return {
    title,
    theme: themeOverride || 'dark',
    slides: slides.map(slide => {
      // Extract data from elements
      const textEls = slide.elements.filter(e => e.type === 'text')
      const imageEl = slide.elements.find(e => e.type === 'image')

      // Find heading (largest font or first text)
      const sorted = [...textEls].sort((a, b) => b.fontSize - a.fontSize)
      const headingEl = sorted[0]
      const otherTexts = sorted.slice(1)

      // Try to separate points from description
      let points = []
      let description = ''
      for (const el of otherTexts) {
        const text = el.text || ''
        if (text.includes('▸') || text.includes('•') || text.includes('\n')) {
          points = text.split('\n').map(l => l.replace(/^[▸•\-\s]+/, '').trim()).filter(Boolean)
        } else {
          description = text
        }
      }

      return {
        heading: headingEl?.text || '',
        points,
        description,
        transition: slide.transition || { type: 'fade', duration: 0.5 },
        image_query: slide.visual_elements?.image_query || '',
        image_url: imageEl?.src || '',
        bg_image: slide.backgroundImage || '',
        bg_color: slide.background || '#1a1a2e',
        text_color: headingEl?.fill || '#ffffff',
        font_family: headingEl?.fontFamily || 'Inter',
        font_size: (headingEl?.fontSize || 24) + 'px',
        alignment: headingEl?.textAlign || 'left',
        layout: slide.layout || 'default',
        slide_type: slide.slide_type || '',
        title: slide.title || '',
        content: slide.content || {},
        visual_elements: slide.visual_elements || {},
        icon_names: slide.elements
          .filter(e => e.type === 'image' && e.isIcon && e.iconName)
          .map(e => e.iconName),
        // Store the new element-based format too for re-loading
        _elements: slide.elements,
      }
    }),
  }
}

// ─── Convert legacy slides to new element-based format ─
export function legacySlidesToElements(legacySlides, deckTheme = null, deckTitle = '') {
  const resolvedTheme = resolveTheme(deckTheme, deckTitle || legacySlides?.[0]?.heading || '')
  const slides = legacySlides.map((s, i, arr) => {
    const bg = s.bg_color && s.bg_color !== '#1a1a2e' ? s.bg_color : resolvedTheme.palette.background
    const bgImage = s.bg_image || ''
    const transition = s.transition || { type: 'fade', duration: 0.5 }

    // If slide already has elements array, use it
    if (s._elements && Array.isArray(s._elements) && s._elements.length > 0) {
      return {
        id: uid(),
        background: bg,
        backgroundImage: bgImage,
        transition,
        elements: s._elements.map(el => ({ ...el, id: uid() })),
        slide_type: s.slide_type || '',
        layout: s.layout || '',
        content: s.content || {},
        visual_elements: s.visual_elements || {},
      }
    }

    const hasStructured = !!(s.content || s.slide_type || s.visual_elements)
    const hasPlaceholders =
      /{{[^}]+}}/.test(s.heading || '') ||
      /{{[^}]+}}/.test(s.description || '') ||
      (Array.isArray(s.points) && s.points.some(p => /{{[^}]+}}/.test(p || '')))

    if (hasStructured) {
      return {
        id: uid(),
        background: bg,
        backgroundImage: bgImage,
        transition,
        elements: layoutStructuredSlide(s, i, arr.length, resolvedTheme, { template: s.layout === 'template' || hasPlaceholders }),
        slide_type: s.slide_type || '',
        layout: s.layout || '',
        content: s.content || {},
        visual_elements: s.visual_elements || {},
      }
    }

    if (s.layout === 'template' || hasPlaceholders) {
      const slideObj = layoutTemplateSlide(s, i, arr.length, resolvedTheme)
      return {
        ...slideObj,
        background: slideObj.background || resolvedTheme.palette.background,
        backgroundImage: bgImage,
        transition,
        slide_type: s.slide_type || '',
        layout: s.layout || '',
        content: s.content || {},
        visual_elements: s.visual_elements || {},
      }
    }
    const slideObj = layoutAISlide(s, i, arr.length, resolvedTheme)
    return {
      ...slideObj,
      background: slideObj.background || resolvedTheme.palette.background,
      backgroundImage: bgImage || slideObj.backgroundImage || '',
      transition,
      slide_type: s.slide_type || '',
      layout: s.layout || '',
      content: s.content || {},
      visual_elements: s.visual_elements || {},
    }
  })

  return { slides, theme: resolvedTheme }
}


// ═══════════════════════════════════════════════════════════
//  PINIA STORE
// ═══════════════════════════════════════════════════════════
export const useEditorStore = defineStore('editor', () => {
  // ─── State ────────────────────────────────────────
  const presentationId = ref(null)
  const title = ref('Untitled Presentation')
  const theme = ref(null)
  const slides = ref([])
  const activeSlideIndex = ref(0)
  const activeElementId = ref(null)
  const clipboard = ref(null)
  const history = ref([])
  const historyIndex = ref(-1)
  const historyHashes = ref([])
  const applyingHistory = ref(false)
  const isDirty = ref(false)
  const changeTick = ref(0)

  // ─── Streaming generation state ───────────────────
  const isGenerating = ref(false)
  const streamedSlideCount = ref(0)
  const generationProgress = ref(0)
  const generationStage = ref('')
  const generationMessage = ref('')
  const totalExpectedSlides = ref(0)

  // ─── Computed ─────────────────────────────────────
  const activeSlide = computed(() => slides.value[activeSlideIndex.value] || null)
  const activeElement = computed(() => {
    if (!activeSlide.value || !activeElementId.value) return null
    return activeSlide.value.elements.find(e => e.id === activeElementId.value) || null
  })
  const totalSlides = computed(() => slides.value.length)
  const canUndo = computed(() => historyIndex.value > 0)
  const canRedo = computed(() => historyIndex.value >= 0 && historyIndex.value < history.value.length - 1)

  function markChanged() {
    isDirty.value = true
    changeTick.value += 1
  }

  function snapshotState() {
    return {
      title: title.value,
      theme: theme.value,
      slides: JSON.parse(JSON.stringify(slides.value)),
      activeSlideIndex: activeSlideIndex.value,
      activeElementId: activeElementId.value,
    }
  }

  function resetHistory() {
    const snap = snapshotState()
    history.value = [snap]
    historyHashes.value = [JSON.stringify(snap)]
    historyIndex.value = 0
  }

  function pushHistory() {
    if (applyingHistory.value) return
    const snap = snapshotState()
    const hash = JSON.stringify(snap)
    const currentHash = historyHashes.value[historyIndex.value]
    if (hash === currentHash) return
    if (historyIndex.value < history.value.length - 1) {
      history.value.splice(historyIndex.value + 1)
      historyHashes.value.splice(historyIndex.value + 1)
    }
    history.value.push(snap)
    historyHashes.value.push(hash)
    historyIndex.value = history.value.length - 1
  }

  function commitHistory() {
    pushHistory()
  }

  function applySnapshot(snap) {
    slides.value = snap.slides || []
    title.value = snap.title || 'Untitled Presentation'
    theme.value = snap.theme || theme.value
    activeSlideIndex.value = Math.min(snap.activeSlideIndex ?? 0, slides.value.length - 1)
    if (activeSlideIndex.value < 0) activeSlideIndex.value = 0
    const elId = snap.activeElementId || null
    const active = slides.value[activeSlideIndex.value]?.elements?.find(e => e.id === elId)
    activeElementId.value = active ? elId : null
  }

  function undo() {
    if (!canUndo.value) return
    applyingHistory.value = true
    historyIndex.value -= 1
    applySnapshot(history.value[historyIndex.value])
    markChanged()
    applyingHistory.value = false
  }

  function redo() {
    if (!canRedo.value) return
    applyingHistory.value = true
    historyIndex.value += 1
    applySnapshot(history.value[historyIndex.value])
    markChanged()
    applyingHistory.value = false
  }

  // ─── Slide operations ─────────────────────────────
  function setSlides(newSlides, newTitle, newTheme) {
    slides.value = newSlides
    title.value = newTitle || 'Untitled Presentation'
    theme.value = resolveTheme(newTheme, newTitle || '')
    activeSlideIndex.value = 0
    activeElementId.value = null
    isDirty.value = false
    resetHistory()
  }

  function addSlide(afterIndex = null) {
    const idx = afterIndex !== null ? afterIndex : activeSlideIndex.value
    const newSlide = createDefaultSlide({
      background: theme.value?.palette?.background || '#1a1a2e',
      elements: [
        createTextElement({
          x: 60, y: 180, width: 840, height: 70,
          text: 'New Slide',
          fontSize: 40, fontWeight: 'bold', fontFamily: 'Space Grotesk',
        }),
        createTextElement({
          x: 60, y: 270, width: 840, height: 40,
          text: 'Click to add content',
          fontSize: 20, fill: 'rgba(255,255,255,0.6)',
        }),
      ],
    })
    slides.value.splice(idx + 1, 0, newSlide)
    activeSlideIndex.value = idx + 1
    activeElementId.value = null
    markChanged()
    pushHistory()
  }

  function duplicateSlide(index) {
    const src = slides.value[index]
    if (!src) return
    const clone = JSON.parse(JSON.stringify(src))
    clone.id = uid()
    clone.elements.forEach(el => { el.id = uid() })
    slides.value.splice(index + 1, 0, clone)
    activeSlideIndex.value = index + 1
    markChanged()
    pushHistory()
  }

  function deleteSlide(index) {
    if (slides.value.length <= 1) return
    slides.value.splice(index, 1)
    if (activeSlideIndex.value >= slides.value.length) {
      activeSlideIndex.value = slides.value.length - 1
    }
    activeElementId.value = null
    markChanged()
    pushHistory()
  }

  function reorderSlides(fromIndex, toIndex) {
    const item = slides.value.splice(fromIndex, 1)[0]
    slides.value.splice(toIndex, 0, item)
    activeSlideIndex.value = toIndex
    markChanged()
    pushHistory()
  }

  function setActiveSlide(index) {
    activeSlideIndex.value = index
    activeElementId.value = null
  }

  function setSlideBackground(color) {
    if (activeSlide.value) {
      activeSlide.value.background = color
      markChanged()
      pushHistory()
    }
  }

  function setSlideBackgroundImage(src) {
    if (activeSlide.value) {
      activeSlide.value.backgroundImage = src || ''
      markChanged()
      pushHistory()
    }
  }

  function clearSlideBackgroundImage() {
    if (activeSlide.value) {
      activeSlide.value.backgroundImage = ''
      markChanged()
      pushHistory()
    }
  }

  // ─── Element operations ───────────────────────────
  function addElement(element) {
    if (!activeSlide.value) return
    activeSlide.value.elements.push(element)
    activeElementId.value = element.id
    markChanged()
    pushHistory()
  }

  function removeElement(elementId) {
    if (!activeSlide.value) return
    const idx = activeSlide.value.elements.findIndex(e => e.id === elementId)
    if (idx !== -1) {
      activeSlide.value.elements.splice(idx, 1)
      if (activeElementId.value === elementId) {
        activeElementId.value = null
      }
      markChanged()
      pushHistory()
    }
  }

  function updateElement(elementId, updates, options = {}) {
    if (!activeSlide.value) return
    const el = activeSlide.value.elements.find(e => e.id === elementId)
    if (el) {
      Object.assign(el, updates)
      markChanged()
      if (options.history !== false) pushHistory()
    }
  }

  function updateElementInSlide(slideIndex, elementId, updates, options = {}) {
    const slide = slides.value[slideIndex]
    if (!slide) return
    const el = slide.elements.find(e => e.id === elementId)
    if (el) {
      Object.assign(el, updates)
      markChanged()
      if (options.history !== false) pushHistory()
    }
  }

  function setActiveElement(elementId) {
    activeElementId.value = elementId
  }

  function clearSelection() {
    activeElementId.value = null
  }

  // ─── Layer operations ─────────────────────────────
  function bringForward(elementId) {
    if (!activeSlide.value) return
    const els = activeSlide.value.elements
    const idx = els.findIndex(e => e.id === elementId)
    if (idx < els.length - 1) {
      ;[els[idx], els[idx + 1]] = [els[idx + 1], els[idx]]
      markChanged()
      pushHistory()
    }
  }

  function sendBackward(elementId) {
    if (!activeSlide.value) return
    const els = activeSlide.value.elements
    const idx = els.findIndex(e => e.id === elementId)
    if (idx > 0) {
      ;[els[idx], els[idx - 1]] = [els[idx - 1], els[idx]]
      markChanged()
      pushHistory()
    }
  }

  function bringToFront(elementId) {
    if (!activeSlide.value) return
    const els = activeSlide.value.elements
    const idx = els.findIndex(e => e.id === elementId)
    if (idx !== -1 && idx < els.length - 1) {
      const el = els.splice(idx, 1)[0]
      els.push(el)
      markChanged()
      pushHistory()
    }
  }

  function sendToBack(elementId) {
    if (!activeSlide.value) return
    const els = activeSlide.value.elements
    const idx = els.findIndex(e => e.id === elementId)
    if (idx > 0) {
      const el = els.splice(idx, 1)[0]
      els.unshift(el)
      markChanged()
      pushHistory()
    }
  }

  // ─── Clipboard ────────────────────────────────────
  function copyElement(elementId) {
    if (!activeSlide.value) return
    const el = activeSlide.value.elements.find(e => e.id === elementId)
    if (el) {
      clipboard.value = JSON.parse(JSON.stringify(el))
    }
  }

  function pasteElement() {
    if (!clipboard.value || !activeSlide.value) return
    const clone = { ...clipboard.value, id: uid(), x: clipboard.value.x + 20, y: clipboard.value.y + 20 }
    activeSlide.value.elements.push(clone)
    activeElementId.value = clone.id
    markChanged()
    pushHistory()
  }

  function setTitle(newTitle, options = {}) {
    title.value = newTitle
    markChanged()
    if (options.history !== false) pushHistory()
  }

  function setTheme(newTheme, options = {}) {
    theme.value = newTheme
    markChanged()
    if (options.history !== false) pushHistory()
  }

  function applyTransitionToAll(transition) {
    if (!transition || !slides.value.length) return
    const next = {
      type: transition.type || 'fade',
      duration: Number.isFinite(transition.duration) ? transition.duration : 0.5,
    }
    slides.value.forEach((slide) => {
      slide.transition = { ...next }
    })
    markChanged()
    pushHistory()
  }

  // ─── Streaming generation methods ─────────────────

  /**
   * Initialize the editor for streaming generation mode.
   * Sets up empty state and marks as generating.
   */
  function initStreamingMode(genTitle, genTheme, expectedSlides) {
    slides.value = []
    title.value = genTitle || 'Generating...'
    theme.value = resolveTheme(genTheme, genTitle || '')
    activeSlideIndex.value = 0
    activeElementId.value = null
    presentationId.value = null
    isGenerating.value = true
    streamedSlideCount.value = 0
    totalExpectedSlides.value = expectedSlides || 0
    generationProgress.value = 0
    generationStage.value = 'content_generation'
    generationMessage.value = 'AI is generating content...'
    isDirty.value = false
    history.value = []
    historyIndex.value = -1
    historyHashes.value = []
  }

  function updateStreamingMeta(genTitle, genTheme, expectedSlides) {
    if (genTitle && typeof genTitle === 'string') {
      title.value = genTitle
    }
    if (genTheme) {
      theme.value = resolveTheme(genTheme, genTitle || title.value || '')
    }
    if (Number.isFinite(expectedSlides) && expectedSlides > 0) {
      totalExpectedSlides.value = expectedSlides
    }
  }

  /**
   * Upsert a streamed slide (placeholder or finalized) by index.
   * If index exists, replaces it; otherwise appends.
   */
  function appendStreamedSlide(rawSlideData, index = null, options = {}) {
    const resolvedTheme = theme.value || resolveTheme(null, title.value)
    const { slides: converted } = legacySlidesToElements(
      [rawSlideData],
      resolvedTheme,
      title.value
    )

    if (!converted.length) return

    const isPlaceholder = options.placeholder === true
    const targetIndex = Number.isInteger(index) && index >= 0 ? index : slides.value.length
    const newSlide = {
      ...converted[0],
      _streamIndex: targetIndex,
      _streamedAt: Date.now(),
      _isPlaceholder: isPlaceholder,
    }

    if (targetIndex < slides.value.length) {
      const prev = slides.value[targetIndex]
      if (prev?.id) newSlide.id = prev.id
      slides.value.splice(targetIndex, 1, newSlide)
    } else if (targetIndex === slides.value.length) {
      slides.value.push(newSlide)
    } else {
      while (slides.value.length < targetIndex) {
        slides.value.push(createDefaultSlide({
          elements: [
            createTextElement({
              x: 80,
              y: 220,
              width: 800,
              height: 60,
              text: 'Preparing slide...',
              fontSize: 28,
              textAlign: 'center',
            }),
          ],
          _isPlaceholder: true,
        }))
      }
      slides.value.push(newSlide)
    }

    streamedSlideCount.value = slides.value.length
    const shouldActivate = options.activate !== false
    if (shouldActivate) {
      activeSlideIndex.value = targetIndex
    }
    activeElementId.value = null
  }

  /**
   * Update generation progress during streaming.
   */
  function updateGenerationProgress(progress, stage, message) {
    generationProgress.value = progress || generationProgress.value
    generationStage.value = stage || generationStage.value
    generationMessage.value = message || generationMessage.value
  }

  /**
   * Finalize streaming mode after generation completes.
   */
  function finalizeGeneration(pptId) {
    isGenerating.value = false
    presentationId.value = pptId || null
    generationProgress.value = 100
    generationStage.value = 'done'
    generationMessage.value = 'Complete!'
    isDirty.value = false
    resetHistory()
  }

  /**
   * Handle generation error during streaming.
   */
  function handleGenerationError(message) {
    isGenerating.value = false
    generationStage.value = 'failed'
    generationMessage.value = message || 'Generation failed'
  }

  return {
    presentationId,
    title,
    theme,
    slides,
    activeSlideIndex,
    activeElementId,
    clipboard,
    isDirty,
    changeTick,
    canUndo,
    canRedo,
    activeSlide,
    activeElement,
    totalSlides,
    // Streaming generation state
    isGenerating,
    streamedSlideCount,
    generationProgress,
    generationStage,
    generationMessage,
    totalExpectedSlides,
    // Core methods
    setSlides,
    addSlide,
    duplicateSlide,
    deleteSlide,
    reorderSlides,
    setActiveSlide,
    setSlideBackground,
    setSlideBackgroundImage,
    clearSlideBackgroundImage,
    addElement,
    removeElement,
    updateElement,
    updateElementInSlide,
    setActiveElement,
    clearSelection,
    bringForward,
    sendBackward,
    bringToFront,
    sendToBack,
    copyElement,
    pasteElement,
    setTitle,
    setTheme,
    applyTransitionToAll,
    commitHistory,
    undo,
    redo,
    markChanged,
    // Streaming generation methods
    initStreamingMode,
    updateStreamingMeta,
    appendStreamedSlide,
    updateGenerationProgress,
    finalizeGeneration,
    handleGenerationError,
  }
})
