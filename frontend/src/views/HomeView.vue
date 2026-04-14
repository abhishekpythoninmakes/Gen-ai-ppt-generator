<template>
  <div class="home-page">
    <header class="home-header">
      <div class="header-content">
        <div>
          <h1 class="animate-fade-in">Welcome back, <span class="gradient-text">{{ authStore.user?.username }}</span></h1>
          <p class="header-subtitle animate-fade-in">Create, edit, and manage your AI-powered presentations</p>
        </div>
        <router-link to="/create" class="btn-primary btn-create">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
          Create PPT
        </router-link>
      </div>
    </header>

    <main class="home-main">
      <!-- Recent Presentations -->
      <section class="section">
        <div class="section-header">
          <h2>Your Presentations</h2>
          <span class="badge">{{ presentations.length }} total</span>
        </div>

        <LoadingSpinner v-if="loading" text="Loading your presentations..." />

        <div v-else-if="presentations.length === 0" class="empty-state animate-fade-in">
          <div class="empty-icon">📊</div>
          <h3>No presentations yet</h3>
          <p>Create your first AI-powered presentation in seconds</p>
          <router-link to="/create" class="btn-primary">Get Started</router-link>
        </div>

        <div v-else class="ppt-grid">
          <div
            v-for="(ppt, index) in presentations"
            :key="ppt.id"
            class="ppt-card card"
            :style="{ animationDelay: `${index * 0.08}s` }"
            @click="openEditor(ppt.id)"
          >
            <div class="ppt-thumbnail">
              <img
                v-if="ppt.thumbnail_url"
                :src="ppt.thumbnail_url"
                :alt="ppt.title"
                loading="lazy"
              />
              <div v-else class="ppt-placeholder">
                <span>✦</span>
              </div>
            </div>
            <div class="ppt-info">
              <h3 class="ppt-title">{{ ppt.title }}</h3>
              <p class="ppt-date">{{ formatDate(ppt.updated_at) }}</p>
            </div>
            <div class="ppt-actions">
              <button class="action-btn edit-btn" @click.stop="openEditor(ppt.id)" title="Edit">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button class="action-btn delete-btn" @click.stop="confirmDelete(ppt)" title="Delete">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Templates Section -->
      <section class="section">
        <div class="section-header">
          <h2>Quick Start Templates</h2>
        </div>
        <div class="templates-grid">
          <div
            v-for="t in templates"
            :key="t.name"
            class="template-card card"
            @click="useTemplate(t.prompt)"
          >
            <div class="template-icon" :style="{ background: t.gradient }">{{ t.icon }}</div>
            <h3>{{ t.name }}</h3>
            <p>{{ t.desc }}</p>
          </div>
        </div>
      </section>
    </main>

    <!-- Delete Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="deleteTarget" class="modal-overlay" @click="deleteTarget = null">
          <div class="modal-content glass" @click.stop>
            <h3>Delete Presentation</h3>
            <p>Are you sure you want to delete "<strong>{{ deleteTarget.title }}</strong>"? This cannot be undone.</p>
            <div class="modal-actions">
              <button class="btn-secondary" @click="deleteTarget = null">Cancel</button>
              <button class="btn-danger" @click="handleDelete">Delete</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePptStore } from '../stores/ppt'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const router = useRouter()
const authStore = useAuthStore()
const pptStore = usePptStore()

const presentations = ref([])
const loading = ref(true)
const deleteTarget = ref(null)

