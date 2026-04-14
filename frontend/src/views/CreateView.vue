<template>
  <div class="create-page">
    <div class="create-container">
      <div class="create-header animate-fade-in">
        <h1>Create a <span class="gradient-text">Presentation</span></h1>
        <p>Describe your topic and let AI generate a stunning presentation for you</p>
      </div>

      <!-- Input Form -->
      <div class="create-form animate-slide-up">
        <div class="prompt-box">
          <textarea
            id="prompt-input"
            v-model="prompt"
            class="input-field prompt-textarea"
            placeholder="e.g., Create a pitch deck for an AI-powered fitness app that tracks workouts and nutrition..."
            rows="4"
            @keydown.ctrl.enter="handleGenerate"
            :disabled="generating"
          ></textarea>
          <div class="prompt-footer">
            <div class="slide-count">
              <label for="slide-count">Slides:</label>
              <input
                id="slide-count"
                type="number"
                min="1"
                max="30"
                v-model.number="numSlides"
                class="input-field slide-input"
                :disabled="generating"
              />
              <select v-model.number="numSlides" class="input-field slide-select" :disabled="generating">
                <option :value="4">4</option>
                <option :value="6">6</option>
                <option :value="8">8</option>
                <option :value="10">10</option>
                <option :value="12">12</option>
                <option :value="14">14</option>
                <option :value="16">16</option>
              </select>
            </div>
            <span class="hint">Ctrl + Enter to generate</span>
          </div>
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>

        <div class="create-actions">
          <button class="btn-primary btn-generate" @click="handleGenerate" :disabled="!prompt.trim() || generating">
            <svg v-if="!generating" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13,2 3,14 12,14 11,22 21,10 12,10"/></svg>
            <span v-if="generating" class="btn-spinner"></span>
            {{ generating ? 'Starting generation...' : 'Generate with AI' }}
          </button>
          <button class="btn-secondary" @click="handleBlank" :disabled="generating">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            Build from Scratch
          </button>
        </div>

        <!-- Templates -->
        <div class="suggestions">
          <p class="suggestions-label">Templates:</p>
          <div v-if="loadingTemplates" class="muted">Loading templates...</div>
          <div v-else class="template-grid">
            <div v-for="t in templates" :key="t.id" class="template-card">
              <div class="thumb" :style="{ backgroundImage: t.thumbnail_url ? `url(${t.thumbnail_url})` : '' }">
                <span v-if="!t.thumbnail_url" class="thumb-placeholder">No Preview</span>
              </div>
              <div class="template-title">{{ t.title }}</div>
              <button class="btn-secondary btn-use" @click="useTemplate(t.id)">Use Template</button>
            </div>
            <div v-if="!templates.length && !loadingTemplates" class="muted">No templates published yet.</div>
          </div>
        </div>

        <!-- Suggestions -->
        <div class="suggestions">
          <p class="suggestions-label">Try a suggestion:</p>
          <div class="suggestion-chips">
            <button
              v-for="s in suggestions"
              :key="s"
              class="chip"
              @click="prompt = s"
            >{{ s }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePptStore } from '../stores/ppt'
import api from '../api'

const router = useRouter()
const route = useRoute()
const pptStore = usePptStore()

const prompt = ref('')
const numSlides = ref(6)
const generating = ref(false)
const error = ref('')
const templates = ref([])
const loadingTemplates = ref(false)

const suggestions = [
  'Pitch deck for a sustainable energy startup',
  'Introduction to Machine Learning for beginners',
  'Q3 Marketing performance review',
  'Product roadmap for a SaaS platform',
  'Team onboarding and culture presentation',
]

onMounted(() => {
  if (route.query.prompt) {
    prompt.value = route.query.prompt
  }
  fetchTemplates()
})

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

async function handleGenerate() {
  if (!prompt.value.trim() || generating.value) return
  error.value = ''
  generating.value = true

  try {
    const requestedSlides = Math.max(1, Math.min(30, Math.round(Number(numSlides.value) || 6)))
    numSlides.value = requestedSlides

    // Start generation job (returns immediately with job ID)
    const job = await pptStore.startGeneratePpt(prompt.value, requestedSlides, 960, 540)

    // Navigate immediately to editor in generating mode
    // The editor will connect to SSE and show slides appearing live
    router.push({
      name: 'EditorGenerating',
      params: { jobId: job.id },
    })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Generation failed. Make sure your API key is set in Settings.'
    generating.value = false
  }
}

async function handleBlank() {
  try {
    const ppt = await pptStore.createBlank()
    router.push({ name: 'Editor', params: { id: ppt.id } })
  } catch {
    window.$toast?.('Failed to create presentation', 'error')
  }
}

async function useTemplate(templateId) {
  try {
    const { data } = await api.post(`/templates/${templateId}/use`)
    window.$toast?.('Template loaded!', 'success')
    router.push({ name: 'Editor', params: { id: data.id } })
  } catch {
    window.$toast?.('Failed to use template', 'error')
  }
}
</script>

<style scoped>
.create-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  min-height: calc(100vh - 64px);
}

.create-container {
  max-width: 680px;
  width: 100%;
}

.create-header {
  text-align: center;
  margin-bottom: 40px;
}

.create-header h1 {
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 700;
  margin-bottom: 10px;
}

.create-header p {
  color: var(--text-secondary);
  font-size: 1.05rem;
}

/* Form */
.prompt-box {
  margin-bottom: 20px;
}

.prompt-textarea {
  resize: vertical;
  min-height: 120px;
  font-size: 1rem;
  line-height: 1.6;
}

.prompt-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.slide-count {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.slide-select {
  width: 70px;
  padding: 8px 12px;
  font-size: 0.9rem;
}

.slide-input {
  width: 80px;
  padding: 8px 10px;
  font-size: 0.9rem;
  text-align: center;
}

.hint {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.error-text {
  color: var(--accent-secondary);
  font-size: 0.85rem;
  text-align: center;
  padding: 10px;
  background: rgba(255, 101, 132, 0.1);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
}

.create-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 40px;
}

.btn-generate {
  flex: 1;
  justify-content: center;
  padding: 16px;
  font-size: 1rem;
}

.create-actions .btn-secondary {
  flex: 1;
  justify-content: center;
}

/* Button spinner */
.btn-spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-right: 6px;
}

/* Suggestions */
.suggestions {
  border-top: 1px solid var(--border-color);
  padding-top: 24px;
}

.suggestions-label {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.template-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thumb {
  height: 100px;
  background-size: cover;
  background-position: center;
  border-radius: 8px;
  background-color: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb-placeholder {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.template-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-use {
  padding: 8px 10px;
  font-size: 0.8rem;
}

.muted {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.chip {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.82rem;
  font-family: var(--font-sans);
  transition: all var(--transition-fast);
}

.chip:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  background: rgba(108, 99, 255, 0.08);
}
</style>
