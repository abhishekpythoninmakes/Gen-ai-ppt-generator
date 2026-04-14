<template>
  <div class="editor-toolbar glass">
    <div class="toolbar-section toolbar-left">
      <router-link :to="backTo" class="toolbar-icon-btn" title="Back">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12,19 5,12 12,5"/>
        </svg>
      </router-link>
      <input
        v-model="titleModel"
        class="title-input"
        @blur="onTitleBlur"
        @keydown.enter="$event.target.blur()"
        placeholder="Presentation Title"
      />
    </div>

    <div class="toolbar-section toolbar-center">
      <!-- Insert tools -->
      <div class="tool-group">
        <button class="tool-btn" @click="addText" title="Add Text">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 7V4h16v3"/><line x1="12" y1="4" x2="12" y2="20"/><line x1="8" y1="20" x2="16" y2="20"/>
          </svg>
          <span class="tool-label">Text</span>
        </button>
        <button class="tool-btn" @click="$emit('add-image')" title="Add Image">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21,15 16,10 5,21"/>
          </svg>
          <span class="tool-label">Image</span>
        </button>
        <button class="tool-btn" @click="$emit('add-icon')" title="Add Icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2l3 6 6 .9-4.5 4.4 1.1 6.2L12 17l-5.6 2.5 1.1-6.2L3 8.9 9 8z"/>
          </svg>
          <span class="tool-label">Icon</span>
        </button>
        <!-- Shape dropdown removed per request -->
      </div>

      <div class="tool-divider"></div>

      <!-- Text formatting (shown when text element is selected) -->
      <template v-if="isTextSelected">
        <div class="tool-group">
          <select v-model="textFontFamily" class="toolbar-select font-select" @change="updateTextProp('fontFamily', textFontFamily)">
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
          <select v-model.number="textFontSize" class="toolbar-select size-select" @change="updateTextProp('fontSize', textFontSize)">
            <option v-for="s in fontSizes" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>

        <div class="tool-divider"></div>

        <div class="tool-group">
          <button class="tool-btn icon-only" :class="{ active: textBold }" @click="toggleBold" title="Bold">
            <strong>B</strong>
          </button>
          <button class="tool-btn icon-only" :class="{ active: textItalic }" @click="toggleItalic" title="Italic">
            <em>I</em>
          </button>
          <button class="tool-btn icon-only" :class="{ active: textUnderline }" @click="toggleUnderline" title="Underline">
            <u>U</u>
          </button>
        </div>

        <div class="tool-divider"></div>

        <div class="tool-group">
          <button class="tool-btn icon-only" :class="{ active: textAlign === 'left' }" @click="updateTextProp('textAlign', 'left')" title="Align Left">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/>
              <line x1="21" y1="14" x2="3" y2="14"/><line x1="17" y1="18" x2="3" y2="18"/>
            </svg>
          </button>
          <button class="tool-btn icon-only" :class="{ active: textAlign === 'center' }" @click="updateTextProp('textAlign', 'center')" title="Align Center">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="10" x2="6" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/>
              <line x1="21" y1="14" x2="3" y2="14"/><line x1="18" y1="18" x2="6" y2="18"/>
            </svg>
          </button>
          <button class="tool-btn icon-only" :class="{ active: textAlign === 'right' }" @click="updateTextProp('textAlign', 'right')" title="Align Right">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="21" y1="10" x2="7" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/>
              <line x1="21" y1="14" x2="3" y2="14"/><line x1="21" y1="18" x2="7" y2="18"/>
            </svg>
          </button>
        </div>

        <div class="tool-divider"></div>

        <div class="tool-group">
          <label class="color-tool" title="Text Color">
            <span class="color-preview" :style="{ background: textColor }"></span>
            <input type="color" v-model="textColor" @input="updateTextProp('fill', textColor)" />
          </label>
        </div>
      </template>

      <!-- Element actions (shown when any element is selected) -->
      <template v-if="store.activeElement">
        <div class="tool-divider"></div>
        <div class="tool-group">
          <button class="tool-btn icon-only" @click="store.bringForward(store.activeElementId)" title="Bring Forward">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="18,15 12,9 6,15"/>
            </svg>
          </button>
          <button class="tool-btn icon-only" @click="store.sendBackward(store.activeElementId)" title="Send Backward">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6,9 12,15 18,9"/>
            </svg>
          </button>
          <button class="tool-btn icon-only delete-btn" @click="$emit('delete-element')" title="Delete Element">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2 2 0 01-2,2H7a2 2 0 01-2-2V6m3,0V4a2 2 0 012-2h4a2 2 0 012,2v2"/>
            </svg>
          </button>
        </div>
      </template>
    </div>

    <div class="toolbar-section toolbar-right">
      <span class="slide-counter">{{ store.activeSlideIndex + 1 }} / {{ store.totalSlides }}</span>
      <button v-if="showTemplates" class="tool-btn" @click="$emit('templates')" title="Templates">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="4" width="7" height="7"/><rect x="14" y="4" width="7" height="7"/><rect x="3" y="15" width="7" height="7"/><rect x="14" y="15" width="7" height="7"/>
        </svg>
        Templates
      </button>
      <button class="tool-btn icon-only" @click="$emit('undo')" :disabled="!store.canUndo" title="Undo">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9,14 4,9 9,4"/><path d="M20 20a8 8 0 0 0-8-8H4"/>
        </svg>
      </button>
      <button class="tool-btn icon-only" @click="$emit('redo')" :disabled="!store.canRedo" title="Redo">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15,4 20,9 15,14"/><path d="M4 20a8 8 0 0 1 8-8h8"/>
        </svg>
      </button>
      <button class="tool-btn" @click="$emit('save')" title="Save">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
          <polyline points="17,21 17,13 7,13 7,21"/><polyline points="7,3 7,8 15,8"/>
        </svg>
      </button>
      <button v-if="showExport" class="tool-btn" @click="$emit('export')" title="Export PPTX">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </button>
      <button v-if="showPresent" class="tool-btn present-btn" @click="$emit('present')" title="Present">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5,3 19,12 5,21"/>
        </svg>
        Present
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useEditorStore } from '../../stores/editor'
import { createTextElement } from '../../stores/editor'

