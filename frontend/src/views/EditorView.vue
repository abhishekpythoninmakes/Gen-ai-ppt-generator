<template>
  <div class="editor-page" v-if="!loading">
    <!-- ══ Live Generation Overlay ══ -->
    <Transition name="gen-overlay">
      <div v-if="editorStore.isGenerating" class="generation-overlay">
        <div class="gen-overlay-content">
          <div class="gen-overlay-left">
            <div class="gen-sparkle">
              <span class="sparkle-icon">✦</span>
              <div class="sparkle-ring"></div>
              <div class="sparkle-ring sparkle-ring-2"></div>
            </div>
            <div class="gen-info">
              <h3 class="gen-title">Building your presentation</h3>
              <p class="gen-subtitle">{{ editorStore.generationMessage }}</p>
            </div>
          </div>
          <div class="gen-overlay-right">
            <div class="gen-slide-counter">
              <span class="slide-count-current">{{ editorStore.streamedSlideCount }}</span>
              <span class="slide-count-divider">/</span>
              <span class="slide-count-total">{{ editorStore.totalExpectedSlides || '?' }}</span>
              <span class="slide-count-label">slides</span>
            </div>
            <div class="gen-progress-bar">
              <div class="gen-progress-fill" :style="{ width: `${editorStore.generationProgress}%` }"></div>
              <div class="gen-progress-shimmer"></div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Toolbar -->
    <EditorToolbar
      :back-to="isTemplateMode ? '/admin/templates' : '/'"
      :show-export="!isTemplateMode && !editorStore.isGenerating"
      :show-present="!isTemplateMode && !editorStore.isGenerating"
      :show-templates="!isTemplateMode && !editorStore.isGenerating"
      @save="saveCurrent"
      @export="exportPptx"
      @present="startPresentation"
      @add-image="openImageDialog"
      @add-icon="openIconDialog"
      @delete-element="deleteActiveElement"
      @templates="openTemplateModal"
      @undo="undo"
      @redo="redo"
    />

    <div class="editor-body">
      <!-- Slide Panel -->
      <SlidePanel />

      <!-- Main Canvas -->
      <SlideCanvas
        ref="canvasRef"
        @element-selected="onElementSelected"
        @element-deselected="onElementDeselected"
        @element-modified="onElementModified"
        @double-click-text="onDoubleClickText"
      />

      <!-- Properties Panel -->
    <PropertiesPanel
      @add-image="openImageDialog"
      @add-icon="openIconDialog"
      @replace-image="openImageReplace"
      @search-image="searchImage"
      @delete-element="deleteActiveElement"
      @background-image="openBackgroundImageDialog"
      @clear-background-image="clearBackgroundImage"
      @icon-color="updateActiveIconColor"
    />
    </div>

    <!-- Presentation Mode -->
    <PresentationMode
      :visible="presenting"
      :slides="editorStore.slides"
      :startIndex="editorStore.activeSlideIndex"
      @close="presenting = false"
    />

    <!-- Hidden file input for image upload -->
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      style="display: none"
      @change="onFileSelected"
    />

    <!-- Image Search Modal -->
    <Teleport to="body">
      <div v-if="showImageModal" class="modal-overlay" @click.self="showImageModal = false">
        <div class="image-modal glass">
          <h3 class="modal-title">Add Image</h3>

          <div class="modal-tabs">
            <button :class="{ active: imageTab === 'search' }" @click="imageTab = 'search'">Search</button>
            <button :class="{ active: imageTab === 'assets' }" @click="imageTab = 'assets'">Assets</button>
            <button :class="{ active: imageTab === 'url' }" @click="imageTab = 'url'">URL</button>
            <button :class="{ active: imageTab === 'upload' }" @click="imageTab = 'upload'">Upload</button>
          </div>

          <div v-if="imageTab === 'search'" class="modal-body">
            <div class="modal-search-row">
              <input
                v-model="imageSearchQuery"
                class="prop-input"
                placeholder="Search for images..."
                @keydown.enter="doImageSearch"
              />
              <button class="modal-search-btn" @click="doImageSearch" :disabled="searchingImage">
                {{ searchingImage ? '...' : '🔍' }}
              </button>
            </div>
            <div v-if="searchResults.length" class="search-results-grid">
              <div v-for="(url, i) in searchResults" :key="i" class="search-result-item" @click="insertImageUrl(url)">
                <img :src="url" alt="Search result" />
              </div>
            </div>
            <div v-if="searchResults.length" class="search-more-row">
              <button class="modal-action-btn" @click="loadMoreImages" :disabled="searchingImage || !hasMoreResults">
                {{ hasMoreResults ? (searchingImage ? 'Loading...' : 'More') : 'No more results' }}
              </button>
            </div>
            <p v-else-if="searchingImage" class="modal-hint">Searching images...</p>
            <p v-else-if="searchedOnce" class="modal-hint">No results found. Try a different query.</p>
          </div>

          <div v-if="imageTab === 'assets'" class="modal-body">
            <div class="modal-search-row">
              <input
                v-model="assetSearchQuery"
                class="prop-input"
                placeholder="Search by asset label..."
                @keydown.enter="searchAssets"
              />
              <button class="modal-search-btn" @click="searchAssets" :disabled="loadingAssets">
                {{ loadingAssets ? '...' : '🔍' }}
              </button>
            </div>
            <div v-if="assetResults.length" class="search-results-grid">
              <div
                v-for="asset in assetResults"
                :key="asset.id"
                class="search-result-item"
                @click="insertImageUrl(asset.url)"
              >
                <img :src="asset.url" :alt="asset.label || 'asset'" />
                <div class="asset-chip">{{ asset.label || 'asset' }}</div>
              </div>
            </div>
            <p v-else class="modal-hint">{{ loadingAssets ? 'Loading assets...' : 'No assets found.' }}</p>
          </div>

          <div v-if="imageTab === 'url'" class="modal-body">
            <input v-model="imageUrlInput" class="prop-input" placeholder="Paste image URL..." />
            <button class="modal-action-btn" @click="insertImageUrl(imageUrlInput)" :disabled="!imageUrlInput.trim()">
              Insert Image
            </button>
          </div>

          <div v-if="imageTab === 'upload'" class="modal-body">
            <div class="upload-dropzone" @click="$refs.fileInput?.click()">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color: var(--text-muted);">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <p>Click to upload an image</p>
            </div>
          </div>

          <button class="modal-close" @click="showImageModal = false">✕</button>
        </div>
      </div>
    </Teleport>

    <!-- Templates Modal -->
    <Teleport to="body">
      <div v-if="showTemplateModal" class="modal-overlay" @click.self="showTemplateModal = false">
        <div class="image-modal glass">
          <h3 class="modal-title">Templates</h3>
          <div class="modal-search-row">
            <input
              v-model="templateSearch"
              class="prop-input"
              placeholder="Search templates..."
            />
          </div>
          <div v-if="loadingTemplates" class="modal-hint">Loading templates...</div>
          <div v-else-if="filteredTemplates.length" class="search-results-grid">
            <div
              v-for="t in filteredTemplates"
              :key="t.id"
              class="search-result-item"
              @click="applyTemplate(t.id)"
            >
              <img v-if="t.thumbnail_url" :src="t.thumbnail_url" alt="Template preview" />
              <div v-else class="template-fallback">{{ t.title }}</div>
            </div>
          </div>
          <p v-else class="modal-hint">No templates found.</p>

          <button class="modal-close" @click="showTemplateModal = false">✕</button>
        </div>
      </div>
    </Teleport>

    <!-- Icon Search Modal -->
    <Teleport to="body">
      <div v-if="showIconModal" class="modal-overlay" @click.self="showIconModal = false">
        <div class="image-modal glass">
          <h3 class="modal-title">Add Icon</h3>
          <div class="modal-search-row">
            <input
              v-model="iconQuery"
              class="prop-input"
              placeholder="Search icons..."
              @keydown.enter="searchIcons"
            />
            <button class="modal-search-btn" @click="searchIcons" :disabled="searchingIcon">
              {{ searchingIcon ? '...' : '🔍' }}
            </button>
          </div>

          <div v-if="iconResults.length" class="search-results-grid">
            <div
              v-for="icon in iconResults"
              :key="icon"
              class="search-result-item"
              @click="insertIcon(icon)"
            >
              <img :src="`https://api.iconify.design/${icon}.svg?width=96`" :alt="icon" />
            </div>
          </div>
          <p v-else class="modal-hint">Search for icons using Iconify.</p>

          <button class="modal-close" @click="showIconModal = false">✕</button>
        </div>
      </div>
    </Teleport>

    <!-- Feedback Modal -->
    <Teleport to="body">
      <div v-if="showFeedbackModal" class="modal-overlay feedback-overlay" @click.self="dismissFeedback">
        <div class="feedback-modal glass">
          <div class="feedback-header">
            <div class="feedback-icon">✦</div>
            <h3>How was this presentation?</h3>
            <p class="feedback-subtitle">Your feedback helps us create better designs</p>
          </div>

          <div class="feedback-stars">
            <button
              v-for="star in 5" :key="star"
              class="star-btn" :class="{ active: feedbackRating >= star }"
              @click="feedbackRating = star"
            >★</button>
          </div>

          <div class="feedback-fields">
            <label>What should we improve?</label>
            <textarea
              v-model="feedbackImprovement"
              class="feedback-input"
              rows="2"
              placeholder="e.g., Use brighter colors, add more charts, better spacing..."
            ></textarea>

            <label>What did you like?</label>
            <textarea
              v-model="feedbackGood"
              class="feedback-input"
              rows="2"
              placeholder="e.g., Great layout, good image choices..."
            ></textarea>
          </div>

          <div class="feedback-actions">
            <button class="btn-secondary" @click="dismissFeedback">Skip</button>
            <button class="btn-primary" @click="submitFeedback" :disabled="submittingFeedback">
              {{ submittingFeedback ? 'Sending...' : 'Submit Feedback' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>

  <div v-else class="editor-loading">
    <LoadingSpinner text="Loading presentation..." />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, toRaw, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePptStore } from '../stores/ppt'
import {
  useEditorStore,
  legacySlidesToElements,
  slidesToLegacyFormat,
  createImageElement,
  createDefaultSlide,
  createTextElement,
} from '../stores/editor'
import api from '../api'
import { exportToPptx } from '../utils/exportPptx'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import EditorToolbar from '../components/editor/EditorToolbar.vue'
import SlidePanel from '../components/editor/SlidePanel.vue'
import SlideCanvas from '../components/editor/SlideCanvas.vue'
import PropertiesPanel from '../components/editor/PropertiesPanel.vue'
import PresentationMode from '../components/editor/PresentationMode.vue'

const route = useRoute()
const router = useRouter()
const pptStore = usePptStore()
const editorStore = useEditorStore()

const canvasRef = ref(null)
const fileInput = ref(null)
const loading = ref(true)
const saving = ref(false)
const presenting = ref(false)
const autoSaveDelayMs = 800
let autoSaveTimer
let pendingAutoSave = false
let savingPromise = null

const isTemplateMode = computed(() => route.meta?.templateEditor === true)
const isGeneratingMode = computed(() => route.meta?.generatingMode === true)

// Image modal state
const showImageModal = ref(false)
const imageTab = ref('search')
const imageSearchQuery = ref('')
const imageUrlInput = ref('')
const searchingImage = ref(false)
const searchResults = ref([])
const searchedOnce = ref(false)
const isReplacingImage = ref(false)
const isSettingBackground = ref(false)
const assetSearchQuery = ref('')
const loadingAssets = ref(false)
const assetResults = ref([])

// Templates modal state
const showTemplateModal = ref(false)
const templates = ref([])
const templateSearch = ref('')
const loadingTemplates = ref(false)

// Icon modal state
const showIconModal = ref(false)
const iconQuery = ref('')
const iconResults = ref([])
const searchingIcon = ref(false)

// SSE stream cleanup
let streamCleanup = null

const filteredTemplates = computed(() => {
  const q = templateSearch.value.trim().toLowerCase()
  if (!q) return templates.value
  return templates.value.filter(t => (t.title || '').toLowerCase().includes(q))
})
const imageSearchPage = ref(1)
const imageSearchPerPage = 4
const hasMoreResults = ref(false)
const minLiveImageQueryLength = 2
const imageSearchDebounceMs = 350
let imageSearchDebounceTimer = null
let imageSearchAbortController = null
let imageSearchRequestSeq = 0

watch(imageTab, (tab) => {
  if (tab !== 'search') {
    clearImageSearchDebounce()
    cancelInFlightImageSearch()
  }
  if (tab === 'assets' && assetResults.value.length === 0) {
    fetchAssetsForEditor()
  }
})

watch(imageSearchQuery, (nextQuery) => {
  if (!showImageModal.value || imageTab.value !== 'search') return
  scheduleLiveImageSearch(nextQuery)
})

watch(showImageModal, (visible) => {
  if (!visible) {
    clearImageSearchDebounce()
    cancelInFlightImageSearch()
  }
})

// ─── Load presentation OR start streaming ─────────
onMounted(async () => {
  if (isGeneratingMode.value) {
    // Streaming generation mode — connect to SSE
    await initStreamingGeneration()
  } else {
    // Normal editor load
    const id = route.params.id
    try {
      if (isTemplateMode.value) {
        const { data } = await api.get(`/admin/templates/${id}`)
        const content = JSON.parse(data.content_json)
        const legacySlides = content.slides || []
        const { slides: elementSlides, theme } = legacySlidesToElements(
          legacySlides,
          content.theme,
          content.title || data.title
        )
        editorStore.setSlides(elementSlides, content.title || data.title, theme)
        await normalizeIconsInSlides()
      } else {
        const data = await pptStore.fetchPresentation(id)
        const content = JSON.parse(data.content_json)
        editorStore.presentationId = parseInt(id)

        const legacySlides = content.slides || []
        const { slides: elementSlides, theme } = legacySlidesToElements(
          legacySlides,
          content.theme,
          content.title || data.title
        )

        editorStore.setSlides(elementSlides, content.title || data.title, theme)
        await normalizeIconsInSlides()
      }
    } catch (e) {
      console.error('Failed to load presentation:', e)
      window.$toast?.('Failed to load presentation', 'error')
      router.push({ name: 'Home' })
    } finally {
      loading.value = false
    }
  }
})

// ─── Feedback modal state ───────────────────────
const showFeedbackModal = ref(false)
const feedbackRating = ref(0)
const feedbackImprovement = ref('')
const feedbackGood = ref('')
const submittingFeedback = ref(false)
const feedbackScopeKey = computed(() => {
  const mode = isTemplateMode.value ? 'template' : 'ppt'
  const id = route.params.id ?? route.params.jobId ?? 'unknown'
  return `${mode}:${id}`
})
let feedbackCheckedScope = null

// ─── SSE Streaming Generation ───────────────────
async function initStreamingGeneration() {
  const jobId = route.params.jobId
  if (!jobId) {
    window.$toast?.('Invalid generation job', 'error')
    router.push({ name: isTemplateMode.value ? 'AdminTemplates' : 'Create' })
    return
  }

  // Initialize editor in streaming mode
  editorStore.initStreamingMode('Generating...', null, 0)
  loading.value = false

  // Choose the right stream connector based on mode
  const connectFn = isTemplateMode.value
    ? pptStore.connectToTemplateStream
    : pptStore.connectToStream

  streamCleanup = connectFn(parseInt(jobId), {
    onStage(data) {
      editorStore.updateGenerationProgress(
        data.progress,
        data.stage,
        data.message
      )
    },

    onTheme(data) {
      if (!editorStore.slides.length) {
        editorStore.initStreamingMode(
          data.title || 'Generating...',
          data.theme,
          data.total_slides || 0
        )
      } else {
        editorStore.updateStreamingMeta(
          data.title || editorStore.title,
          data.theme,
          data.total_slides || editorStore.totalExpectedSlides || 0
        )
      }
      loading.value = false
    },

    onSlide(data) {
      editorStore.appendStreamedSlide(
        data.slide,
        Number.isInteger(data.index) ? data.index : null,
        {
          placeholder: data.placeholder === true,
          activate: data.placeholder !== true,
        }
      )
      editorStore.updateGenerationProgress(
        Math.round(35 + (((Number(data.index) || 0) + 1) / Math.max(Number(data.total) || 1, 1)) * 57),
        'slide_building',
        data.placeholder
          ? `Drafting slide ${Number(data.index) + 1} of ${data.total}...`
          : `Building slide ${Number(data.index) + 1} of ${data.total}...`
      )
    },

    onComplete(data) {
      if (isTemplateMode.value) {
        // Template generation complete
        editorStore.finalizeGeneration(data.template_id)
        window.$toast?.('Template generated!', 'success')
        if (data.template_id) {
          router.replace({ name: 'TemplateEditor', params: { id: data.template_id } })
        }
      } else {
        // PPT generation complete
        editorStore.finalizeGeneration(data.ppt_id)
        window.$toast?.('Presentation generated!', 'success')
        if (data.ppt_id) {
          router.replace({ name: 'Editor', params: { id: data.ppt_id } })
        }
      }
    },

    onError(data) {
      editorStore.handleGenerationError(data.message)
      window.$toast?.(data.message || 'Generation failed', 'error')
      setTimeout(() => {
        router.push({ name: isTemplateMode.value ? 'AdminTemplates' : 'Create' })
      }, 2000)
    },
  })
}

// ─── Feedback system ────────────────────────────
async function checkShouldAskFeedback() {
  const scope = feedbackScopeKey.value
  if (feedbackCheckedScope === scope) return false
  try {
    const { data } = await api.get('/feedback/should-ask')
    feedbackCheckedScope = scope
    return data.should_ask === true
  } catch {
    // Keep scope unchecked on transient/API failures so we can retry later.
    return false
  }
}

async function submitFeedback() {
  if (submittingFeedback.value) return
  submittingFeedback.value = true
  try {
    await api.post('/feedback', {
      job_type: isTemplateMode.value ? 'template' : 'ppt',
      prompt_text: '',
      rating: feedbackRating.value || null,
      feedback_text: '',
      improvement_suggestions: feedbackImprovement.value.trim() || null,
      what_was_good: feedbackGood.value.trim() || null,
    })
    window.$toast?.('Thanks for your feedback!', 'success', 2000)
  } catch {
    // silently fail
  }
  showFeedbackModal.value = false
  submittingFeedback.value = false
  if (pendingNavigation) {
    pendingNavigation()
    pendingNavigation = null
  }
}

function dismissFeedback() {
  showFeedbackModal.value = false
  if (pendingNavigation) {
    pendingNavigation()
    pendingNavigation = null
  }
}

let pendingNavigation = null

watch(feedbackScopeKey, () => {
  // When switching editor mode/route (ppt <-> template or id change),
  // allow a fresh feedback eligibility check.
  feedbackCheckedScope = null
})

// ─── Auto-save ──────────────────────────────────────
let autoSaveInterval
onMounted(() => {
  autoSaveInterval = setInterval(() => {
    if (!loading.value && editorStore.isDirty && editorStore.slides.length > 0) {
      saveCurrent(true)
    }
  }, 30000)
})

onUnmounted(() => {
  clearInterval(autoSaveInterval)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  clearImageSearchDebounce()
  cancelInFlightImageSearch()
  // Clean up SSE stream if still connected
  if (streamCleanup) {
    streamCleanup()
    streamCleanup = null
  }
})

// ─── Navigation guard for feedback popup ────────
import { onBeforeRouteLeave } from 'vue-router'

onBeforeRouteLeave(async (to, from, next) => {
  // Don't show feedback during generation or if already showing
  if (editorStore.isGenerating || showFeedbackModal.value || isGeneratingMode.value) {
    next()
    return
  }

  // Check if we should ask for feedback (random ~25-30%)
  const shouldAsk = await checkShouldAskFeedback()
  if (shouldAsk) {
    showFeedbackModal.value = true
    feedbackRating.value = 0
    feedbackImprovement.value = ''
    feedbackGood.value = ''
    pendingNavigation = () => next()
    // Don't navigate yet — wait for feedback submission or dismissal
    return
  }

  next()
})

// ─── Keyboard shortcuts ─────────────────────────────
function onKeyDown(e) {
  // Delete key
  if ((e.key === 'Delete' || e.key === 'Backspace') && editorStore.activeElement) {
    // Don't delete if we're editing text in a text field
    const tag = document.activeElement?.tagName?.toLowerCase()
    if (tag === 'input' || tag === 'textarea' || document.activeElement?.contentEditable === 'true') return
    deleteActiveElement()
  }

  // Ctrl+S to save
  if (e.ctrlKey && e.key === 's') {
    e.preventDefault()
    saveCurrent()
  }

  // Undo / Redo
  const key = e.key?.toLowerCase?.() || e.key
  if (e.ctrlKey && key === 'z' && !e.shiftKey) {
    e.preventDefault()
    undo()
  }
  if ((e.ctrlKey && key === 'y') || (e.ctrlKey && e.shiftKey && key === 'z')) {
    e.preventDefault()
    redo()
  }

  // Ctrl+C / Ctrl+V
  if (e.ctrlKey && e.key === 'c' && editorStore.activeElementId) {
    editorStore.copyElement(editorStore.activeElementId)
  }
  if (e.ctrlKey && e.key === 'v' && editorStore.clipboard) {
    editorStore.pasteElement()
  }

  // Escape to deselect
  if (e.key === 'Escape') {
    if (presenting.value) {
      presenting.value = false
    } else {
      editorStore.clearSelection()
      canvasRef.value?.getCanvas()?.discardActiveObject()
      canvasRef.value?.getCanvas()?.renderAll()
    }
  }
}

onMounted(() => window.addEventListener('keydown', onKeyDown))
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))

