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
        <h1 class="gradient-text">SlideForge</h1>
        <p class="auth-subtitle">Sign in to create stunning presentations with AI</p>
      </div>

      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="form-group">
          <label for="login-identifier">Email or Username</label>
          <input
            id="login-identifier"
            v-model="form.identifier"
            type="text"
            class="input-field"
            placeholder="Enter your email or username"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label for="login-password">Password</label>
          <input
            id="login-password"
            v-model="form.password"
            type="password"
            class="input-field"
            placeholder="Enter your password"
            required
            autocomplete="current-password"
          />
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>

        <button type="submit" class="btn-primary btn-full" :disabled="loading">
          <span v-if="loading" class="btn-spinner"></span>
          {{ loading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>

      <p class="auth-footer">
        Don't have an account?
        <router-link to="/register" class="auth-link">Create one</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ identifier: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(form.identifier, form.password)
    window.$toast?.('Welcome back!', 'success')
    if (authStore.isAdmin) {
      router.push({ name: 'Admin' })
    } else {
      router.push({ name: 'Home' })
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Login failed. Please try again.'
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
  background: #6c63ff;
  top: -200px;
  right: -100px;
}

.bg-orb-2 {
  width: 400px;
  height: 400px;
  background: #ff6584;
  bottom: -150px;
  left: -100px;
}

.bg-orb-3 {
  width: 300px;
  height: 300px;
  background: #b06cff;
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
  transition: color var(--transition-fast);
}

.auth-link:hover {
  color: #8b83ff;
}
</style>