defineProps({
  showExport: { type: Boolean, default: true },
  showPresent: { type: Boolean, default: true },
  showTemplates: { type: Boolean, default: true },
  backTo: { type: String, default: '/' },
})

const emit = defineEmits(['save', 'export', 'present', 'add-image', 'add-icon', 'delete-element', 'undo', 'redo', 'templates'])
const store = useEditorStore()

const fontSizes = [10, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 44, 48, 56, 64, 72, 96]

// Text formatting state
const textFontFamily = ref('Inter')
const textFontSize = ref(24)
const textBold = ref(false)
const textItalic = ref(false)
const textUnderline = ref(false)
const textAlign = ref('left')
const textColor = ref('#ffffff')

const isTextSelected = computed(() => {
  const el = store.activeElement
  if (!el) return false
  if (el.type === 'text') return true
  return typeof el.text === 'string'
})
const titleModel = computed({
  get: () => store.title,
  set: (val) => store.setTitle(val, { history: false }),
})

// Sync text props when selection changes
watch(() => store.activeElement, (el) => {
  if (el && el.type === 'text') {
    textFontFamily.value = el.fontFamily || 'Inter'
    textFontSize.value = el.fontSize || 24
    textBold.value = el.fontWeight === 'bold'
    textItalic.value = el.fontStyle === 'italic'
    textUnderline.value = el.underline || false
    textAlign.value = el.textAlign || 'left'
    textColor.value = el.fill || '#ffffff'
  }
}, { immediate: true })

function updateTextProp(prop, value) {
  if (!store.activeElementId) return
  store.updateElement(store.activeElementId, { [prop]: value })
}

function toggleBold() {
  textBold.value = !textBold.value
  updateTextProp('fontWeight', textBold.value ? 'bold' : 'normal')
}

function toggleItalic() {
  textItalic.value = !textItalic.value
  updateTextProp('fontStyle', textItalic.value ? 'italic' : 'normal')
}

function toggleUnderline() {
  textUnderline.value = !textUnderline.value
  updateTextProp('underline', textUnderline.value)
}

function addText() {
  const el = createTextElement({
    x: 100 + Math.random() * 100,
    y: 150 + Math.random() * 100,
  })
  store.addElement(el)
}

function onTitleBlur() {
  store.commitHistory()
  emit('save')
}
</script>

<style scoped>
.editor-toolbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 8px;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-left {
  flex: 0 0 auto;
  min-width: 220px;
}

.toolbar-center {
  flex: 1;
  justify-content: center;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
}
.toolbar-center::-webkit-scrollbar { display: none; }

.toolbar-right {
  flex: 0 0 auto;
  gap: 6px;
}

.toolbar-icon-btn {
  color: var(--text-secondary);
  padding: 6px;
  border-radius: 6px;
  display: flex;
  transition: all 0.15s;
}
.toolbar-icon-btn:hover {
  color: var(--text-primary);
  background: rgba(108, 99, 255, 0.1);
}

.title-input {
  background: none;
  border: 1px solid transparent;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 600;
  font-family: var(--font-sans);
  padding: 5px 10px;
  border-radius: 6px;
  width: 200px;
  outline: none;
  transition: all 0.15s;
}
.title-input:hover { border-color: var(--border-color); }
.title-input:focus { border-color: var(--accent-primary); background: var(--bg-input); }

.tool-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.tool-btn {
  padding: 6px 10px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.78rem;
  transition: all 0.12s;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  position: relative;
}
.tool-btn:hover {
  background: rgba(108, 99, 255, 0.1);
  color: var(--text-primary);
}
.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tool-btn.active {
  background: rgba(108, 99, 255, 0.15);
  color: var(--accent-primary);
}
.tool-btn.icon-only {
  padding: 6px 8px;
  font-size: 0.82rem;
}
.tool-btn.icon-only strong, .tool-btn.icon-only em, .tool-btn.icon-only u {
  font-size: 0.85rem;
}

.delete-btn:hover {
  background: rgba(255, 71, 87, 0.15);
  color: #ff6b81;
}

.tool-label {
  font-size: 0.75rem;
}

.caret { margin-left: -2px; }

.tool-divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
  margin: 0 6px;
  flex-shrink: 0;
}

.toolbar-select {
  padding: 4px 8px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  font-size: 0.78rem;
  font-family: var(--font-sans);
  outline: none;
  cursor: pointer;
}
.font-select { width: 130px; }
.size-select { width: 60px; }

.color-tool {
  position: relative;
  cursor: pointer;
  display: flex;
  align-items: center;
}
.color-tool input[type="color"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.color-preview {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  border: 2px solid var(--border-color);
  transition: border-color 0.15s;
}
.color-tool:hover .color-preview {
  border-color: var(--accent-primary);
}

.slide-counter {
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 0 8px;
}

.present-btn {
  background: var(--accent-gradient) !important;
  border: none !important;
  color: white !important;
  font-weight: 600;
  padding: 6px 14px !important;
}
.present-btn:hover {
  box-shadow: 0 4px 15px rgba(108, 99, 255, 0.3);
}

</style>
