<template>
  <div class="admin-page">
    <div class="admin-header">
      <h1>Template Manager</h1>
      <div class="admin-actions">
        <button class="btn-primary" @click="openCreateModal">Create Template</button>
        <router-link class="btn-secondary" to="/admin">Back to Admin</router-link>
      </div>
    </div>

    <div v-if="loading" class="muted">Loading templates...</div>

    <div v-else class="template-grid">
      <div v-for="tpl in templates" :key="tpl.id" class="template-card">
        <div class="thumb" :style="{ backgroundImage: tpl.thumbnail_url ? `url(${tpl.thumbnail_url})` : '' }">
          <span v-if="!tpl.thumbnail_url" class="thumb-placeholder">No Preview</span>
        </div>
        <div class="template-info">
          <div class="title">{{ tpl.title }}</div>
          <div class="status" :class="tpl.status">{{ tpl.status }}</div>
        </div>
        <div class="template-actions">
          <router-link class="btn-small" :to="`/admin/templates/${tpl.id}/editor`">Edit</router-link>
          <button class="btn-small" @click="togglePublish(tpl)">
            {{ tpl.status === 'published' ? 'Unpublish' : 'Publish' }}
          </button>
          <button class="btn-small danger" @click="deleteTemplate(tpl)">Delete</button>
        </div>
      </div>
    </div>

    <!-- Create Template Modal -->
    <Teleport to="body">
      <div v-if="showCreate" class="modal-overlay" @click.self="closeCreateModal">
        <div class="modal-card">
          <h3>Create Template</h3>
          <p class="muted">Describe the template you want, or create from scratch.</p>

          <textarea v-model="prompt" class="input" rows="4" placeholder="e.g., Create a template for water pollution for class 2..."></textarea>

          <div v-if="generating" class="gen-progress">
            <div class="progress-header">
              <div class="pulse-dot"></div>
              <div class="progress-title">AI Template Generation</div>
              <div class="percent">{{ genProgress }}%</div>
            </div>

            <div class="stage-rail">
              <div
                v-for="(stage, idx) in stageSteps"
                :key="stage.key"
                class="stage-pill"
                :class="{
                  active: idx === currentStageIndex,
                  done: idx < currentStageIndex
                }"
              >
                {{ stage.label }}
              </div>
            </div>

            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${genProgress}%` }">
                <span class="progress-gloss"></span>
              </div>
            </div>
            <div class="progress-meta">
              <span class="stage">{{ stageLabel }}</span>
              <span class="hint">{{ stageHint }}</span>
            </div>
          </div>

          <div class="row">
            <label>Slides</label>
            <div class="slide-controls">
              <input
                v-model.number="numSlides"
                type="number"
                min="1"
                max="30"
                class="input small slide-input"
              />
              <select v-model.number="numSlides" class="input small slide-select">
                <option :value="4">4</option>
                <option :value="6">6</option>
                <option :value="8">8</option>
                <option :value="10">10</option>
                <option :value="12">12</option>
                <option :value="14">14</option>
                <option :value="16">16</option>
              </select>
            </div>
          </div>

          <p v-if="genError" class="error-text">{{ genError }}</p>

          <div class="modal-actions">
            <button class="btn-secondary" :disabled="generating" @click="createBlank">Create from Scratch</button>
            <button class="btn-primary" :disabled="!prompt.trim() || generating" @click="generateTemplate">
              Generate from Prompt
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const templates = ref([])
const loading = ref(false)
const showCreate = ref(false)
const prompt = ref('')
const numSlides = ref(6)
const generating = ref(false)
const genProgress = ref(0)
const genStage = ref('queued')
const genError = ref('')
let pollTimer = null
const stageSteps = [
  { key: 'queued', label: 'Queued' },
  { key: 'content_generation', label: 'Content' },
  { key: 'image_generation', label: 'Visuals' },
  { key: 'slide_design', label: 'Design' },
  { key: 'saving', label: 'Saving' },
  { key: 'done', label: 'Done' },
]
const stageHintMap = {
  queued: 'Preparing job',
  content_generation: 'Structuring slide narrative',
  image_generation: 'Matching images/icons and assets',
  slide_design: 'Balancing layout and typography',
  saving: 'Persisting template to workspace',
  done: 'Final checks',
  failed: 'Generation halted',
}
const currentStageIndex = computed(() => {
  const idx = stageSteps.findIndex(s => s.key === genStage.value)
  return idx === -1 ? 0 : idx
})
const stageHint = computed(() => stageHintMap[genStage.value] || 'Working...')

const stageLabel = computed(() => {
  switch (genStage.value) {
    case 'content_generation':
      return 'Generating content'
    case 'image_generation':
      return 'Fetching images'
    case 'slide_design':
      return 'Designing slides'
    case 'saving':
      return 'Saving template'
    case 'done':
      return 'Finalizing'
    case 'failed':
      return 'Failed'
    default:
      return 'Queued'
  }
})

async function fetchTemplates() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/templates')
    templates.value = data
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  prompt.value = ''
  numSlides.value = 6
  genProgress.value = 0
  genStage.value = 'queued'
  genError.value = ''
  generating.value = false
  showCreate.value = true
}

function closeCreateModal() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  showCreate.value = false
}

async function generateTemplate() {
  genError.value = ''
  generating.value = true
  genProgress.value = 0
  genStage.value = 'queued'
  try {
    const requestedSlides = Math.max(1, Math.min(30, Math.round(Number(numSlides.value) || 6)))
    numSlides.value = requestedSlides

    const { data } = await api.post('/admin/templates/generate', {
      prompt: prompt.value,
      num_slides: requestedSlides,
      slide_width: 960,
      slide_height: 540,
    })
    // Navigate immediately to editor in streaming mode (same as PPT generation)
    showCreate.value = false
    generating.value = false
    router.push({
      name: 'TemplateEditorGenerating',
      params: { jobId: data.id },
    })
  } catch (e) {
    genError.value = e.response?.data?.detail || 'Failed to create template'
    generating.value = false
  }
}

async function createBlank() {
  if (generating.value) return
  loading.value = true
  try {
    const { data } = await api.post('/admin/templates/blank')
    templates.value.unshift(data)
    window.$toast?.('Blank template created (draft)', 'success')
    showCreate.value = false
  } catch (e) {
    window.$toast?.(e.response?.data?.detail || 'Failed to create template', 'error')
  } finally {
    loading.value = false
  }
}

async function togglePublish(tpl) {
  loading.value = true
  try {
    const path = tpl.status === 'published' ? 'unpublish' : 'publish'
    const { data } = await api.post(`/admin/templates/${tpl.id}/${path}`)
    const idx = templates.value.findIndex(t => t.id === data.id)
    if (idx !== -1) templates.value[idx] = data
  } catch (e) {
    window.$toast?.(e.response?.data?.detail || 'Failed to update template', 'error')
  } finally {
    loading.value = false
  }
}

async function deleteTemplate(tpl) {
  loading.value = true
  try {
    await api.delete(`/admin/templates/${tpl.id}`)
    templates.value = templates.value.filter(t => t.id !== tpl.id)
  } catch (e) {
    window.$toast?.(e.response?.data?.detail || 'Failed to delete template', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(fetchTemplates)
onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.admin-page {
  padding: 32px 24px;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.admin-actions {
  display: flex;
  gap: 10px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.template-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.thumb {
  height: 140px;
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1a1a2e;
}
.thumb-placeholder {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.template-info {
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title {
  font-size: 0.9rem;
  font-weight: 600;
}
.status {
  font-size: 0.7rem;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.1);
}
.status.published {
  background: rgba(46, 213, 115, 0.2);
  color: #7bed9f;
}

.template-actions {
  display: flex;
  gap: 6px;
  padding: 10px 12px 14px;
}

.btn-small {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.75rem;
}
.btn-small:hover { border-color: var(--accent-primary); color: var(--text-primary); }
.btn-small.danger { border-color: rgba(255,101,132,0.3); color: #ff9bb3; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5000;
}

.modal-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  width: 520px;
  max-width: 90vw;
}

.input {
  width: 100%;
  padding: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  margin: 10px 0;
}
.input.small { width: 120px; }

.error-text {
  color: #ff9bb3;
  font-size: 0.85rem;
  margin-top: 6px;
}

.gen-progress {
  margin: 12px 0 6px;
  padding: 12px;
  border: 1px solid rgba(92, 170, 255, 0.28);
  border-radius: 12px;
  background:
    radial-gradient(circle at 15% 20%, rgba(74, 160, 255, 0.2), transparent 52%),
    radial-gradient(circle at 85% 10%, rgba(92, 255, 189, 0.16), transparent 44%),
    linear-gradient(145deg, rgba(18, 28, 46, 0.85), rgba(14, 20, 36, 0.95));
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.pulse-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #6ed3ff;
  box-shadow: 0 0 0 0 rgba(110, 211, 255, 0.7);
  animation: pulseDot 1.5s ease-out infinite;
}

.progress-title {
  font-size: 0.86rem;
  font-weight: 700;
  color: #dff2ff;
  letter-spacing: 0.02em;
}

.stage-rail {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 10px;
}

.stage-pill {
  text-align: center;
  font-size: 0.7rem;
  padding: 5px 6px;
  border-radius: 999px;
  color: #90a7c9;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.25s ease;
}

.stage-pill.active {
  color: #f7fdff;
  border-color: rgba(110, 211, 255, 0.7);
  background: linear-gradient(120deg, rgba(78, 174, 255, 0.35), rgba(94, 237, 200, 0.35));
}

.stage-pill.done {
  color: #cff9ea;
  border-color: rgba(94, 237, 200, 0.5);
  background: rgba(94, 237, 200, 0.22);
}

.progress-bar {
  width: 100%;
  height: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.16);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ea6ff, #65f0cf 55%, #5fcbff);
  transition: width 0.5s ease;
  position: relative;
}

.progress-gloss {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 35%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.45), transparent);
  animation: glossRun 1.8s linear infinite;
}

.progress-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  font-size: 0.79rem;
  color: #a8c2e2;
}

.hint {
  text-align: right;
  opacity: 0.95;
}

@keyframes pulseDot {
  0% { box-shadow: 0 0 0 0 rgba(110, 211, 255, 0.7); }
  70% { box-shadow: 0 0 0 8px rgba(110, 211, 255, 0); }
  100% { box-shadow: 0 0 0 0 rgba(110, 211, 255, 0); }
}

@keyframes glossRun {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(320%); }
}

@media (max-width: 720px) {
  .stage-rail {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.slide-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.slide-input {
  width: 90px;
  margin: 10px 0;
}

.slide-select {
  width: 90px;
  margin: 10px 0;
}

.modal-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 14px;
}

.muted { color: var(--text-muted); font-size: 0.85rem; }
</style>