// ─── Auto-save on every change (debounced) ─────────
watch(() => editorStore.changeTick, () => {
  if (loading.value) return
  if (!editorStore.isDirty || editorStore.slides.length === 0) return
  pendingAutoSave = true
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    if (saving.value) return
    if (!editorStore.isDirty || editorStore.slides.length === 0) {
      pendingAutoSave = false
      return
    }
    pendingAutoSave = false
    saveCurrent(true)
  }, autoSaveDelayMs)
})

// ─── Canvas event handlers ──────────────────────────
function onElementSelected(elementId) {
  // Properties panel will auto-update via store
}

function onElementDeselected() {
  // Properties panel will auto-update via store
}

function onElementModified(elementId, updates) {
  // Element already updated in store by canvas component
}

function onDoubleClickText(elementId, fabricObj) {
  // Fabric.js textbox already supports inline editing on double-click
  // The canvas handles this natively
}

// ─── Actions ────────────────────────────────────────
function deleteActiveElement() {
  if (editorStore.activeElementId) {
    canvasRef.value?.deleteSelected()
  }
}

function getThumbnailData() {
  try {
    const dataUrl = canvasRef.value?.exportToDataURL?.()
    return dataUrl || ''
  } catch (e) {
    return ''
  }
}

async function savePresentation(silent = false) {
  if (saving.value) {
    pendingAutoSave = true
    return savingPromise
  }
  saving.value = true
  savingPromise = (async () => {
    try {
      const rawSlides = toRaw(editorStore.slides).map(s => ({
        ...s,
        elements: s.elements.map(e => toRaw(e)),
      }))
      const content = slidesToLegacyFormat(rawSlides, editorStore.title, editorStore.theme)
      const payload = {
        title: editorStore.title,
        content_json: JSON.stringify(content),
      }
      const thumbnail = getThumbnailData()
      if (thumbnail) payload.thumbnail_url = thumbnail
      await pptStore.updatePresentation(route.params.id, payload)
      editorStore.isDirty = false
      if (!silent) window.$toast?.('Saved!', 'success', 2000)
    } catch (e) {
      console.error('Save failed:', e)
      if (!silent) window.$toast?.('Failed to save', 'error')
    } finally {
      saving.value = false
    }
  })()
  await savingPromise
  savingPromise = null
  if (pendingAutoSave && editorStore.isDirty) {
    pendingAutoSave = false
    await savePresentation(true)
  } else {
    pendingAutoSave = false
  }
}

