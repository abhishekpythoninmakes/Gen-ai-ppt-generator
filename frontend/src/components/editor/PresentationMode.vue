<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="present-overlay"
      @keydown.esc="$emit('close')"
      @keydown.right="next"
      @keydown.left="prev"
      @keydown.space.prevent="next"
      tabindex="0"
      ref="overlayRef"
    >
      <div class="present-slide-wrapper">
        <div class="present-slide-animate" :class="transitionClass" :style="transitionStyle" :key="currentIndex">
          <canvas ref="presentCanvas" :id="'present-canvas-' + currentIndex"></canvas>
        </div>
      </div>
      <div class="present-controls">
        <button @click="prev" :disabled="currentIndex === 0" class="present-nav-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15,18 9,12 15,6"/>
          </svg>
        </button>
        <span class="present-counter">{{ currentIndex + 1 }} / {{ slides.length }}</span>
        <button @click="next" :disabled="currentIndex === slides.length - 1" class="present-nav-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9,18 15,12 9,6"/>
          </svg>
        </button>
        <button @click="$emit('close')" class="present-exit-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
          Exit
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount, toRaw, computed } from 'vue'
import { fabric } from 'fabric'

const props = defineProps({
  visible: Boolean,
  slides: { type: Array, default: () => [] },
  startIndex: { type: Number, default: 0 },
})

const emit = defineEmits(['close'])

const overlayRef = ref(null)
const presentCanvas = ref(null)
const currentIndex = ref(0)
const transitionClass = ref('')
const direction = ref('next')
const transitionStyle = computed(() => {
  const tr = props.slides?.[currentIndex.value]?.transition || {}
  const duration = Number(tr.duration || 0.5)
  return { animationDuration: `${Math.max(0.2, Math.min(duration, 2.0))}s` }
})

let fcanvas = null

watch(() => props.visible, async (val) => {
  if (val) {
    currentIndex.value = props.startIndex
    transitionClass.value = ''
    await nextTick()
    overlayRef.value?.focus()
    initCanvas()
    renderCurrentSlide()
  } else {
    destroyCanvas()
  }
})

watch(currentIndex, async () => {
  const slide = props.slides[currentIndex.value]
  const tr = slide?.transition || { type: 'fade', duration: 0.5 }
  const animName = direction.value === 'next' ? getEnterAnimation(tr.type) : getEnterAnimationReverse(tr.type)

  transitionClass.value = ''
  await nextTick()
  transitionClass.value = animName

  await nextTick()
  initCanvas()
  renderCurrentSlide()
})

function getEnterAnimation(type) {
  const map = {
    'fade': 'anim-fade-in',
    'slide-left': 'anim-slide-left',
    'slide-right': 'anim-slide-right',
    'slide-up': 'anim-slide-up',
    'slide-down': 'anim-slide-down',
    'zoom-in': 'anim-zoom-in',
    'scale-fade': 'anim-scale-fade',
    'flip': 'anim-flip',
    'push': 'anim-push-left',
    'dissolve': 'anim-dissolve',
    'wipe': 'anim-wipe',
    'cover': 'anim-cover',
    'none': '',
  }
  return map[type] || 'anim-fade-in'
}

function getEnterAnimationReverse(type) {
  const map = {
    'fade': 'anim-fade-in',
    'slide-left': 'anim-slide-right',
    'slide-right': 'anim-slide-left',
    'slide-up': 'anim-slide-down',
    'slide-down': 'anim-slide-up',
    'zoom-in': 'anim-zoom-in',
    'scale-fade': 'anim-scale-fade',
    'flip': 'anim-flip',
    'push': 'anim-push-right',
    'dissolve': 'anim-dissolve',
    'wipe': 'anim-wipe-reverse',
    'cover': 'anim-cover-reverse',
    'none': '',
  }
  return map[type] || 'anim-fade-in'
}

function initCanvas() {
  if (fcanvas) fcanvas.dispose()
  const w = window.innerWidth
  const h = window.innerHeight - 60
  fcanvas = new fabric.StaticCanvas(presentCanvas.value, {
    width: w,
    height: h,
    backgroundColor: '#000',
  })
}

