<template>
  <div class="slide-canvas-wrapper" @click.self="onCanvasClick">
    <div class="canvas-container" ref="containerRef">
      <canvas ref="canvasEl" :id="canvasId"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick, toRaw } from 'vue'
import { fabric } from 'fabric'
import { useEditorStore } from '../../stores/editor'

const props = defineProps({
  canvasId: { type: String, default: 'slide-fabric-canvas' },
  width: { type: Number, default: 960 },
  height: { type: Number, default: 540 },
})

const emit = defineEmits(['element-selected', 'element-deselected', 'element-modified', 'canvas-ready', 'double-click-text'])

const store = useEditorStore()
const canvasEl = ref(null)
const containerRef = ref(null)

let canvas = null
let isUpdating = false // prevent circular updates
let renderToken = 0

// ─── Initialize Fabric Canvas ───────────────────────
onMounted(async () => {
  await nextTick()
  canvas = new fabric.Canvas(canvasEl.value, {
    width: props.width,
    height: props.height,
    backgroundColor: '#1a1a2e',
    selection: true,
    preserveObjectStacking: true,
    stopContextMenu: true,
    fireRightClick: true,
  })

  // Events
  canvas.on('selection:created', onSelectionCreated)
  canvas.on('selection:updated', onSelectionCreated)
  canvas.on('selection:cleared', onSelectionCleared)
  canvas.on('object:modified', onObjectModified)
  canvas.on('object:moving', onObjectMoving)
  canvas.on('text:changed', onTextChanged)
  canvas.on('text:editing:entered', onTextEditingEntered)
  canvas.on('text:editing:exited', onTextEditingExited)
  canvas.on('mouse:dblclick', onDoubleClick)

  emit('canvas-ready', canvas)

  // Initial render
  if (store.activeSlide) {
    renderSlide()
  }
})

onBeforeUnmount(() => {
  if (canvas) {
    canvas.off()
    canvas.dispose()
    canvas = null
  }
})

// ─── Watch for slide changes ────────────────────────
watch(() => store.activeSlideIndex, () => {
  renderSlide()
})

watch(() => store.activeSlide?.background, (newBg) => {
  if (canvas && newBg) {
    canvas.setBackgroundColor(newBg, () => canvas.renderAll())
  }
})

watch(() => store.activeSlide?.backgroundImage, () => {
  renderSlide()
})

watch(() => store.activeSlide?.elements, () => {
  if (!isUpdating) {
    renderSlide()
  }
}, { deep: true })

// Disable interaction during generation
watch(() => store.isGenerating, (generating) => {
  if (!canvas) return
  canvas.selection = !generating
  canvas.getObjects().forEach(obj => {
    obj.selectable = !generating
    obj.evented = !generating
  })
  canvas.renderAll()
})

// ─── Render entire slide ────────────────────────────
function renderSlide() {
  if (!canvas || !store.activeSlide) return
  isUpdating = true
  const token = ++renderToken

  canvas.clear()
  canvas.setBackgroundColor(store.activeSlide.background || '#1a1a2e', () => {})

  const elements = store.activeSlide.elements || []
  let loadPromises = []

  loadPromises.push(setBackgroundImage(store.activeSlide.backgroundImage || '', token))

  elements.forEach(el => {
    const raw = toRaw(el)
    if (raw.type === 'text') {
      loadPromises.push(Promise.resolve(addTextObject(raw)))
    } else if (raw.type === 'image') {
      loadPromises.push(addImageObject(raw, token))
    } else if (raw.type === 'shape') {
      loadPromises.push(Promise.resolve(addShapeObject(raw)))
    }
  })

  Promise.allSettled(loadPromises).then(() => {
    if (token !== renderToken) return
    syncZOrder(elements)
    canvas.renderAll()
    // Re-select active element if there was one
    if (store.activeElementId) {
      const obj = canvas.getObjects().find(o => o._elementId === store.activeElementId)
      if (obj) {
        canvas.setActiveObject(obj)
        canvas.renderAll()
      }
    }
    isUpdating = false
  }).catch(() => {
    isUpdating = false
  })
}

