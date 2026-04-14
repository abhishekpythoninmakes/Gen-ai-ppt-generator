<template>
  <div class="settings-page">
    <div class="settings-container animate-fade-in">
      <div class="settings-header">
        <h1>Settings</h1>
        <p>Configure your API keys and AI model for generation</p>
      </div>

      <LoadingSpinner v-if="loading" text="Loading settings..." />

      <form v-else @submit.prevent="handleSave" class="settings-form">
        <!-- LLM Model Selection -->
        <div class="settings-section model-section">
          <div class="section-icon" style="background: linear-gradient(135deg, #a855f7, #6366f1)">🧠</div>
          <div class="section-body">
            <h3>AI Model <span class="tag tag-model">Active</span></h3>
            <p>Choose which AI model to use for generating presentations. Different models have different capabilities and speeds.</p>
            <div class="model-select-wrapper">
              <select id="llm-model" v-model="form.selected_llm_model" class="input-field model-select">
                <optgroup label="── Groq (Fast & Free) ──">
                  <option value="groq/llama-3.3-70b-versatile">Llama 3.3 70B Versatile</option>
                  <option value="groq/llama-3.1-8b-instant">Llama 3.1 8B Instant</option>
                  <option value="groq/mixtral-8x7b-32768">Mixtral 8x7B</option>
                </optgroup>
                <optgroup label="── OpenAI ──">
                  <option value="openai/gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="openai/gpt-4">GPT-4</option>
                  <option value="openai/gpt-4-32k">GPT-4 32K</option>
                  <option value="openai/gpt-4o">GPT-4o</option>
                  <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
                  <option value="openai/gpt-4.1">GPT-4.1</option>
                  <option value="openai/gpt-4.1-mini">GPT-4.1 Mini</option>
                  <option value="openai/gpt-4.1-nano">GPT-4.1 Nano</option>
                  <option value="openai/gpt-5-nano">GPT-5 Nano</option>
                  <option value="openai/gpt-5-mini">GPT-5 Mini</option>
                  <option value="openai/gpt-5.4">GPT-5.4</option>
                  <option value="openai/gpt-5.4-pro">GPT-5.4 Pro</option>
                  <option value="openai/gpt-5.4-mini">GPT-5.4 Mini</option>
                  <option value="openai/gpt-5.4-nano">GPT-5.4 Nano</option>
                </optgroup>
              </select>
              <div class="model-badge" :class="modelProvider">
                {{ modelProvider === 'openai' ? 'OpenAI' : 'Groq' }}
              </div>
            </div>
          </div>
        </div>

        <!-- OpenAI API Key -->
        <div class="settings-section">
          <div class="section-icon" style="background: linear-gradient(135deg, #10b981, #06b6d4)">🔑</div>
          <div class="section-body">
            <h3>OpenAI API Key <span v-if="modelProvider === 'openai'" class="tag">Required</span></h3>
            <p>Required when using OpenAI models (GPT series). Get your key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">platform.openai.com</a></p>
            <input
              id="openai-key"
              v-model="form.openai_api_key"
              type="password"
              class="input-field"
              placeholder="sk-..."
              autocomplete="off"
            />
          </div>
        </div>

        <!-- Groq API Key -->
        <div class="settings-section">
          <div class="section-icon" style="background: linear-gradient(135deg, #6c63ff, #b06cff)">🤖</div>
          <div class="section-body">
            <h3>Groq API Key <span v-if="modelProvider === 'groq'" class="tag">Required</span></h3>
            <p>Required when using Groq models (Llama, Mixtral). Get your key from <a href="https://console.groq.com" target="_blank" rel="noopener">console.groq.com</a></p>
            <input
              id="groq-key"
              v-model="form.groq_api_key"
              type="password"
              class="input-field"
              placeholder="gsk_..."
              autocomplete="off"
            />
          </div>
        </div>

        <div class="settings-section">
          <div class="section-icon" style="background: linear-gradient(135deg, #2ed573, #7bed9f)">📷</div>
          <div class="section-body">
            <h3>Pexels API Key <span class="tag">Primary</span></h3>
            <p>Primary image source. Get your key from <a href="https://www.pexels.com/api/" target="_blank" rel="noopener">pexels.com/api</a></p>
            <input
              id="pexels-key"
              v-model="form.pexels_api_key"
              type="password"
              class="input-field"
              placeholder="Enter Pexels API key"
              autocomplete="off"
            />
          </div>
        </div>

        <div class="settings-section">
          <div class="section-icon" style="background: linear-gradient(135deg, #ff6584, #ff4757)">🖼️</div>
          <div class="section-body">
            <h3>Unsplash API Keys <span class="tag tag-fallback">Fallback</span></h3>
            <p>Fallback image source. Get your keys from <a href="https://unsplash.com/developers" target="_blank" rel="noopener">unsplash.com/developers</a>. Create an app to get both keys.</p>
            <div class="key-group">
              <label for="unsplash-access-key">Access Key</label>
              <input
                id="unsplash-access-key"
                v-model="form.unsplash_access_key"
                type="password"
                class="input-field"
                placeholder="Enter Unsplash Access Key"
                autocomplete="off"
              />
            </div>
            <div class="key-group">
              <label for="unsplash-secret-key">Secret Key</label>
              <input
                id="unsplash-secret-key"
                v-model="form.unsplash_secret_key"
                type="password"
                class="input-field"
                placeholder="Enter Unsplash Secret Key"
                autocomplete="off"
              />
            </div>
          </div>
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>

        <div class="form-actions">
          <button type="submit" class="btn-primary" :disabled="saving">
            <span v-if="saving" class="btn-spinner"></span>
            {{ saving ? 'Saving...' : 'Save Settings' }}
          </button>
        </div>
      </form>

      <!-- ─── Usage & Billing Dashboard ──────────────────── -->
      <div class="usage-dashboard animate-fade-in" v-if="!loading">
        <div class="usage-header">
          <h2>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/>
            </svg>
            Usage & Billing
          </h2>
          <button class="refresh-btn" @click="fetchUsage" :disabled="usageLoading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: usageLoading }">
              <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
            </svg>
          </button>
        </div>

        <!-- Summary Cards -->
        <div class="usage-summary-row">
          <div class="summary-card glass">
            <div class="summary-icon" style="background: linear-gradient(135deg, #6366f1, #a855f7)">⚡</div>
            <div class="summary-info">
              <span class="summary-value">{{ animatedTokens.toLocaleString() }}</span>
              <span class="summary-label">Total Tokens</span>
            </div>
          </div>
          <div class="summary-card glass">
            <div class="summary-icon" style="background: linear-gradient(135deg, #10b981, #06b6d4)">💰</div>
            <div class="summary-info">
              <span class="summary-value">${{ animatedCost.toFixed(4) }}</span>
              <span class="summary-label">Total Cost</span>
            </div>
          </div>
          <div class="summary-card glass">
            <div class="summary-icon" style="background: linear-gradient(135deg, #f59e0b, #ef4444)">📊</div>
            <div class="summary-info">
              <span class="summary-value">{{ usageSummary.total_generations }}</span>
              <span class="summary-label">Generations</span>
            </div>
          </div>
        </div>

        <!-- Recent Generations -->
        <div class="chart-card glass" v-if="recentGenerations.length">
          <h3>Token Usage per Generation (Recent)</h3>
          <div class="recent-bars">
            <div v-for="g in recentGenerations" :key="g.id" class="recent-bar">
              <div class="recent-bar-track">
                <div
                  class="recent-bar-fill"
                  :style="{ transform: `scaleY(${recentBarsReady ? g.tokensPct : 0})` }"
                  :title="`${g.dateLabel}: ${g.total_tokens.toLocaleString()} tokens ($${g.cost_usd.toFixed(4)})`"
                ></div>
              </div>
              <div class="recent-bar-meta">
                <div class="recent-bar-tokens">{{ g.total_tokens.toLocaleString() }}</div>
                <div class="recent-bar-date">{{ g.dateLabel }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Detailed Generation Log -->
        <div class="table-card glass" v-if="usageLogRows.length">
          <h3>Generation Usage Log</h3>
          <div class="table-wrapper">
            <table class="usage-table usage-log-table">
              <thead>
                <tr>
                  <th>Date & Time</th>
                  <th>Type</th>
                  <th>Model</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in usageLogRows" :key="row.id" class="table-row-anim">
                  <td>{{ row.createdLabel }}</td>
                  <td>
                    <span class="job-type-badge" :class="row.job_type">
                      {{ row.jobTypeLabel }}
                    </span>
                  </td>
                  <td>{{ row.modelLabel }}</td>
                  <td>{{ row.total_tokens.toLocaleString() }}</td>
                  <td class="cost-cell">${{ row.cost_usd.toFixed(4) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Usage Chart -->
        <div class="chart-card glass" v-if="usageSummary.daily && usageSummary.daily.length">
          <h3>Token Usage (Last 30 Days)</h3>
          <div class="chart-container">
            <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="usage-chart" preserveAspectRatio="none">
              <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#6366f1" stop-opacity="0.4" />
                  <stop offset="100%" stop-color="#6366f1" stop-opacity="0.02" />
                </linearGradient>
              </defs>
              <!-- Grid lines -->
              <line v-for="i in 4" :key="'grid-'+i"
                :x1="0" :y1="chartHeight * i / 4" :x2="chartWidth" :y2="chartHeight * i / 4"
                stroke="rgba(255,255,255,0.06)" stroke-width="1" />
              <!-- Area fill -->
              <path :d="chartAreaPath" fill="url(#chartGrad)" class="chart-area-anim" />
              <!-- Line -->
              <path :d="chartLinePath" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="chart-line-anim" />
              <!-- Dots -->
              <circle v-for="(pt, idx) in chartPoints" :key="idx"
                :cx="pt.x" :cy="pt.y" r="3"
                fill="#6366f1" stroke="#1a1a2e" stroke-width="1.5"
                class="chart-dot-anim"
                :style="{ animationDelay: (idx * 20) + 'ms' }"
              >
                <title>{{ usageSummary.daily[idx]?.date }}: {{ usageSummary.daily[idx]?.tokens }} tokens</title>
              </circle>
            </svg>
          </div>
        </div>

        <!-- Per-Model Cost Table -->
        <div class="table-card glass" v-if="usageSummary.by_model && usageSummary.by_model.length">
          <h3>Cost Breakdown by Model</h3>
          <div class="table-wrapper">
            <table class="usage-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Generations</th>
                  <th>Input Tokens</th>
                  <th>Output Tokens</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in usageSummary.by_model" :key="row.model" class="table-row-anim">
                  <td>
                    <span class="model-name-badge" :class="row.model.includes('openai') || row.model.includes('gpt') ? 'openai' : 'groq'">
                      {{ row.model.replace('openai/', '').replace('groq/', '') }}
                    </span>
                  </td>
                  <td>{{ row.count }}</td>
                  <td>{{ row.prompt_tokens.toLocaleString() }}</td>
                  <td>{{ row.completion_tokens.toLocaleString() }}</td>
                  <td class="cost-cell">${{ row.cost_usd.toFixed(4) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else-if="!usageLoading" class="usage-empty glass">
          <p>No usage data yet. Generate a presentation or template to see token usage, cost, and timestamps here.</p>
        </div>
      </div>

      <div class="info-box glass">
        <h4>📌 How It Works</h4>
        <p>Select your preferred AI model from the dropdown above. The system will use the corresponding API key:</p>
        <ol>
          <li><strong>Groq models</strong> — Uses your Groq API key (fast, free tier available)</li>
          <li><strong>OpenAI models</strong> — Uses your OpenAI API key (paid, high quality)</li>
        </ol>
        <p>Images are fetched using Pexels (primary) → Unsplash (fallback) → Placeholder (final fallback).</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import api from '../api'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const loading = ref(true)
const saving = ref(false)
const error = ref('')

const form = reactive({
  groq_api_key: '',
  openai_api_key: '',
  selected_llm_model: 'groq/llama-3.3-70b-versatile',
  pexels_api_key: '',
  unsplash_access_key: '',
  unsplash_secret_key: '',
})

const modelProvider = computed(() => {
  return form.selected_llm_model?.startsWith('openai/') ? 'openai' : 'groq'
})

// ─── Usage state ────────────────────────────────────
const usageLoading = ref(false)
const usageSummary = reactive({
  total_tokens: 0,
  total_cost_usd: 0,
  total_generations: 0,
  by_model: [],
  daily: [],
})

const usageHistoryLoading = ref(false)
const usageHistory = ref([])
let usageRefreshTimer = null

// Controls bar animation when usage history refreshes.
const recentBarsReady = ref(false)
const recentBarLimit = 10

const recentGenerations = computed(() => {
  const items = (usageHistory.value || [])
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, recentBarLimit)

  const maxTokens = Math.max(1, ...items.map(i => i.total_tokens || 0))
  return items.map(i => {
    const tokens = Number(i.total_tokens || 0) || 0
    const cost = Number(i.cost_usd || 0) || 0
    const created = i.created_at ? new Date(i.created_at) : null
    return {
      id: i.id,
      total_tokens: tokens,
      cost_usd: cost,
      tokensPct: tokens / maxTokens,
      dateLabel: created ? created.toLocaleDateString() : '',
      modelLabel: (i.model || '').replace('openai/', '').replace('groq/', ''),
    }
  })
})

const usageLogRows = computed(() => {
  return (usageHistory.value || [])
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 50)
    .map(i => {
      const created = i.created_at ? new Date(i.created_at) : null
      const jobType = (i.job_type || 'ppt').toLowerCase()
      const modelRaw = (i.model || '').replace('openai/', '').replace('groq/', '')
      return {
        id: i.id,
        job_type: jobType,
        jobTypeLabel: jobType === 'template' ? 'Template' : 'PPT',
        modelLabel: modelRaw || 'unknown',
        total_tokens: Number(i.total_tokens || 0) || 0,
        cost_usd: Number(i.cost_usd || 0) || 0,
        createdLabel: created
          ? created.toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
          })
          : '',
      }
    })
})

const animatedTokens = ref(0)
const animatedCost = ref(0)

const chartWidth = 600
const chartHeight = 160

const chartPoints = computed(() => {
  const daily = usageSummary.daily || []
  if (!daily.length) return []
  const maxTokens = Math.max(1, ...daily.map(d => d.tokens || 0))
  const padding = 10
  const usableW = chartWidth - padding * 2
  const usableH = chartHeight - padding * 2
  return daily.map((d, i) => ({
    x: padding + (i / Math.max(1, daily.length - 1)) * usableW,
    y: padding + usableH - ((d.tokens || 0) / maxTokens) * usableH,
  }))
})

const chartLinePath = computed(() => {
  const pts = chartPoints.value
  if (pts.length < 2) return ''
  return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
})

const chartAreaPath = computed(() => {
  const pts = chartPoints.value
  if (pts.length < 2) return ''
  const padding = 10
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
  return `${line} L${pts[pts.length - 1].x},${chartHeight - padding} L${pts[0].x},${chartHeight - padding} Z`
})

function animateCounter(target, current, setter, duration = 800) {
  const start = current
  const diff = target - start
  const startTime = performance.now()
  function tick(now) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
    setter(start + diff * eased)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

async function fetchUsage() {
  usageLoading.value = true
  try {
    const { data } = await api.get('/settings/usage/summary')
    Object.assign(usageSummary, data)
    // Animate counters
    animateCounter(data.total_tokens || 0, animatedTokens.value, v => { animatedTokens.value = Math.round(v) })
    animateCounter(data.total_cost_usd || 0, animatedCost.value, v => { animatedCost.value = v })
  } catch {
    // Silent fail for usage
  } finally {
    usageLoading.value = false
  }
}

async function fetchUsageHistory() {
  if (usageHistoryLoading.value) return
  usageHistoryLoading.value = true
  try {
    const { data } = await api.get('/settings/usage')
    usageHistory.value = data
    // Trigger bar transition when refreshed.
    recentBarsReady.value = false
    requestAnimationFrame(() => {
      recentBarsReady.value = true
    })
  } catch {
    usageHistory.value = []
  } finally {
    usageHistoryLoading.value = false
  }
}

function handleVisibilityChange() {
  if (document.visibilityState !== 'visible') return
  fetchUsage()
  fetchUsageHistory()
}

onMounted(async () => {
  try {
    const { data } = await api.get('/settings')
    Object.assign(form, data)
  } catch {
    window.$toast?.('Failed to load settings', 'error')
  } finally {
    loading.value = false
  }
  // Fetch usage data
  fetchUsage()
  fetchUsageHistory()

  // Auto-refresh usage while user stays on the page.
  document.addEventListener('visibilitychange', handleVisibilityChange)
  usageRefreshTimer = setInterval(() => {
    if (document.visibilityState !== 'visible') return
    fetchUsage()
    fetchUsageHistory()
  }, 15000)
})

onBeforeUnmount(() => {
  if (usageRefreshTimer) clearInterval(usageRefreshTimer)
  usageRefreshTimer = null
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

async function handleSave() {
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.post('/settings', form)
    Object.assign(form, data)
    window.$toast?.('Settings saved!', 'success')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to save settings'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-page {
  flex: 1;
  padding: 40px 24px 60px;
}

.settings-container {
  max-width: 720px;
  margin: 0 auto;
}

.settings-header {
  margin-bottom: 36px;
}

.settings-header h1 {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 6px;
}

.settings-header p {
  color: var(--text-secondary);
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 36px;
}

.settings-section {
  display: flex;
  gap: 20px;
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  transition: border-color var(--transition-normal);
}

.settings-section:hover {
  border-color: var(--border-glow);
}

.model-section {
  border-color: rgba(168, 85, 247, 0.3);
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.05), rgba(99, 102, 241, 0.05));
}

.model-section:hover {
  border-color: rgba(168, 85, 247, 0.5);
}

.section-icon {
  width: 48px;
  height: 48px;
  min-width: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
}

.section-body {
  flex: 1;
}

.section-body h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-body p {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 14px;
  line-height: 1.5;
}

.section-body a {
  color: var(--accent-primary);
  text-decoration: none;
}

.section-body a:hover {
  text-decoration: underline;
}

.model-select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-select {
  flex: 1;
  padding: 12px 16px;
  font-size: 0.95rem;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' fill='none'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%239ca3af' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 14px center;
  padding-right: 36px;
}

.model-badge {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.model-badge.openai {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(6, 182, 212, 0.2));
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.model-badge.groq {
  background: linear-gradient(135deg, rgba(108, 99, 255, 0.2), rgba(176, 108, 255, 0.2));
  color: #b06cff;
  border: 1px solid rgba(176, 108, 255, 0.3);
}

.key-group {
  margin-bottom: 12px;
}

.key-group:last-child {
  margin-bottom: 0;
}

.key-group label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 500;
}

.tag {
  padding: 2px 8px;
  font-size: 0.7rem;
  border-radius: 10px;
  background: rgba(108, 99, 255, 0.2);
  color: var(--accent-primary);
  font-weight: 600;
}

.tag-fallback {
  background: rgba(255, 165, 2, 0.15);
  color: #ffa502;
}

.tag-model {
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(99, 102, 241, 0.25));
  color: #a855f7;
}

.error-text {
  color: var(--accent-secondary);
  font-size: 0.85rem;
  text-align: center;
  padding: 10px;
  background: rgba(255, 101, 132, 0.1);
  border-radius: var(--radius-sm);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.info-box {
  padding: 24px;
  border-radius: var(--radius-lg);
}

.info-box h4 {
  margin-bottom: 10px;
  font-size: 1rem;
}

.info-box p {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.info-box ol {
  margin: 12px 0;
  padding-left: 20px;
}

.info-box li {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 6px;
}

/* ─── Usage Dashboard ─────────────────────────────── */
.usage-dashboard {
  margin-top: 32px;
  margin-bottom: 32px;
}

.usage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.usage-header h2 {
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
}

.refresh-btn {
  padding: 8px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  font-family: var(--font-sans);
  font-size: 0.8rem;
}
.refresh-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}
.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.usage-summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  transition: all 0.25s;
}
.summary-card:hover {
  border-color: var(--border-glow);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}

.summary-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.summary-info {
  display: flex;
  flex-direction: column;
}

.summary-value {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: var(--font-display);
  color: var(--text-primary);
}

.summary-label {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 2px;
}

.chart-card, .table-card {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
  transition: all 0.25s;
}

.chart-card:hover, .table-card:hover {
  border-color: var(--border-glow);
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.2);
}

