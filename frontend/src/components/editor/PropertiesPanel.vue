<template>
  <div class="props-panel">
    <!-- No selection state -->
    <template v-if="!store.activeElement">
      <div class="panel-section">
        <h3 class="section-title">Slide</h3>
        <div class="prop-row">
          <label>Background</label>
          <div class="color-row">
            <input type="color" :value="store.activeSlide?.background || '#1a1a2e'" @input="store.setSlideBackground($event.target.value)" class="color-swatch" />
            <input type="text" :value="store.activeSlide?.background || '#1a1a2e'" @change="store.setSlideBackground($event.target.value)" class="prop-input color-hex" />
          </div>
        </div>
        <div class="prop-row">
          <label>Quick Colors</label>
          <div class="preset-grid">
            <button
              v-for="c in presetBgs"
              :key="c"
              class="preset-btn"
              :class="{ active: store.activeSlide?.background === c }"
              :style="{ background: c }"
              @click="store.setSlideBackground(c)"
            ></button>
          </div>
        </div>

        <div class="prop-row">
          <label>Background Image</label>
          <div class="bg-image-row">
            <div v-if="store.activeSlide?.backgroundImage" class="bg-thumb">
              <img :src="store.activeSlide.backgroundImage" alt="Background" />
            </div>
            <div v-else class="bg-thumb empty">No Image</div>
          </div>
          <div class="bg-actions">
            <button class="replace-btn" @click="$emit('background-image')">Add / Change</button>
            <button v-if="store.activeSlide?.backgroundImage" class="replace-btn danger" @click="$emit('clear-background-image')">Remove</button>
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">
          <span style="display:flex;align-items:center;gap:6px">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>
            </svg>
            Slide Transition
          </span>
        </h3>
        <div class="prop-row">
          <label>Animation</label>
          <select class="prop-input" :value="currentTransition" @change="setTransitionType($event.target.value)">
            <option value="none">None</option>
            <option value="fade">Fade</option>
            <option value="slide-left">Slide Left</option>
            <option value="slide-right">Slide Right</option>
            <option value="slide-up">Slide Up</option>
            <option value="slide-down">Slide Down</option>
            <option value="zoom-in">Zoom In</option>
            <option value="scale-fade">Scale Fade</option>
            <option value="flip">Flip</option>
            <option value="push">Push</option>
            <option value="dissolve">Dissolve</option>
            <option value="wipe">Wipe</option>
            <option value="cover">Cover</option>
          </select>
        </div>
        <div class="prop-row">
          <label>Duration</label>
          <div class="slider-row">
            <input type="range" min="0.2" max="2.0" step="0.1" :value="currentDuration" @input="setTransitionDuration(parseFloat($event.target.value))" class="prop-range" />
            <span class="range-value">{{ currentDuration.toFixed(1) }}s</span>
          </div>
        </div>
        <div class="transition-preview-grid">
          <button
            v-for="preset in animationPresets"
            :key="preset.type"
            class="transition-preset-btn"
            :class="{ active: currentTransition === preset.type }"
            @click="setTransitionType(preset.type)"
            :title="preset.label"
          >
            <span class="preset-icon">{{ preset.icon }}</span>
            <span class="preset-label">{{ preset.label }}</span>
          </button>
        </div>
        <div class="prop-row" style="margin-top: 8px;">
          <button class="replace-btn" @click="applyTransitionToAll">
            Apply To All Slides
          </button>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">Add Elements</h3>
        <div class="quick-add-grid">
          <button class="quick-add-btn" @click="addHeading">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 7V4h16v3"/><line x1="12" y1="4" x2="12" y2="20"/>
            </svg>
            Heading
          </button>
          <button class="quick-add-btn" @click="addBody">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/>
              <line x1="21" y1="14" x2="3" y2="14"/><line x1="17" y1="18" x2="3" y2="18"/>
            </svg>
            Body
          </button>
          <button class="quick-add-btn" @click="$emit('add-image')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21,15 16,10 5,21"/>
            </svg>
            Image
          </button>
          <button class="quick-add-btn" @click="$emit('add-icon')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2l3 6 6 .9-4.5 4.4 1.1 6.2L12 17l-5.6 2.5 1.1-6.2L3 8.9 9 8z"/>
            </svg>
            Icon
          </button>
          <button class="quick-add-btn" @click="addRect">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
            </svg>
            Shape
          </button>
        </div>
      </div>
    </template>

    <!-- Text element properties -->
    <template v-else-if="store.activeElement.type === 'text'">
      <div class="panel-section">
        <h3 class="section-title">
          Text
          <button class="section-action" @click="$emit('delete-element')" title="Delete">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2 2 0 01-2,2H7a2 2 0 01-2-2V6m3,0V4a2 2 0 012-2h4a2 2 0 012,2v2"/>
            </svg>
          </button>
        </h3>

        <div class="prop-row">
          <label>Content</label>
          <textarea
            class="prop-textarea"
            :value="store.activeElement.text"
            @input="store.updateElement(store.activeElementId, { text: $event.target.value })"
            rows="4"
          ></textarea>
        </div>

        <div class="prop-row">
          <label>Font</label>
          <select class="prop-input" :value="store.activeElement.fontFamily" @change="store.updateElement(store.activeElementId, { fontFamily: $event.target.value })">
            <option value="Inter">Inter</option>
            <option value="Space Grotesk">Space Grotesk</option>
            <option value="Manrope">Manrope</option>
            <option value="Sora">Sora</option>
            <option value="DM Sans">DM Sans</option>
            <option value="Playfair Display">Playfair Display</option>
            <option value="Georgia">Georgia</option>
            <option value="Arial">Arial</option>
            <option value="Courier New">Courier New</option>
            <option value="Verdana">Verdana</option>
            <option value="Times New Roman">Times New Roman</option>
            <option value="Roboto">Roboto</option>
          </select>
        </div>

        <div class="prop-row two-col">
          <div>
            <label>Size</label>
            <input type="number" class="prop-input" :value="store.activeElement.fontSize" @input="store.updateElement(store.activeElementId, { fontSize: parseInt($event.target.value) || 24 })" min="8" max="200" />
          </div>
          <div>
            <label>Line H</label>
            <input type="number" class="prop-input" :value="store.activeElement.lineHeight" @input="store.updateElement(store.activeElementId, { lineHeight: parseFloat($event.target.value) || 1.3 })" min="0.5" max="3" step="0.1" />
          </div>
        </div>

        <div class="prop-row">
          <label>Color</label>
          <div class="color-row">
            <input type="color" :value="store.activeElement.fill" @input="store.updateElement(store.activeElementId, { fill: $event.target.value })" class="color-swatch" />
            <input type="text" :value="store.activeElement.fill" @change="store.updateElement(store.activeElementId, { fill: $event.target.value })" class="prop-input color-hex" />
          </div>
        </div>

        <div class="prop-row">
          <label>Background</label>
          <div class="color-row">
            <input type="color" :value="store.activeElement.backgroundColor || '#000000'" @input="store.updateElement(store.activeElementId, { backgroundColor: $event.target.value })" class="color-swatch" />
            <input type="text" :value="store.activeElement.backgroundColor || ''" @change="store.updateElement(store.activeElementId, { backgroundColor: $event.target.value })" class="prop-input color-hex" placeholder="#000000" />
          </div>
        </div>

        <div class="prop-row">
          <label>Bg Opacity</label>
          <div class="slider-row">
            <input type="range" min="0" max="1" step="0.05" :value="store.activeElement.backgroundOpacity ?? 0.6" @input="store.updateElement(store.activeElementId, { backgroundOpacity: parseFloat($event.target.value) })" class="prop-range" />
            <span class="range-value">{{ Math.round(((store.activeElement.backgroundOpacity ?? 0.6)) * 100) }}%</span>
          </div>
        </div>

        <div class="prop-row">
          <label>Opacity</label>
          <div class="slider-row">
            <input type="range" min="0" max="1" step="0.05" :value="store.activeElement.opacity" @input="store.updateElement(store.activeElementId, { opacity: parseFloat($event.target.value) })" class="prop-range" />
            <span class="range-value">{{ Math.round((store.activeElement.opacity || 1) * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">Position</h3>
        <div class="prop-row two-col">
          <div>
            <label>X</label>
            <input type="number" class="prop-input" :value="store.activeElement.x" @input="store.updateElement(store.activeElementId, { x: parseInt($event.target.value) || 0 })" />
          </div>
          <div>
            <label>Y</label>
            <input type="number" class="prop-input" :value="store.activeElement.y" @input="store.updateElement(store.activeElementId, { y: parseInt($event.target.value) || 0 })" />
          </div>
        </div>
        <div class="prop-row two-col">
          <div>
            <label>Width</label>
            <input type="number" class="prop-input" :value="store.activeElement.width" @input="store.updateElement(store.activeElementId, { width: parseInt($event.target.value) || 100 })" />
          </div>
          <div>
            <label>Rotation</label>
            <input type="number" class="prop-input" :value="store.activeElement.rotation || 0" @input="store.updateElement(store.activeElementId, { rotation: parseInt($event.target.value) || 0 })" />
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">Layer</h3>
        <div class="layer-btns">
          <button class="layer-btn" @click="store.bringToFront(store.activeElementId)" title="Bring to Front">⬆ Front</button>
          <button class="layer-btn" @click="store.bringForward(store.activeElementId)" title="Bring Forward">↑ Up</button>
          <button class="layer-btn" @click="store.sendBackward(store.activeElementId)" title="Send Backward">↓ Down</button>
          <button class="layer-btn" @click="store.sendToBack(store.activeElementId)" title="Send to Back">⬇ Back</button>
        </div>
      </div>
    </template>

    <!-- Image element properties -->
    <template v-else-if="store.activeElement.type === 'image'">
      <div class="panel-section">
        <h3 class="section-title">
          {{ isIconElement ? 'Icon' : 'Image' }}
          <button class="section-action" @click="$emit('delete-element')" title="Delete">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2 2 0 01-2,2H7a2 2 0 01-2-2V6m3,0V4a2 2 0 012-2h4a2 2 0 012,2v2"/>
            </svg>
          </button>
        </h3>

        <div class="prop-row" v-if="!isIconElement">
          <label>Image URL</label>
          <input type="text" class="prop-input" :value="store.activeElement.src" @change="store.updateElement(store.activeElementId, { src: $event.target.value })" placeholder="https://..." />
        </div>

        <div class="prop-row" v-if="!isIconElement">
          <label>Search Image</label>
          <div class="search-row">
            <input type="text" class="prop-input" v-model="imageQuery" placeholder="Search..." @keydown.enter="$emit('search-image', imageQuery)" />
            <button class="search-btn" @click="$emit('search-image', imageQuery)">🔍</button>
          </div>
        </div>

        <button v-if="!isIconElement" class="replace-btn" @click="$emit('replace-image')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          Replace Image
        </button>

        <div class="prop-row" v-if="isIconElement">
          <label>Icon Color</label>
          <div class="color-row">
            <input type="color" :value="store.activeElement.iconColor || '#ffffff'" @input="$emit('icon-color', $event.target.value)" class="color-swatch" />
            <input type="text" :value="store.activeElement.iconColor || '#ffffff'" @change="$emit('icon-color', $event.target.value)" class="prop-input color-hex" />
          </div>
        </div>

        <div class="prop-row">
          <label>Opacity</label>
          <div class="slider-row">
            <input type="range" min="0" max="1" step="0.05" :value="store.activeElement.opacity" @input="store.updateElement(store.activeElementId, { opacity: parseFloat($event.target.value) })" class="prop-range" />
            <span class="range-value">{{ Math.round((store.activeElement.opacity || 1) * 100) }}%</span>
          </div>
        </div>

        <div class="prop-row">
          <label>Border Radius</label>
          <div class="slider-row">
            <input type="range" min="0" max="50" step="1" :value="store.activeElement.borderRadius || 0" @input="store.updateElement(store.activeElementId, { borderRadius: parseInt($event.target.value) })" class="prop-range" />
            <span class="range-value">{{ store.activeElement.borderRadius || 0 }}px</span>
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">Position & Size</h3>
        <div class="prop-row two-col">
          <div>
            <label>X</label>
            <input type="number" class="prop-input" :value="store.activeElement.x" @input="store.updateElement(store.activeElementId, { x: parseInt($event.target.value) || 0 })" />
          </div>
          <div>
            <label>Y</label>
            <input type="number" class="prop-input" :value="store.activeElement.y" @input="store.updateElement(store.activeElementId, { y: parseInt($event.target.value) || 0 })" />
          </div>
        </div>
        <div class="prop-row two-col">
          <div>
            <label>Width</label>
            <input type="number" class="prop-input" :value="store.activeElement.width" @input="store.updateElement(store.activeElementId, { width: parseInt($event.target.value) || 100 })" />
          </div>
          <div>
            <label>Height</label>
            <input type="number" class="prop-input" :value="store.activeElement.height" @input="store.updateElement(store.activeElementId, { height: parseInt($event.target.value) || 100 })" />
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">Layer</h3>
        <div class="layer-btns">
          <button class="layer-btn" @click="store.bringToFront(store.activeElementId)">⬆ Front</button>
          <button class="layer-btn" @click="store.bringForward(store.activeElementId)">↑ Up</button>
          <button class="layer-btn" @click="store.sendBackward(store.activeElementId)">↓ Down</button>
          <button class="layer-btn" @click="store.sendToBack(store.activeElementId)">⬇ Back</button>
        </div>
      </div>
    </template>

    <!-- Shape element properties -->
    <template v-else-if="store.activeElement.type === 'shape'">
      <div class="panel-section">
        <h3 class="section-title">
          Shape
          <button class="section-action" @click="$emit('delete-element')" title="Delete">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2 2 0 01-2,2H7a2 2 0 01-2-2V6m3,0V4a2 2 0 012-2h4a2 2 0 012,2v2"/>
            </svg>
          </button>
        </h3>

        <div class="prop-row">
          <label>Type</label>
          <select class="prop-input" :value="store.activeElement.shapeType" @change="store.updateElement(store.activeElementId, { shapeType: $event.target.value })">
            <option value="rect">Rectangle</option>
            <option value="circle">Ellipse</option>
            <option value="triangle">Triangle</option>
            <option value="diamond">Diamond</option>
            <option value="arrow">Arrow</option>
            <option value="line">Line</option>
            <option value="hexagon">Hexagon</option>
          </select>
        </div>

        <div class="prop-row">
          <label>Fill Color</label>
          <div class="color-row">
            <input type="color" :value="store.activeElement.fill || '#6c63ff'" @input="store.updateElement(store.activeElementId, { fill: $event.target.value })" class="color-swatch" />
            <input type="text" :value="store.activeElement.fill" @change="store.updateElement(store.activeElementId, { fill: $event.target.value })" class="prop-input color-hex" />
          </div>
        </div>

        <div class="prop-row">
          <label>Stroke</label>
          <div class="color-row">
            <input type="color" :value="store.activeElement.stroke || '#6c63ff'" @input="store.updateElement(store.activeElementId, { stroke: $event.target.value })" class="color-swatch" />
            <input type="number" class="prop-input" style="width: 60px;" :value="store.activeElement.strokeWidth || 2" @input="store.updateElement(store.activeElementId, { strokeWidth: parseInt($event.target.value) || 1 })" min="0" max="20" />
          </div>
        </div>

        <div class="prop-row">
          <label>Opacity</label>
          <div class="slider-row">
            <input type="range" min="0" max="1" step="0.05" :value="store.activeElement.opacity" @input="store.updateElement(store.activeElementId, { opacity: parseFloat($event.target.value) })" class="prop-range" />
            <span class="range-value">{{ Math.round((store.activeElement.opacity || 1) * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">Position & Size</h3>
        <div class="prop-row two-col">
          <div>
            <label>X</label>
            <input type="number" class="prop-input" :value="store.activeElement.x" @input="store.updateElement(store.activeElementId, { x: parseInt($event.target.value) || 0 })" />
          </div>
          <div>
            <label>Y</label>
            <input type="number" class="prop-input" :value="store.activeElement.y" @input="store.updateElement(store.activeElementId, { y: parseInt($event.target.value) || 0 })" />
          </div>
        </div>
        <div class="prop-row two-col">
          <div>
            <label>Width</label>
            <input type="number" class="prop-input" :value="store.activeElement.width" @input="store.updateElement(store.activeElementId, { width: parseInt($event.target.value) || 100 })" />
          </div>
          <div>
            <label>Height</label>
            <input type="number" class="prop-input" :value="store.activeElement.height" @input="store.updateElement(store.activeElementId, { height: parseInt($event.target.value) || 100 })" />
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">Layer</h3>
        <div class="layer-btns">
          <button class="layer-btn" @click="store.bringToFront(store.activeElementId)">⬆ Front</button>
          <button class="layer-btn" @click="store.bringForward(store.activeElementId)">↑ Up</button>
          <button class="layer-btn" @click="store.sendBackward(store.activeElementId)">↓ Down</button>
          <button class="layer-btn" @click="store.sendToBack(store.activeElementId)">⬇ Back</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useEditorStore, createTextElement, createShapeElement } from '../../stores/editor'

const emit = defineEmits(['add-image', 'add-icon', 'replace-image', 'search-image', 'delete-element', 'background-image', 'clear-background-image', 'icon-color'])
const store = useEditorStore()

const imageQuery = ref('')
const isIconElement = computed(() => {
  const el = store.activeElement
  if (!el) return false
  if (el.isIcon) return true
  if (el.iconName) return true
  if (el.src && el.src.includes('api.iconify.design')) return true
  return false
})

// ─── Animation presets ──────────────────────────────
const animationPresets = [
  { type: 'none', label: 'None', icon: '⊘' },
  { type: 'fade', label: 'Fade', icon: '◐' },
  { type: 'slide-left', label: 'Slide ←', icon: '⟵' },
  { type: 'slide-right', label: 'Slide →', icon: '⟶' },
  { type: 'slide-up', label: 'Slide ↑', icon: '↑' },
  { type: 'slide-down', label: 'Slide ↓', icon: '↓' },
  { type: 'zoom-in', label: 'Zoom', icon: '⊕' },
  { type: 'scale-fade', label: 'Scale', icon: '◎' },
  { type: 'flip', label: 'Flip', icon: '⟲' },
  { type: 'push', label: 'Push', icon: '⤳' },
  { type: 'dissolve', label: 'Dissolve', icon: '✦' },
  { type: 'wipe', label: 'Wipe', icon: '▸' },
  { type: 'cover', label: 'Cover', icon: '⬆' },
]

const currentTransition = computed(() => {
  return store.activeSlide?.transition?.type || 'fade'
})

const currentDuration = computed(() => {
  return store.activeSlide?.transition?.duration || 0.5
})

function setTransitionType(type) {
  if (!store.activeSlide) return
  const current = store.activeSlide.transition || { type: 'fade', duration: 0.5 }
  store.activeSlide.transition = { ...current, type }
  store.markChanged?.()
  store.commitHistory?.()
}

function setTransitionDuration(duration) {
  if (!store.activeSlide) return
  const current = store.activeSlide.transition || { type: 'fade', duration: 0.5 }
  store.activeSlide.transition = { ...current, duration }
  store.markChanged?.()
  store.commitHistory?.()
}

function applyTransitionToAll() {
  const transition = {
    type: currentTransition.value,
    duration: currentDuration.value,
  }
  store.applyTransitionToAll?.(transition)
}

const presetBgs = [
  '#0a0a1a', '#1a1a2e', '#16213e', '#0f3460',
  '#1b1b2f', '#162447', '#1f4068', '#1a3c40',
  '#2d132c', '#3d0c11', '#1a0a2e', '#0d1b2a',
  '#ffffff', '#f0f0f0', '#fdf6e3', '#282c35',
  '#1e3a5f', '#2c3e50', '#27ae60', '#8e44ad',
]

function addHeading() {
  store.addElement(createTextElement({
    x: 60,
    y: 60 + store.activeSlide.elements.length * 20,
    width: 840,
    height: 70,
    text: 'Heading',
    fontSize: 40,
    fontWeight: 'bold',
    fontFamily: 'Space Grotesk',
  }))
}

function addBody() {
  store.addElement(createTextElement({
    x: 60,
    y: 200 + store.activeSlide.elements.length * 20,
    width: 840,
    height: 120,
    text: 'Body text goes here. Click to edit.',
    fontSize: 20,
    fill: 'rgba(255,255,255,0.8)',
  }))
}

function addRect() {
  store.addElement(createShapeElement({
    x: 300 + Math.random() * 100,
    y: 150 + Math.random() * 100,
    width: 200,
    height: 150,
    shapeType: 'rect',
  }))
}
</script>

<style scoped>
.props-panel {
  width: 280px;
  min-width: 280px;
  border-left: 1px solid var(--border-color);
  background: var(--bg-secondary);
  overflow-y: auto;
  padding: 0;
}

.panel-section {
  padding: 16px 14px;
  border-bottom: 1px solid var(--border-color);
}

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-action {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  transition: all 0.12s;
}
.section-action:hover {
  color: #ff6b81;
  background: rgba(255, 71, 87, 0.1);
}

.prop-row {
  margin-bottom: 12px;
}

.prop-row label {
  display: block;
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-bottom: 5px;
  font-weight: 500;
}

.prop-input {
  width: 100%;
  padding: 7px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  font-size: 0.8rem;
  font-family: var(--font-sans);
  outline: none;
  transition: border-color 0.15s;
}
.prop-input:focus {
  border-color: var(--accent-primary);
}

.prop-textarea {
  width: 100%;
  padding: 8px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  font-size: 0.8rem;
  font-family: var(--font-sans);
  outline: none;
  resize: vertical;
  min-height: 60px;
  line-height: 1.4;
  transition: border-color 0.15s;
}
.prop-textarea:focus {
  border-color: var(--accent-primary);
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.color-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-swatch {
  width: 32px;
  height: 32px;
  border: 2px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  background: none;
  padding: 2px;
  flex-shrink: 0;
}

.color-hex {
  flex: 1;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.prop-range {
  flex: 1;
  -webkit-appearance: none;
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  outline: none;
}
.prop-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent-primary);
  cursor: pointer;
}

.range-value {
  font-size: 0.72rem;
  color: var(--text-muted);
  min-width: 36px;
  text-align: right;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 5px;
}

.preset-btn {
  aspect-ratio: 1;
  border: 2px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.12s;
}
.preset-btn:hover, .preset-btn.active {
  border-color: var(--accent-primary);
  transform: scale(1.1);
}

.quick-add-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.quick-add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: 8px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.75rem;
  transition: all 0.12s;
}
.quick-add-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  background: rgba(108, 99, 255, 0.08);
}

.search-row {
  display: flex;
  gap: 6px;
}
.search-row .prop-input { flex: 1; }

.search-btn {
  padding: 6px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.12s;
}
.search-btn:hover {
  border-color: var(--accent-primary);
}

.replace-btn {
  width: 100%;
  padding: 9px;
  margin: 8px 0;
  background: var(--bg-card);
  border: 1px dashed var(--border-color);
  color: var(--text-secondary);
  border-radius: 8px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.12s;
}
.replace-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}
.replace-btn.danger {
  border-style: solid;
  color: #ff6b81;
}
.replace-btn.danger:hover {
  border-color: #ff6b81;
  color: #ff6b81;
}

.bg-image-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bg-thumb {
  width: 100%;
  height: 90px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.75rem;
}
.bg-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.bg-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.layer-btns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.layer-btn {
  padding: 7px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.72rem;
  transition: all 0.12s;
}
.layer-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.transition-preview-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
  margin-top: 8px;
}

.transition-preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 2px;
  background: var(--bg-card);
  border: 1.5px solid var(--border-color);
  color: var(--text-muted);
  border-radius: 6px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;
}
.transition-preset-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  background: rgba(108, 99, 255, 0.06);
}
.transition-preset-btn.active {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  background: rgba(108, 99, 255, 0.12);
  box-shadow: 0 0 0 1px var(--accent-primary);
}

.preset-icon {
  font-size: 1rem;
  line-height: 1;
}

.preset-label {
  font-size: 0.55rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
</style>