async function saveTemplate(silent = false) {
  if (saving.value) {
    pendingAutoSave = true
    return savingPromise
  }
  saving.value = true
  savingPromise = (async () => {
    try {
      const rawSlides = toRaw(editorStore.slides).map(s => ({
        ...s,
        elements: s.elements.map(e => toRaw(e)),
      }))
      const content = slidesToLegacyFormat(rawSlides, editorStore.title, editorStore.theme)
      const payload = {
        title: editorStore.title,
        content_json: JSON.stringify(content),
      }
      const thumbnail = getThumbnailData()
      if (thumbnail) payload.thumbnail_url = thumbnail
      await api.put(`/admin/templates/${route.params.id}`, payload)
      editorStore.isDirty = false
      if (!silent) window.$toast?.('Template saved!', 'success', 2000)
    } catch (e) {
      console.error('Template save failed:', e)
      if (!silent) window.$toast?.('Failed to save template', 'error')
    } finally {
      saving.value = false
    }
  })()
  await savingPromise
  savingPromise = null
  if (pendingAutoSave && editorStore.isDirty) {
    pendingAutoSave = false
    await saveTemplate(true)
  } else {
    pendingAutoSave = false
  }
}

function saveCurrent(silent = false) {
  return isTemplateMode.value ? saveTemplate(silent) : savePresentation(silent)
}