const templates = [
  { name: 'Business Pitch', icon: '🚀', desc: 'Startup pitch deck', gradient: 'linear-gradient(135deg, #6c63ff, #b06cff)', prompt: 'Create a professional startup pitch deck for a tech company' },
  { name: 'Education', icon: '📚', desc: 'Lecture & tutorials', gradient: 'linear-gradient(135deg, #2ed573, #7bed9f)', prompt: 'Create an educational lecture presentation about modern technology' },
  { name: 'Marketing', icon: '📈', desc: 'Campaign strategy', gradient: 'linear-gradient(135deg, #ff6584, #ff4757)', prompt: 'Create a marketing campaign strategy presentation' },
  { name: 'Product Launch', icon: '🎯', desc: 'New product reveal', gradient: 'linear-gradient(135deg, #ffa502, #ff6348)', prompt: 'Create a product launch presentation for a new app' },
  { name: 'Team Meeting', icon: '👥', desc: 'Status updates', gradient: 'linear-gradient(135deg, #3742fa, #70a1ff)', prompt: 'Create a quarterly team status update presentation' },
  { name: 'Research', icon: '🔬', desc: 'Findings & analysis', gradient: 'linear-gradient(135deg, #a29bfe, #6c5ce7)', prompt: 'Create a research findings and analysis presentation' },
]

onMounted(async () => {
  try {
    await pptStore.fetchPresentations()
    presentations.value = pptStore.presentations
  } catch (e) {
    window.$toast?.('Failed to load presentations', 'error')
  } finally {
    loading.value = false
  }
})

function openEditor(id) {
  router.push({ name: 'Editor', params: { id } })
}

function useTemplate(prompt) {
  router.push({ name: 'Create', query: { prompt } })
}

function confirmDelete(ppt) {
  deleteTarget.value = ppt
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    await pptStore.deletePresentation(deleteTarget.value.id)
    presentations.value = pptStore.presentations
    window.$toast?.('Presentation deleted', 'success')
  } catch {
    window.$toast?.('Failed to delete', 'error')
  }
  deleteTarget.value = null
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.home-page {
  flex: 1;
}

.home-header {
  padding: 40px 32px 32px;
  background: linear-gradient(180deg, rgba(108, 99, 255, 0.06), transparent);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
}

.header-content h1 {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 700;
}

.header-subtitle {
  color: var(--text-secondary);
  margin-top: 6px;
  font-size: 1rem;
}

.btn-create {
  font-size: 1rem;
  padding: 14px 32px;
}

.home-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 32px 60px;
}

.section {
  margin-bottom: 48px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.section-header h2 {
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 600;
}

.badge {
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(108, 99, 255, 0.15);
  color: var(--accent-primary);
  font-size: 0.8rem;
  font-weight: 600;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 64px 32px;
  background: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-lg);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}

.empty-state h3 {
  font-size: 1.3rem;
  margin-bottom: 8px;
}

.empty-state p {
  color: var(--text-secondary);
  margin-bottom: 24px;
}

/* PPT Grid */
.ppt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.ppt-card {
  cursor: pointer;
  overflow: hidden;
  animation: fadeIn 0.4s ease-out backwards;
}

.ppt-thumbnail {
  height: 170px;
  overflow: hidden;
  background: var(--bg-secondary);
}

.ppt-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-slow);
}

.ppt-card:hover .ppt-thumbnail img {
  transform: scale(1.05);
}

.ppt-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  background: linear-gradient(135deg, var(--bg-card), var(--bg-secondary));
  color: var(--text-muted);
}

.ppt-info {
  padding: 16px 18px 12px;
}

.ppt-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ppt-date {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.ppt-actions {
  display: flex;
  gap: 8px;
  padding: 0 18px 14px;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
}

.edit-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.delete-btn:hover {
  color: #ff4757;
  border-color: #ff4757;
}

/* Templates */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.template-card {
  padding: 24px 20px;
  cursor: pointer;
  text-align: center;
}

.template-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin: 0 auto 14px;
}

.template-card h3 {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 6px;
}

.template-card p {
  font-size: 0.8rem;
  color: var(--text-muted);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 24px;
}

.modal-content {
  max-width: 440px;
  width: 100%;
  padding: 32px;
  border-radius: var(--radius-lg);
}

.modal-content h3 {
  font-size: 1.2rem;
  margin-bottom: 12px;
}

.modal-content p {
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.25s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