.chart-card h3, .table-card h3 {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
  letter-spacing: 0.03em;
}

.chart-container {
  width: 100%;
  height: 160px;
}

.usage-chart {
  width: 100%;
  height: 100%;
}

/* ─── Recent Generations Bars ───────────────────────── */
.recent-bars {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  height: 140px;
  margin-bottom: 6px;
}

.recent-bar {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.recent-bar-track {
  width: 100%;
  height: 92px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  position: relative;
  overflow: hidden;
}

.recent-bar-fill {
  position: absolute;
  inset: 0;
  transform-origin: bottom;
  transform: scaleY(0);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.7), rgba(168, 85, 247, 0.55));
  transition: transform 700ms cubic-bezier(0.2, 0.9, 0.2, 1);
  filter: drop-shadow(0 10px 20px rgba(99, 102, 241, 0.12));
}

.recent-bar-meta {
  width: 100%;
  text-align: center;
}

.recent-bar-tokens {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.82rem;
  color: var(--text-primary);
}

.recent-bar-date {
  font-size: 0.68rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.chart-area-anim {
  animation: fadeInUp 0.6s ease-out both;
}

.chart-line-anim {
  stroke-dasharray: 2000;
  stroke-dashoffset: 2000;
  animation: drawLine 1.2s ease-out forwards;
}

.chart-dot-anim {
  opacity: 0;
  animation: popIn 0.3s ease-out forwards;
}

@keyframes drawLine {
  to { stroke-dashoffset: 0; }
}

@keyframes popIn {
  from { opacity: 0; transform: scale(0); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.table-wrapper {
  overflow-x: auto;
}

.usage-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.usage-table th {
  text-align: left;
  padding: 10px 12px;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
}

.usage-table td {
  padding: 10px 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.usage-table tbody tr {
  transition: background 0.15s;
}

.usage-table tbody tr:hover {
  background: rgba(108, 99, 255, 0.04);
}

.table-row-anim {
  animation: fadeInUp 0.3s ease-out both;
}

.model-name-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}

.model-name-badge.openai {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.model-name-badge.groq {
  background: rgba(176, 108, 255, 0.12);
  color: #b06cff;
}

.job-type-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}

.job-type-badge.ppt {
  background: rgba(99, 102, 241, 0.14);
  color: #818cf8;
}

.job-type-badge.template {
  background: rgba(16, 185, 129, 0.14);
  color: #10b981;
}

.usage-log-table td:first-child {
  white-space: nowrap;
}

.cost-cell {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-weight: 600;
  color: #10b981 !important;
}

.usage-empty {
  padding: 32px;
  text-align: center;
  background: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
  font-size: 0.9rem;
}

@media (max-width: 640px) {
  .usage-summary-row {
    grid-template-columns: 1fr;
  }
}
</style>