function setBackgroundImage(src, token) {
  return new Promise((resolve) => {
    if (!canvas) return resolve(null)
    if (!src) {
      canvas.setBackgroundImage(null, () => resolve(null))
      return
    }
    const callback = (img, isError) => {
      if (token !== renderToken || !canvas) {
        resolve(null)
        return
      }
      if (!img || isError) {
        canvas.setBackgroundImage(null, () => resolve(null))
        return
      }
      const scale = Math.max(props.width / (img.width || 1), props.height / (img.height || 1))
      img.set({
        originX: 'center',
        originY: 'center',
        left: props.width / 2,
        top: props.height / 2,
        scaleX: scale,
        scaleY: scale,
      })
      canvas.setBackgroundImage(img, () => resolve(img))
    }
    
    // Safety timeout
    setTimeout(() => resolve(null), 5000)

    fabric.Image.fromURL(src, callback, { crossOrigin: 'anonymous' })
  })
}

function syncZOrder(elements) {
  if (!canvas) return
  elements.forEach((el, idx) => {
    const obj = canvas.getObjects().find(o => o._elementId === el.id)
    if (obj) {
      canvas.moveTo(obj, idx)
    }
  })
}

// ─── Add Text Object ────────────────────────────────
function addTextObject(el) {
  const bgColor = el.backgroundColor || ''
  const bgOpacity = typeof el.backgroundOpacity === 'number' ? el.backgroundOpacity : 1
  const bgRgba = bgColor ? hexToRgba(bgColor, bgOpacity) : ''
  const textbox = new fabric.Textbox(el.text || 'Text', {
    left: el.x || 0,
    top: el.y || 0,
    width: el.width || 300,
    fontSize: el.fontSize || 24,
    fontFamily: el.fontFamily || 'Inter',
    fontWeight: el.fontWeight || 'normal',
    fontStyle: el.fontStyle || 'normal',
    underline: el.underline || false,
    fill: el.fill || '#ffffff',
    backgroundColor: bgRgba || '',
    textAlign: el.textAlign || 'left',
    lineHeight: el.lineHeight || 1.3,
    opacity: el.opacity !== undefined ? el.opacity : 1,
    angle: el.rotation || 0,
    selectable: !el.locked,
    evented: !el.locked,
    splitByGrapheme: false,
    lockScalingFlip: true,
    cornerStyle: 'circle',
    cornerColor: '#6c63ff',
    cornerSize: 10,
    transparentCorners: false,
    borderColor: '#6c63ff',
    borderScaleFactor: 2,
    padding: 8,
  })
  textbox._elementId = el.id
  textbox._elementType = 'text'
  canvas.add(textbox)
  return textbox
}

function hexToRgba(hex, alpha = 1) {
  if (!hex) return ''
  const cleaned = hex.replace('#', '')
  if (cleaned.length !== 6) return ''
  const r = parseInt(cleaned.slice(0, 2), 16)
  const g = parseInt(cleaned.slice(2, 4), 16)
  const b = parseInt(cleaned.slice(4, 6), 16)
  const a = Math.max(0, Math.min(1, alpha))
  return `rgba(${r}, ${g}, ${b}, ${a})`
}