async function exportPptx() {
  try {
    if (isTemplateMode.value) {
      window.$toast?.('Export is not available for templates', 'error')
      return
    }
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }
    pendingAutoSave = true
    await saveCurrent(true)
    window.$toast?.('Generating PPTX...', 'info', 2000)
    const rawSlides = toRaw(editorStore.slides).map(s => ({
      ...s,
      elements: s.elements.map(e => toRaw(e)),
    }))
    await exportToPptx(rawSlides, editorStore.title, toRaw(editorStore.theme))
    window.$toast?.('Downloaded!', 'success')
  } catch (err) {
    console.error('PptxGenJS export failed:', err)
    window.$toast?.('Export failed — trying server fallback...', 'info', 2000)
    // Fallback to backend export
    try {
      const response = await api.get(`/export/${route.params.id}/pptx`, { responseType: 'arraybuffer' })
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${editorStore.title || 'presentation'}.pptx`
      document.body.appendChild(link)
      link.click()
      setTimeout(() => {
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      }, 150)
      window.$toast?.('Downloaded!', 'success')
    } catch {
      window.$toast?.('Export failed', 'error')
    }
  }
}

function startPresentation() {
  presenting.value = true
}

function undo() {
  editorStore.undo()
}

function redo() {
  editorStore.redo()
}

// ─── Templates ─────────────────────────────────────
async function fetchTemplates() {
  loadingTemplates.value = true
  try {
    const { data } = await api.get('/templates')
    templates.value = data
  } catch {
    templates.value = []
  } finally {
    loadingTemplates.value = false
  }
}

function openTemplateModal() {
  templateSearch.value = ''
  showTemplateModal.value = true
  fetchTemplates()
}

const TEXT_STYLE_PROPS = [
  'fontFamily',
  'fontWeight',
  'fontStyle',
  'underline',
  'fill',
  'backgroundColor',
  'backgroundOpacity',
  'textAlign',
  'lineHeight',
  'opacity',
]

const IMAGE_STYLE_PROPS = [
  'borderRadius',
  'shadow',
  'opacity',
]

const SHAPE_STYLE_PROPS = [
  'fill',
  'stroke',
  'strokeWidth',
  'opacity',
]

function copyStyleProps(target, source, props) {
  if (!target || !source) return
  for (const key of props) {
    if (source[key] !== undefined) {
      target[key] = source[key]
    }
  }
}

function applyTemplateStyleToElements(currentElements = [], templateElements = []) {
  const textStyle = templateElements.find(el => el?.type === 'text')
  const imageStyle = templateElements.find(el => el?.type === 'image')
  const shapeStyle = templateElements.find(el => el?.type === 'shape')

  for (const el of currentElements) {
    if (!el) continue

    if (el.type === 'text' && textStyle) {
      copyStyleProps(el, textStyle, TEXT_STYLE_PROPS)
      continue
    }

    if (el.type === 'image' && imageStyle) {
      copyStyleProps(el, imageStyle, IMAGE_STYLE_PROPS)
      continue
    }

    if (el.type === 'shape' && shapeStyle) {
      copyStyleProps(el, shapeStyle, SHAPE_STYLE_PROPS)
    }
  }
}

function applyTemplateStyleToCurrentSlides(templateSlides = [], templateTheme = null) {
  const currentSlides = editorStore.slides || []
  if (!currentSlides.length) return false

  if (templateTheme) {
    editorStore.theme = templateTheme
  }

  if (!templateSlides.length) {
    editorStore.markChanged()
    editorStore.commitHistory()
    return true
  }

  for (let i = 0; i < currentSlides.length; i += 1) {
    const currentSlide = currentSlides[i]
    if (!currentSlide) continue

    const templateSlide = templateSlides[i % templateSlides.length]
    if (!templateSlide) continue

    currentSlide.background = templateSlide.background || currentSlide.background
    currentSlide.backgroundImage = templateSlide.backgroundImage || ''
    if (templateSlide.transition) {
      currentSlide.transition = { ...templateSlide.transition }
    }
    applyTemplateStyleToElements(currentSlide.elements || [], templateSlide.elements || [])
  }

  editorStore.clearSelection()
  editorStore.markChanged()
  editorStore.commitHistory()
  return true
}

async function applyTemplate(templateId) {
  try {
    const { data } = await api.get(`/templates/${templateId}`)
    const content = JSON.parse(data.content_json)
    const legacySlides = content.slides || []
    const { slides: elementSlides, theme } = legacySlidesToElements(
      legacySlides,
      content.theme,
      content.title || data.title
    )
    if (!editorStore.slides.length) {
      editorStore.setSlides(elementSlides, content.title || data.title, theme)
      await normalizeIconsInSlides()
      editorStore.isDirty = true
      editorStore.commitHistory()
      window.$toast?.('Template applied!', 'success', 2000)
    } else {
      applyTemplateStyleToCurrentSlides(elementSlides, theme)
      await normalizeIconsInSlides()
      window.$toast?.('Template style applied. Your content is preserved.', 'success', 2200)
    }

    showTemplateModal.value = false
    await saveCurrent(true)
  } catch {
    window.$toast?.('Failed to apply template', 'error')
  }
}

// ─── Icons (Iconify) ───────────────────────────────
function openIconDialog() {
  iconQuery.value = ''
  iconResults.value = []
  showIconModal.value = true
}

async function searchIcons() {
  if (!iconQuery.value.trim()) return
  searchingIcon.value = true
  try {
    const q = encodeURIComponent(iconQuery.value.trim())
    const res = await fetch(`https://api.iconify.design/search?query=${q}&limit=30`)
    const data = await res.json()
    iconResults.value = data.icons || []
  } catch {
    iconResults.value = []
    window.$toast?.('Icon search failed', 'error')
  } finally {
    searchingIcon.value = false
  }
}

