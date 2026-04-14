<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
      <div class="bg-orb bg-orb-3"></div>
    </div>

    <div class="auth-container animate-slide-up">
      <div class="auth-header">
        <span class="brand-icon">✦</span>
        <h1 class="gradient-text">Create Account</h1>
        <p class="auth-subtitle">Start generating AI-powered presentations</p>
      </div>

      <form @submit.prevent="handleRegister" class="auth-form">
        <div class="form-group">
          <label for="reg-email">Email</label>
          <input
            id="reg-email"
            v-model="form.email"
            type="email"
            class="input-field"
            placeholder="you@example.com"
            required
            autocomplete="email"
          />
        </div>

        <div class="form-group">
          <label for="reg-username">Username</label>
          <input
            id="reg-username"
            v-model="form.username"
            type="text"
            class="input-field"
            placeholder="Choose a username"
            required
            autocomplete="username"
          />
          <span class="hint">Letters, numbers, underscores only</span>
        </div>

        <div class="form-group">
          <label for="reg-password">Password</label>
          <input
            id="reg-password"
            v-model="form.password"
            type="password"
            class="input-field"
            placeholder="Min 8 chars, uppercase, lowercase, number"
            required
            autocomplete="new-password"
          />
          <div class="password-strength">
            <div class="strength-bar" :class="strengthClass" :style="{ width: strengthPercent + '%' }"></div>
          </div>
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>

        <button type="submit" class="btn-primary btn-full" :disabled="loading">
          <span v-if="loading" class="btn-spinner"></span>
          {{ loading ? 'Creating account...' : 'Create Account' }}
        </button>
      </form>

      <p class="auth-footer">
        Already have an account?
        <router-link to="/login" class="auth-link">Sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ email: '', username: '', password: '' })
const loading = ref(false)
const error = ref('')

const strengthPercent = computed(() => {
  const p = form.password
  if (!p) return 0
  let score = 0
  if (p.length >= 8) score += 25
  if (/[A-Z]/.test(p)) score += 25
  if (/[a-z]/.test(p)) score += 25
  if (/[0-9]/.test(p)) score += 25
  return score
})

const strengthClass = computed(() => {
  if (strengthPercent.value <= 25) return 'weak'
  if (strengthPercent.value <= 50) return 'fair'
  if (strengthPercent.value <= 75) return 'good'
  return 'strong'
})

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await authStore.register(form.email, form.username, form.password)
    window.$toast?.('Account created! Welcome!', 'success')
    router.push({ name: 'Home' })
  } catch (e) {
    const detail = e.response?.data?.detail
    if (Array.isArray(detail)) {
      error.value = detail.map((d) => d.msg).join('. ')
    } else {
      error.value = detail || 'Registration failed.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 24px;
}

.auth-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.4;
}

.bg-orb-1 {
  width: 500px;
  height: 500px;
  background: #b06cff;
  top: -200px;
  left: -100px;
}

.bg-orb-2 {
  width: 400px;
  height: 400px;
  background: #6c63ff;
  bottom: -150px;
  right: -100px;
}

.bg-orb-3 {
  width: 300px;
  height: 300px;
  background: #ff6584;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.15;
}

.auth-container {
  width: 100%;
  max-width: 440px;
  padding: 48px 40px;
  background: var(--bg-glass);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  position: relative;
  z-index: 1;
}

.auth-header {
  text-align: center;
  margin-bottom: 36px;
}

.auth-header .brand-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 12px;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.auth-header h1 {
  font-family: var(--font-display);
  font-size: 2rem;
  margin-bottom: 8px;
}

.auth-subtitle {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.hint {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.password-strength {
  height: 4px;
  background: var(--bg-input);
  border-radius: 4px;
  overflow: hidden;
}

.strength-bar {
  height: 100%;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.strength-bar.weak { background: #ff4757; }
.strength-bar.fair { background: #ffa502; }
.strength-bar.good { background: #2ed573; }
.strength-bar.strong { background: #7bed9f; }

.error-text {
  color: var(--accent-secondary);
  font-size: 0.85rem;
  text-align: center;
  padding: 8px;
  background: rgba(255, 101, 132, 0.1);
  border-radius: var(--radius-sm);
}

.btn-full {
  width: 100%;
  justify-content: center;
  padding: 16px;
  font-size: 1rem;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.auth-link {
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 600;
}

.auth-link:hover {
  color: #8b83ff;
}
</style>