// ─── Add Image Object ───────────────────────────────
function addImageObject(el, token) {
  return new Promise((resolve) => {
    if (!el.src) {
      // Placeholder for missing image
      const rect = new fabric.Rect({
        left: el.x || 0,
        top: el.y || 0,
        width: el.width || 300,
        height: el.height || 200,
        fill: '#2a2a4e',
        stroke: '#6c63ff',
        strokeWidth: 1,
        strokeDashArray: [5, 5],
        rx: el.borderRadius || 0,
        ry: el.borderRadius || 0,
        opacity: el.opacity || 1,
        angle: el.rotation || 0,
        selectable: !el.locked,
        evented: !el.locked,
        cornerStyle: 'circle',
        cornerColor: '#6c63ff',
        cornerSize: 10,
        transparentCorners: false,
        borderColor: '#6c63ff',
        borderScaleFactor: 2,
      })
      rect._elementId = el.id
      rect._elementType = 'image'
      rect._imageSrc = ''
      if (token === renderToken) {
        canvas.add(rect)
        resolve(rect)
      } else {
        resolve(null)
      }
      return
    }

    const callback = (img, isError) => {
      if (token !== renderToken || !canvas) {
        resolve(null)
        return
      }
      if (!img || isError) {
        // Aesthetic fallback placeholder
        const fallbackSvg = encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"><rect width="100%" height="100%" fill="#162447"/><circle cx="150" cy="90" r="40" fill="#1f4068"/><path d="M50,200 L120,110 L180,160 L240,100 L300,180 L300,200 Z" fill="#1a3c40"/></svg>`)
        fabric.Image.fromURL(`data:image/svg+xml;utf8,${fallbackSvg}`, (fbImg) => {
          if (!fbImg || !canvas) { resolve(null); return; }
          const scaleX = (el.width || 300) / (fbImg.width || 1)
          const scaleY = (el.height || 200) / (fbImg.height || 1)
          fbImg.set({
            left: el.x || 0,
            top: el.y || 0,
            scaleX,
            scaleY,
            opacity: el.opacity || 1,
            angle: el.rotation || 0,
            selectable: !el.locked,
            evented: !el.locked,
            cornerStyle: 'circle',
            cornerColor: '#6c63ff',
            cornerSize: 10,
            transparentCorners: false,
            borderColor: '#6c63ff',
            borderScaleFactor: 2,
            lockScalingFlip: true,
          })
          if (el.borderRadius) {
            fbImg.clipPath = new fabric.Rect({
              width: fbImg.width,
              height: fbImg.height,
              rx: el.borderRadius / scaleX,
              ry: el.borderRadius / scaleY,
              originX: 'center',
              originY: 'center',
            })
          }
          fbImg._elementId = el.id
          fbImg._elementType = 'image'
          fbImg._imageSrc = ''
          const existing = canvas.getObjects().find(o => o._elementId === el.id)
          if (existing) canvas.remove(existing)
          canvas.add(fbImg)
          resolve(fbImg)
        })
        return
      }
      const scaleX = (el.width || 300) / (img.width || 1)
      const scaleY = (el.height || 200) / (img.height || 1)
      img.set({
        left: el.x || 0,
        top: el.y || 0,
        scaleX,
        scaleY,
        opacity: el.opacity !== undefined ? el.opacity : 1,
        angle: el.rotation || 0,
        selectable: !el.locked,
        evented: !el.locked,
        cornerStyle: 'circle',
        cornerColor: '#6c63ff',
        cornerSize: 10,
        transparentCorners: false,
        borderColor: '#6c63ff',
        borderScaleFactor: 2,
        lockScalingFlip: true,
      })
      // Apply border radius via clipPath
      if (el.borderRadius) {
        img.clipPath = new fabric.Rect({
          width: img.width,
          height: img.height,
          rx: el.borderRadius / scaleX,
          ry: el.borderRadius / scaleY,
          originX: 'center',
          originY: 'center',
        })
      }
      if (el.shadow) {
        img.setShadow({
          color: 'rgba(0,0,0,0.4)',
          blur: 20,
          offsetX: 5,
          offsetY: 5,
        })
      }
      img._elementId = el.id
      img._elementType = 'image'
      img._imageSrc = el.src
      // Remove any stale object with same element id before adding
      const existing = canvas.getObjects().find(o => o._elementId === el.id)
      if (existing) canvas.remove(existing)
      canvas.add(img)
      resolve(img)
    }

    // Safety timeout
    setTimeout(() => resolve(null), 5000)

    fabric.Image.fromURL(el.src, callback, { crossOrigin: 'anonymous' })
  })
}

