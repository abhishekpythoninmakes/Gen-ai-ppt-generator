<template>
  <div class="slide-panel-container">
    <div class="panel-header">
      <h3>Slides</h3>
      <button class="add-slide-btn" @click="store.addSlide()" title="Add new slide">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
      </button>
    </div>
    <div class="slide-list" ref="slideListRef">
      <div
        v-for="(slide, index) in store.slides"
        :key="slide.id"
        class="slide-thumbnail"
        :class="{
          active: index === store.activeSlideIndex,
          dragging: dragIndex === index,
          'stream-new': store.isGenerating && index === store.slides.length - 1,
        }"
        @click="store.setActiveSlide(index)"
        :draggable="!store.isGenerating"
        @dragstart="!store.isGenerating && onDragStart(index, $event)"
        @dragover.prevent="!store.isGenerating && onDragOver(index, $event)"
        @drop="!store.isGenerating && onDrop(index)"
        @dragend="dragIndex = -1"
        @contextmenu.prevent="showMenu(index, $event)"
      >
        <span class="slide-number">{{ index + 1 }}</span>
        <div class="thumb-inner" :style="getThumbBackground(slide)">
          <div class="thumb-elements">
            <div
              v-for="el in slide.elements.slice(0, 4)"
              :key="el.id"
              class="thumb-element"
              :class="'thumb-' + el.type"
              :style="getThumbStyle(el)"
            >
              <span v-if="el.type === 'text'" class="thumb-text">{{ truncate(el.text, 30) }}</span>
              <img v-else-if="el.type === 'image' && el.src" :src="el.src" class="thumb-img" />
              <div v-else-if="el.type === 'shape'" class="thumb-shape"></div>
            </div>
          </div>
        </div>

        <div class="thumb-actions" v-if="store.slides.length > 1 && !store.isGenerating">
          <button class="thumb-action-btn" @click.stop="store.duplicateSlide(index)" title="Duplicate">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
            </svg>
          </button>
          <button class="thumb-action-btn delete" @click.stop="store.deleteSlide(index)" title="Delete">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useEditorStore } from '../../stores/editor'

const store = useEditorStore()
const dragIndex = ref(-1)
const slideListRef = ref(null)

// Auto-scroll to the latest slide during generation
watch(
  () => store.streamedSlideCount,
  async (count) => {
    if (count > 0 && store.isGenerating && slideListRef.value) {
      await nextTick()
      const list = slideListRef.value
      const lastThumb = list.querySelector('.slide-thumbnail:last-child')
      if (lastThumb) {
        lastThumb.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    }
  }
)

function truncate(str, max) {
  if (!str) return ''
  return str.length > max ? str.slice(0, max) + '…' : str
}

function getThumbStyle(el) {
  const scale = 156 / 960 // thumbnail width / canvas width
  return {
    left: (el.x || 0) * scale + 'px',
    top: (el.y || 0) * scale + 'px',
    width: (el.width || 100) * scale + 'px',
    height: Math.min((el.height || 50) * scale, 20) + 'px',
  }
}

function getThumbBackground(slide) {
  const bg = slide.background || '#1a1a2e'
  const img = slide.backgroundImage || ''
  if (img) {
    return {
      backgroundImage: `url(${img})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundColor: bg,
    }
  }
  return { background: bg }
}

function onDragStart(index, e) {
  dragIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', index.toString())
}

function onDragOver(index, e) {
  e.dataTransfer.dropEffect = 'move'
}

function onDrop(targetIndex) {
  if (dragIndex.value === -1 || dragIndex.value === targetIndex) return
  store.reorderSlides(dragIndex.value, targetIndex)
  dragIndex.value = -1
}

function showMenu(index, e) {
  // Could add right-click context menu in future
}
</script>

<style scoped>
.slide-panel-container {
  width: 200px;
  min-width: 200px;
  border-right: 1px solid var(--border-color);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--border-color);
}

.panel-header h3 {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
}

.add-slide-btn {
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.add-slide-btn:hover {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.slide-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slide-thumbnail {
  position: relative;
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.15s ease;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px;
}

.slide-thumbnail.active {
  border-color: var(--accent-primary);
  box-shadow: 0 0 12px rgba(108, 99, 255, 0.25);
}

.slide-thumbnail:hover {
  border-color: var(--border-glow);
}

.slide-thumbnail.dragging {
  opacity: 0.5;
}

.slide-number {
  font-size: 0.65rem;
  color: var(--text-muted);
  width: 16px;
  text-align: center;
  flex-shrink: 0;
  padding-top: 4px;
}

.thumb-inner {
  flex: 1;
  height: 87px;
  border-radius: 5px;
  position: relative;
  overflow: hidden;
}

.thumb-elements {
  position: relative;
  width: 100%;
  height: 100%;
}

.thumb-element {
  position: absolute;
  overflow: hidden;
}

.thumb-text {
  font-size: 4px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.2;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 2px;
}

.thumb-shape {
  width: 100%;
  height: 100%;
  background: rgba(108, 99, 255, 0.3);
  border: 1px solid rgba(108, 99, 255, 0.5);
  border-radius: 3px;
}

.thumb-actions {
  position: absolute;
  top: 4px;
  right: 4px;
  display: none;
  gap: 2px;
  z-index: 2;
}

.slide-thumbnail:hover .thumb-actions {
  display: flex;
}

.thumb-action-btn {
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.15s;
}

.thumb-action-btn:hover {
  background: var(--accent-primary);
  color: white;
}

.thumb-action-btn.delete:hover {
  background: #ff4757;
}

/* Streaming: pulse animation on newest slide */
.slide-thumbnail.stream-new {
  border-color: var(--accent-primary);
  animation: stream-pulse 1.5s ease-in-out infinite;
}

.slide-thumbnail.stream-new .thumb-inner {
  animation: stream-fade-in 0.5s ease-out;
}

@keyframes stream-pulse {
  0%, 100% {
    box-shadow: 0 0 8px rgba(108, 99, 255, 0.2);
  }
  50% {
    box-shadow: 0 0 20px rgba(108, 99, 255, 0.5), 0 0 40px rgba(108, 99, 255, 0.15);
  }
}

@keyframes stream-fade-in {
  0% {
    opacity: 0;
    transform: scale(0.92);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