function destroyCanvas() {
  if (fcanvas) {
    fcanvas.dispose()
    fcanvas = null
  }
}

onBeforeUnmount(() => destroyCanvas())

function renderCurrentSlide() {
  if (!fcanvas || !props.slides[currentIndex.value]) return

  const slide = toRaw(props.slides[currentIndex.value])
  const cw = fcanvas.getWidth()
  const ch = fcanvas.getHeight()

  const scale = Math.min(cw / 960, ch / 540)
  const offsetX = (cw - 960 * scale) / 2
  const offsetY = (ch - 540 * scale) / 2

  fcanvas.clear()
  fcanvas.setBackgroundColor('#000', () => {})

  // Draw slide background
  const bgRect = new fabric.Rect({
    left: offsetX,
    top: offsetY,
    width: 960 * scale,
    height: 540 * scale,
    fill: slide.background || '#1a1a2e',
    selectable: false,
    evented: false,
  })
  fcanvas.add(bgRect)

  // Background image
  if (slide.backgroundImage) {
    const bgImgPromise = new Promise(resolve => {
      fabric.Image.fromURL(slide.backgroundImage, (img) => {
        if (!img) { resolve(); return }
        const sw = (960 * scale) / (img.width || 1)
        const sh = (540 * scale) / (img.height || 1)
        img.set({
          left: offsetX,
          top: offsetY,
          scaleX: sw,
          scaleY: sh,
          selectable: false,
          evented: false,
          opacity: 0.85,
        })
        fcanvas.add(img)
        resolve()
      }, { crossOrigin: 'anonymous' })
    })
    bgImgPromise.then(() => renderElements(slide, scale, offsetX, offsetY))
  } else {
    renderElements(slide, scale, offsetX, offsetY)
  }
}

function renderElements(slide, scale, offsetX, offsetY) {
  const elements = slide.elements || []
  let loadPromises = []

  elements.forEach(el => {
    if (el.type === 'text') {
      const obj = new fabric.Textbox(el.text || '', {
        left: offsetX + (el.x || 0) * scale,
        top: offsetY + (el.y || 0) * scale,
        width: (el.width || 300) * scale,
        fontSize: (el.fontSize || 24) * scale,
        fontFamily: el.fontFamily || 'Inter',
        fontWeight: el.fontWeight || 'normal',
        fontStyle: el.fontStyle || 'normal',
        underline: el.underline || false,
        fill: el.fill || '#ffffff',
        textAlign: el.textAlign || 'left',
        lineHeight: el.lineHeight || 1.3,
        opacity: el.opacity || 1,
        angle: el.rotation || 0,
        selectable: false,
        evented: false,
      })
      fcanvas.add(obj)
    } else if (el.type === 'image' && el.src) {
      loadPromises.push(new Promise(resolve => {
        fabric.Image.fromURL(el.src, (img) => {
          if (!img) { resolve(); return }
          const sw = (el.width || 300) * scale / (img.width || 1)
          const sh = (el.height || 200) * scale / (img.height || 1)
          img.set({
            left: offsetX + (el.x || 0) * scale,
            top: offsetY + (el.y || 0) * scale,
            scaleX: sw,
            scaleY: sh,
            opacity: el.opacity || 1,
            angle: el.rotation || 0,
            selectable: false,
            evented: false,
          })
          fcanvas.add(img)
          resolve()
        }, { crossOrigin: 'anonymous' })
      }))
    } else if (el.type === 'shape') {
      const obj = createShapeForPresent(el, scale, offsetX, offsetY)
      if (obj) fcanvas.add(obj)
    }
  })

  Promise.all(loadPromises).then(() => fcanvas.renderAll())
}