async function iconToPngDataUrl(iconName, color = '#ffffff', size = 256) {
  const safeColor = encodeURIComponent(color)
  const svgUrl = `https://api.iconify.design/${iconName}.svg?color=${safeColor}&width=${size}`
  const res = await fetch(svgUrl)
  const svgText = await res.text()
  const svgBlob = new Blob([svgText], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(svgBlob)
  try {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    await new Promise((resolve, reject) => {
      img.onload = resolve
      img.onerror = reject
      img.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, size, size)
    ctx.drawImage(img, 0, 0, size, size)
    return canvas.toDataURL('image/png')
  } finally {
    URL.revokeObjectURL(url)
  }
}

function extractIconNameFromUrl(url) {
  if (!url) return ''
  const m = url.match(/api\.iconify\.design\/([^.?/]+(?:\/[^.?/]+)?)\.(?:png|svg)/)
  return m ? m[1] : ''
}

async function insertIcon(iconName) {
  if (!iconName) return
  let src = ''
  const color = '#ffffff'
  try {
    src = await iconToPngDataUrl(iconName, color, 256)
  } catch {
    src = `https://api.iconify.design/${iconName}.png?width=256`
  }
  editorStore.addElement(createImageElement({
    x: 220 + Math.random() * 80,
    y: 120 + Math.random() * 60,
    width: 120,
    height: 120,
    src,
    borderRadius: 0,
    isIcon: true,
    iconName,
    iconColor: color,
  }))
  showIconModal.value = false
  window.$toast?.('Icon added!', 'success', 2000)
}

async function normalizeIconsInSlides() {
  const slides = editorStore.slides || []
  for (let s = 0; s < slides.length; s += 1) {
    const slide = slides[s]
    if (!slide?.elements?.length) continue
    for (const el of slide.elements) {
      if (el.type !== 'image') continue
      const isIcon = el.isIcon || !!el.iconName || (el.src && el.src.includes('api.iconify.design'))
      if (!isIcon) continue
      const iconName = el.iconName || extractIconNameFromUrl(el.src) || ''
      const iconColor = el.iconColor || '#ffffff'
      if (!iconName) {
        if (!el.isIcon) {
          editorStore.updateElementInSlide(s, el.id, { isIcon: true, iconColor }, { history: false })
        }
        continue
      }
      if (!el.isIcon || el.iconName !== iconName) {
        editorStore.updateElementInSlide(s, el.id, { isIcon: true, iconName, iconColor }, { history: false })
      }
      if (!el.src || !el.src.startsWith('data:')) {
        try {
          const dataUrl = await iconToPngDataUrl(iconName, iconColor, 256)
          editorStore.updateElementInSlide(s, el.id, { src: dataUrl, isIcon: true, iconName, iconColor }, { history: false })
        } catch {
          // keep existing src if conversion fails
        }
      }
    }
  }
}

async function updateActiveIconColor(color) {
  const el = editorStore.activeElement
  if (!el || !editorStore.activeElementId) return
  const iconName = el.iconName || extractIconNameFromUrl(el.src) || ''
  if (!iconName) {
    editorStore.updateElement(editorStore.activeElementId, { iconColor: color, isIcon: true })
    return
  }
  try {
    const src = await iconToPngDataUrl(iconName, color, 256)
    editorStore.updateElement(editorStore.activeElementId, { src, iconColor: color, isIcon: true, iconName })
    window.$toast?.('Icon color updated', 'success', 1200)
  } catch {
    editorStore.updateElement(editorStore.activeElementId, { iconColor: color, isIcon: true, iconName })
    window.$toast?.('Failed to recolor icon', 'error')
  }
}

// ─── Image handling ─────────────────────────────────
function clearImageSearchDebounce() {
  if (imageSearchDebounceTimer) {
    clearTimeout(imageSearchDebounceTimer)
    imageSearchDebounceTimer = null
  }
}

function cancelInFlightImageSearch() {
  if (imageSearchAbortController) {
    imageSearchAbortController.abort()
    imageSearchAbortController = null
  }
}

function resetImageSearchState() {
  searchResults.value = []
  hasMoreResults.value = false
  imageSearchPage.value = 1
  searchingImage.value = false
}

function scheduleLiveImageSearch(rawQuery) {
  clearImageSearchDebounce()
  cancelInFlightImageSearch()

  const query = (rawQuery || '').trim()
  if (query.length < minLiveImageQueryLength) {
    if (!query.length) searchedOnce.value = false
    resetImageSearchState()
    return
  }

  imageSearchDebounceTimer = setTimeout(async () => {
    imageSearchPage.value = 1
    await doImageSearch({ silent: true, fromLiveTyping: true })
  }, imageSearchDebounceMs)
}

function openImageDialog() {
  clearImageSearchDebounce()
  cancelInFlightImageSearch()
  isReplacingImage.value = false
  isSettingBackground.value = false
  imageTab.value = 'search'
  imageSearchQuery.value = ''
  imageUrlInput.value = ''
  searchResults.value = []
  searchedOnce.value = false
  imageSearchPage.value = 1
  hasMoreResults.value = false
  assetSearchQuery.value = ''
  showImageModal.value = true
}

function openImageReplace() {
  clearImageSearchDebounce()
  cancelInFlightImageSearch()
  isReplacingImage.value = true
  isSettingBackground.value = false
  imageTab.value = 'search'
  imageSearchQuery.value = ''
  imageUrlInput.value = ''
  searchResults.value = []
  searchedOnce.value = false
  imageSearchPage.value = 1
  hasMoreResults.value = false
  assetSearchQuery.value = ''
  showImageModal.value = true
}

function openBackgroundImageDialog() {
  clearImageSearchDebounce()
  cancelInFlightImageSearch()
  isReplacingImage.value = false
  isSettingBackground.value = true
  imageTab.value = 'search'
  imageSearchQuery.value = ''
  imageUrlInput.value = ''
  searchResults.value = []
  searchedOnce.value = false
  imageSearchPage.value = 1
  hasMoreResults.value = false
  assetSearchQuery.value = ''
  showImageModal.value = true
}

function clearBackgroundImage() {
  editorStore.clearSlideBackgroundImage()
  window.$toast?.('Background image removed', 'success', 1500)
}

async function fetchAssetsForEditor(query = '') {
  loadingAssets.value = true
  try {
    const { data } = await api.get('/ppt/assets', {
      params: {
        q: query.trim(),
        limit: 120,
      },
    })
    assetResults.value = Array.isArray(data) ? data : []
  } catch {
    assetResults.value = []
    window.$toast?.('Failed to load assets', 'error')
  } finally {
    loadingAssets.value = false
  }
}

function searchAssets() {
  fetchAssetsForEditor(assetSearchQuery.value || '')
}

async function doImageSearch(options = {}) {
  const { silent = false, fromLiveTyping = false } = options
  const query = imageSearchQuery.value.trim()
  if (query.length < minLiveImageQueryLength) {
    if (!silent) window.$toast?.(`Type at least ${minLiveImageQueryLength} characters`, 'error')
    resetImageSearchState()
    return
  }

  if (!fromLiveTyping) {
    clearImageSearchDebounce()
  }
  cancelInFlightImageSearch()

  imageSearchPage.value = 1
  searchedOnce.value = true
  searchingImage.value = true

  const requestId = ++imageSearchRequestSeq
  const controller = new AbortController()
  imageSearchAbortController = controller

  try {
    const { data } = await api.post(
      '/ppt/search-image',
      {
        query,
        page: imageSearchPage.value,
        per_page: imageSearchPerPage,
      },
      { signal: controller.signal }
    )

    if (requestId !== imageSearchRequestSeq) return

    const urls = data.image_urls || []
    searchResults.value = urls
    hasMoreResults.value = urls.length >= imageSearchPerPage
  } catch (e) {
    if (e?.code === 'ERR_CANCELED') return
    if (requestId !== imageSearchRequestSeq) return
    searchResults.value = []
    hasMoreResults.value = false
    if (!silent) window.$toast?.('Image search failed', 'error')
  } finally {
    if (requestId === imageSearchRequestSeq) {
      searchingImage.value = false
    }
    if (imageSearchAbortController === controller) {
      imageSearchAbortController = null
    }
  }
}

async function loadMoreImages() {
  if (searchingImage.value || !imageSearchQuery.value.trim()) return
  if (imageSearchQuery.value.trim().length < minLiveImageQueryLength) return

  clearImageSearchDebounce()
  cancelInFlightImageSearch()

  searchingImage.value = true
  const requestId = ++imageSearchRequestSeq
  const controller = new AbortController()
  imageSearchAbortController = controller

  try {
    imageSearchPage.value += 1
    const { data } = await api.post(
      '/ppt/search-image',
      {
        query: imageSearchQuery.value.trim(),
        page: imageSearchPage.value,
        per_page: imageSearchPerPage,
      },
      { signal: controller.signal }
    )

    if (requestId !== imageSearchRequestSeq) return

    const urls = data.image_urls || []
    if (urls.length === 0) {
      hasMoreResults.value = false
      return
    }
    const set = new Set(searchResults.value)
    urls.forEach(u => set.add(u))
    searchResults.value = Array.from(set)
    hasMoreResults.value = urls.length >= imageSearchPerPage
  } catch (e) {
    if (e?.code === 'ERR_CANCELED') return
    window.$toast?.('Image search failed', 'error')
  } finally {
    if (requestId === imageSearchRequestSeq) {
      searchingImage.value = false
    }
    if (imageSearchAbortController === controller) {
      imageSearchAbortController = null
    }
  }
}

async function searchImage(query) {
  if (!query?.trim() || query.trim().length < minLiveImageQueryLength) return
  searchingImage.value = true
  try {
    const { data } = await api.post('/ppt/search-image', {
      query: query.trim(),
      page: 1,
      per_page: 1,
    })
    const url = data.image_urls?.[0]
    if (url && editorStore.activeElementId) {
      editorStore.updateElement(editorStore.activeElementId, { src: url })
      window.$toast?.('Image updated!', 'success', 2000)
    }
  } catch {
    window.$toast?.('Image search failed', 'error')
  } finally {
    searchingImage.value = false
  }
}

function insertImageUrl(url) {
  if (!url?.trim()) return

  if (isSettingBackground.value) {
    editorStore.setSlideBackgroundImage(url)
    showImageModal.value = false
    isSettingBackground.value = false
    window.$toast?.('Background image set', 'success', 2000)
    return
  }

  if (isReplacingImage.value && editorStore.activeElementId && editorStore.activeElement?.type === 'image') {
    editorStore.updateElement(editorStore.activeElementId, { src: url })
  } else {
    editorStore.addElement(createImageElement({
      x: 200 + Math.random() * 100,
      y: 100 + Math.random() * 60,
      width: 400,
      height: 280,
      src: url,
      borderRadius: 8,
    }))
  }

  showImageModal.value = false
  window.$toast?.('Image added!', 'success', 2000)
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = () => {
    insertImageUrl(reader.result)
  }
  reader.readAsDataURL(file)

  // Reset input
  e.target.value = ''
}
</script>

<style scoped>
.editor-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-loading {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.editor-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

/* ─── Image Modal ────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-modal {
  width: 520px;
  max-width: 90vw;
  max-height: 80vh;
  border-radius: 16px;
  padding: 24px;
  position: relative;
  overflow-y: auto;
}

.modal-title {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 20px;
}

.modal-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background: var(--bg-input);
  border-radius: 10px;
  padding: 3px;
}

.modal-tabs button {
  flex: 1;
  padding: 8px;
  background: none;
  border: none;
  color: var(--text-muted);
  border-radius: 8px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 500;
  transition: all 0.15s;
}

.modal-tabs button.active {
  background: var(--accent-primary);
  color: white;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-search-row {
  display: flex;
  gap: 8px;
}

.modal-search-row .prop-input {
  flex: 1;
  padding: 10px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 8px;
  font-size: 0.85rem;
  font-family: var(--font-sans);
  outline: none;
}
.modal-search-row .prop-input:focus {
  border-color: var(--accent-primary);
}

.modal-search-btn {
  padding: 10px 16px;
  background: var(--accent-primary);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  color: white;
  transition: all 0.15s;
}
.modal-search-btn:hover { opacity: 0.9; }
.modal-search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.search-results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  transition: all 0.15s;
}
.search-result-item:hover {
  border-color: var(--accent-primary);
  transform: scale(1.03);
}
.search-result-item img {
  width: 100%;
  height: 100px;
  object-fit: cover;
  display: block;
}

.asset-chip {
  padding: 6px 8px;
  font-size: 0.68rem;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.35);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-fallback {
  width: 100%;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-card);
}

.modal-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
  padding: 20px;
}

.modal-action-btn {
  padding: 10px 20px;
  background: var(--accent-gradient);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.15s;
}
.modal-action-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(108,99,255,0.3); }
.modal-action-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.search-more-row {
  display: flex;
  justify-content: center;
  margin-top: 6px;
}

.upload-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-muted);
  font-size: 0.85rem;
}
.upload-dropzone:hover {
  border-color: var(--accent-primary);
  background: rgba(108, 99, 255, 0.05);
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  border-radius: 50%;
  cursor: pointer;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.modal-close:hover {
  background: rgba(255, 71, 87, 0.2);
  color: #ff6b81;
}
</style>

<style scoped>
/* ═══ Generation Overlay ═══════════════════════════ */
.generation-overlay {
  position: relative;
  z-index: 100;
  background: linear-gradient(
    135deg,
    rgba(108, 99, 255, 0.15) 0%,
    rgba(78, 205, 196, 0.1) 50%,
    rgba(255, 101, 132, 0.1) 100%
  );
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(108, 99, 255, 0.3);
  padding: 0;
  overflow: hidden;
}

.generation-overlay::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(108, 99, 255, 0.08) 50%,
    transparent 100%
  );
  animation: gen-shimmer-bg 3s ease-in-out infinite;
}

@keyframes gen-shimmer-bg {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

.gen-overlay-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  gap: 24px;
}

.gen-overlay-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.gen-sparkle {
  position: relative;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sparkle-icon {
  font-size: 1.3rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: sparkle-pulse 1.5s ease-in-out infinite;
  z-index: 1;
}

@keyframes sparkle-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.8; }
}