// ─── Add Shape Object ───────────────────────────────
function addShapeObject(el) {
  let shape
  const commonProps = {
    left: el.x || 0,
    top: el.y || 0,
    fill: el.fill || 'rgba(108, 99, 255, 0.3)',
    stroke: el.stroke || '#6c63ff',
    strokeWidth: el.strokeWidth || 2,
    opacity: el.opacity || 1,
    angle: el.rotation || 0,
    selectable: !el.locked,
    evented: !el.locked,
    cornerStyle: 'circle',
    cornerColor: '#6c63ff',
    cornerSize: 10,
    transparentCorners: false,
    borderColor: '#6c63ff',
    borderScaleFactor: 2,
    lockScalingFlip: true,
  }

  switch (el.shapeType) {
    case 'circle':
      shape = new fabric.Ellipse({
        ...commonProps,
        rx: (el.width || 200) / 2,
        ry: (el.height || 200) / 2,
      })
      break
    case 'triangle':
      shape = new fabric.Triangle({
        ...commonProps,
        width: el.width || 200,
        height: el.height || 200,
      })
      break
    case 'diamond': {
      const w = el.width || 200
      const h = el.height || 200
      const points = [
        { x: w / 2, y: 0 },
        { x: w, y: h / 2 },
        { x: w / 2, y: h },
        { x: 0, y: h / 2 },
      ]
      shape = new fabric.Polygon(points, { ...commonProps })
      break
    }
    case 'hexagon': {
      const w = el.width || 200
      const h = el.height || 200
      const points = [
        { x: w * 0.25, y: 0 },
        { x: w * 0.75, y: 0 },
        { x: w, y: h / 2 },
        { x: w * 0.75, y: h },
        { x: w * 0.25, y: h },
        { x: 0, y: h / 2 },
      ]
      shape = new fabric.Polygon(points, { ...commonProps })
      break
    }
    case 'line':
      shape = new fabric.Line([0, 0, el.width || 200, 0], {
        ...commonProps,
        fill: '',
        strokeWidth: el.strokeWidth || 3,
      })
      break
    case 'arrow': {
      const aw = el.width || 200
      const arrowPoints = [
        { x: 0, y: 10 },
        { x: aw - 20, y: 10 },
        { x: aw - 20, y: 0 },
        { x: aw, y: 15 },
        { x: aw - 20, y: 30 },
        { x: aw - 20, y: 20 },
        { x: 0, y: 20 },
      ]
      shape = new fabric.Polygon(arrowPoints, { ...commonProps })
      break
    }
    default: // rect
      shape = new fabric.Rect({
        ...commonProps,
        width: el.width || 200,
        height: el.height || 200,
        rx: 8,
        ry: 8,
      })
  }

  shape._elementId = el.id
  shape._elementType = 'shape'
  canvas.add(shape)
  return shape
}

// ─── Event handlers ─────────────────────────────────
function onSelectionCreated(e) {
  if (isUpdating) return
  const obj = e.selected?.[0]
  if (obj?._elementId) {
    store.setActiveElement(obj._elementId)
    emit('element-selected', obj._elementId)
  }
}

function onSelectionCleared() {
  if (isUpdating) return
  store.clearSelection()
  emit('element-deselected')
}