function createShapeForPresent(el, scale, ox, oy) {
  const common = {
    left: ox + (el.x || 0) * scale,
    top: oy + (el.y || 0) * scale,
    fill: el.fill || 'rgba(108,99,255,0.3)',
    stroke: el.stroke || '#6c63ff',
    strokeWidth: (el.strokeWidth || 2) * scale,
    opacity: el.opacity || 1,
    angle: el.rotation || 0,
    selectable: false,
    evented: false,
  }
  const w = (el.width || 200) * scale
  const h = (el.height || 200) * scale

  switch (el.shapeType) {
    case 'circle':
      return new fabric.Ellipse({ ...common, rx: w / 2, ry: h / 2 })
    case 'triangle':
      return new fabric.Triangle({ ...common, width: w, height: h })
    case 'rect':
    default:
      return new fabric.Rect({ ...common, width: w, height: h, rx: 8 * scale, ry: 8 * scale })
  }
}

function prev() {
  if (currentIndex.value > 0) {
    direction.value = 'prev'
    currentIndex.value--
  }
}

function next() {
  if (currentIndex.value < props.slides.length - 1) {
    direction.value = 'next'
    currentIndex.value++
  }
}
</script>

<style scoped>
.present-overlay {
  position: fixed;
  inset: 0;
  background: #000;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  outline: none;
}

.present-slide-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.present-slide-animate {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ─── Animations ──────────────────────────────────── */
.anim-fade-in {
  animation: fadeIn 0.5s ease-out both;
}

.anim-slide-left {
  animation: slideLeft 0.4s ease-out both;
}

.anim-slide-right {
  animation: slideRight 0.4s ease-out both;
}

.anim-slide-up {
  animation: slideUp 0.4s ease-out both;
}

.anim-slide-down {
  animation: slideDown 0.4s ease-out both;
}

.anim-zoom-in {
  animation: zoomIn 0.45s ease-out both;
}

.anim-scale-fade {
  animation: scaleFadeIn 0.45s ease-out both;
}

.anim-flip {
  animation: flipIn 0.5s ease-out both;
}

.anim-push-left {
  animation: pushLeft 0.35s ease-out both;
}

.anim-push-right {
  animation: pushRight 0.35s ease-out both;
}

.anim-dissolve {
  animation: dissolveIn 0.6s ease-out both;
}

.anim-wipe {
  animation: wipeRight 0.5s ease-out both;
}

.anim-wipe-reverse {
  animation: wipeLeft 0.5s ease-out both;
}

.anim-cover {
  animation: coverUp 0.4s ease-out both;
}

.anim-cover-reverse {
  animation: coverDown 0.4s ease-out both;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideLeft {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes slideRight {
  from { transform: translateX(-100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes slideDown {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes zoomIn {
  from { transform: scale(0.6); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

@keyframes scaleFadeIn {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

@keyframes flipIn {
  from { transform: perspective(1200px) rotateY(-90deg); opacity: 0; }
  to { transform: perspective(1200px) rotateY(0); opacity: 1; }
}

@keyframes pushLeft {
  from { transform: translateX(60%); opacity: 0.3; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes pushRight {
  from { transform: translateX(-60%); opacity: 0.3; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes dissolveIn {
  from { opacity: 0; filter: blur(8px); }
  to { opacity: 1; filter: blur(0); }
}

@keyframes wipeRight {
  from { clip-path: inset(0 100% 0 0); }
  to { clip-path: inset(0 0 0 0); }
}

@keyframes wipeLeft {
  from { clip-path: inset(0 0 0 100%); }
  to { clip-path: inset(0 0 0 0); }
}

@keyframes coverUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@keyframes coverDown {
  from { transform: translateY(-100%); }
  to { transform: translateY(0); }
}

/* ─── Controls ────────────────────────────────────── */
.present-controls {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: rgba(0, 0, 0, 0.9);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.present-nav-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.15s;
}
.present-nav-btn:hover:not(:disabled) {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}
.present-nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.present-counter {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.85rem;
  min-width: 60px;
  text-align: center;
}

.present-exit-btn {
  padding: 8px 16px;
  background: rgba(255, 71, 87, 0.15);
  border: 1px solid rgba(255, 71, 87, 0.4);
  color: #ff6b81;
  border-radius: 8px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s;
  margin-left: 16px;
}
.present-exit-btn:hover {
  background: #ff4757;
  color: white;
  border-color: #ff4757;
}
</style>