.sparkle-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 2s linear infinite;
}

.sparkle-ring-2 {
  inset: 5px;
  border-top-color: var(--accent-secondary);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.gen-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.gen-title {
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.gen-subtitle {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin: 0;
  max-width: 300px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gen-overlay-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
}

.gen-slide-counter {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.slide-count-current {
  font-size: 1.6rem;
  font-weight: 800;
  font-family: var(--font-display);
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}

.slide-count-divider {
  font-size: 1rem;
  color: var(--text-muted);
  margin: 0 1px;
}

.slide-count-total {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.slide-count-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-left: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.gen-progress-bar {
  width: 160px;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.gen-progress-fill {
  height: 100%;
  background: var(--accent-gradient);
  border-radius: 999px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.gen-progress-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.3) 50%,
    transparent 100%
  );
  animation: progress-shimmer 1.8s ease-in-out infinite;
}

@keyframes progress-shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Overlay transition */
.gen-overlay-enter-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.gen-overlay-leave-active {
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.gen-overlay-enter-from {
  opacity: 0;
  transform: translateY(-100%);
}
.gen-overlay-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}

/* ─── Feedback Modal ───────────────────────────── */
.feedback-overlay {
  z-index: 10000;
}

.feedback-modal {
  width: 460px;
  max-width: 92vw;
  padding: 32px;
  text-align: center;
  border-radius: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.4);
  animation: feedbackSlideIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes feedbackSlideIn {
  from { opacity: 0; transform: scale(0.9) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.feedback-header {
  margin-bottom: 20px;
}

.feedback-icon {
  font-size: 2rem;
  margin-bottom: 8px;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: sparkle-pulse 2s ease-in-out infinite;
}

.feedback-header h3 {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 4px;
}

.feedback-subtitle {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.feedback-stars {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
}

.star-btn {
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.15);
  transition: all 0.2s ease;
  padding: 4px;
}

.star-btn.active {
  color: #FFD93D;
  text-shadow: 0 0 12px rgba(255, 217, 61, 0.4);
  transform: scale(1.15);
}

.star-btn:hover {
  color: #FFD93D;
  transform: scale(1.2);
}

.feedback-fields {
  text-align: left;
  margin-bottom: 20px;
}

.feedback-fields label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 6px;
  margin-top: 12px;
  font-weight: 500;
}

.feedback-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  resize: vertical;
  transition: border-color 0.2s;
}

.feedback-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.feedback-input::placeholder {
  color: var(--text-muted);
}

.feedback-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.feedback-actions .btn-primary {
  padding: 10px 24px;
}

.feedback-actions .btn-secondary {
  padding: 10px 20px;
}
</style>