function onObjectModified(e) {
  const obj = e.target
  if (!obj?._elementId) return

  isUpdating = true
  const updates = {
    x: Math.round(obj.left),
    y: Math.round(obj.top),
    rotation: Math.round(obj.angle || 0),
  }

  if (obj._elementType === 'text') {
    updates.width = Math.round(obj.width * (obj.scaleX || 1))
    updates.height = Math.round(obj.height * (obj.scaleY || 1))
    updates.text = obj.text
    // Reset scale after applying to width/height
    obj.set({ scaleX: 1, scaleY: 1 })
    obj.set({ width: updates.width })
  } else if (obj._elementType === 'image') {
    updates.width = Math.round((obj.width || 0) * (obj.scaleX || 1))
    updates.height = Math.round((obj.height || 0) * (obj.scaleY || 1))
  } else if (obj._elementType === 'shape') {
    if (obj.type === 'ellipse') {
      updates.width = Math.round((obj.rx || 0) * 2 * (obj.scaleX || 1))
      updates.height = Math.round((obj.ry || 0) * 2 * (obj.scaleY || 1))
    } else {
      updates.width = Math.round((obj.width || 0) * (obj.scaleX || 1))
      updates.height = Math.round((obj.height || 0) * (obj.scaleY || 1))
    }
  }

  store.updateElement(obj._elementId, updates)
  emit('element-modified', obj._elementId, updates)

  nextTick(() => { isUpdating = false })
}

function onObjectMoving(e) {
  // Snap to edges (optional enhancement)
  const obj = e.target
  const snap = 10
  if (Math.abs(obj.left) < snap) obj.left = 0
  if (Math.abs(obj.top) < snap) obj.top = 0
  if (Math.abs(obj.left + obj.getScaledWidth() - props.width) < snap) {
    obj.left = props.width - obj.getScaledWidth()
  }
  if (Math.abs(obj.top + obj.getScaledHeight() - props.height) < snap) {
    obj.top = props.height - obj.getScaledHeight()
  }
}

function onTextChanged(e) {
  const obj = e.target
  if (!obj?._elementId) return

  isUpdating = true
  const updates = {
    text: obj.text,
    width: Math.round((obj.width || 0) * (obj.scaleX || 1)),
    height: Math.round((obj.height || 0) * (obj.scaleY || 1)),
  }
  store.updateElement(obj._elementId, updates, { history: false })
  emit('element-modified', obj._elementId, updates)
  nextTick(() => { isUpdating = false })
}

function onTextEditingExited(e) {
  const obj = e.target
  if (!obj?._elementId) return
  store.commitHistory()
}

function onTextEditingEntered(e) {
  const obj = e.target
  if (!obj?._elementId) return
  store.setActiveElement(obj._elementId)
  emit('element-selected', obj._elementId)
}

function onDoubleClick(e) {
  const obj = canvas.findTarget(e.e)
  if (obj?._elementType === 'text') {
    emit('double-click-text', obj._elementId, obj)
  }
}

function onCanvasClick() {
  if (canvas) {
    canvas.discardActiveObject()
    canvas.renderAll()
  }
  store.clearSelection()
  emit('element-deselected')
}

// ─── Public methods (exposed to parent) ─────────────
function getCanvas() {
  return canvas
}

function refreshCanvas() {
  renderSlide()
}

function selectElement(elementId) {
  if (!canvas) return
  const obj = canvas.getObjects().find(o => o._elementId === elementId)
  if (obj) {
    canvas.setActiveObject(obj)
    canvas.renderAll()
  }
}

function deleteSelected() {
  if (!canvas) return
  const active = canvas.getActiveObject()
  if (active?._elementId) {
    store.removeElement(active._elementId)
  }
}

function exportToDataURL() {
  if (!canvas) return ''
  return canvas.toDataURL({ format: 'png', multiplier: 0.3 })
}

defineExpose({
  getCanvas,
  refreshCanvas,
  selectElement,
  deleteSelected,
  exportToDataURL,
  renderSlide,
})
</script>

<style scoped>
.slide-canvas-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 24px;
  background: #080818;
  overflow: auto;
  min-height: 0;
}

.canvas-container {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(108, 99, 255, 0.08);
  flex-shrink: 0;
}

.canvas-container :deep(.canvas-container) {
  border-radius: 8px;
}
</style>
