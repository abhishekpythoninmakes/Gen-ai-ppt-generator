<template>
  <div class="admin-page">
    <div class="admin-header">
      <h1>Admin Panel</h1>
      <div class="admin-actions">
        <router-link class="btn-secondary" to="/admin/assets">Assets Manager</router-link>
        <router-link class="btn-secondary" to="/admin/templates">Template Manager</router-link>
        <router-link class="btn-secondary" to="/">Back to App</router-link>
      </div>
    </div>

    <div class="admin-grid">
      <div class="card">
        <h2>Users</h2>
        <p class="muted">Manage users and admin roles.</p>

        <div class="table">
          <div class="row header">
            <div>Username</div>
            <div>Email</div>
            <div>Role</div>
            <div>Action</div>
          </div>
          <div v-for="u in users" :key="u.id" class="row">
            <div>{{ u.username }}</div>
            <div>{{ u.email }}</div>
            <div>
              <span class="badge" :class="{ admin: u.is_admin }">{{ u.is_admin ? 'Admin' : 'User' }}</span>
            </div>
            <div>
              <button
                class="btn-small"
                @click="toggleRole(u)"
                :disabled="loading"
              >
                {{ u.is_admin ? 'Make User' : 'Make Admin' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <h2>Create Admin</h2>
        <p class="muted">Create a new admin user.</p>

        <form @submit.prevent="createAdmin" class="form">
          <input v-model="form.username" class="input" placeholder="Username" required />
          <input v-model="form.email" class="input" type="email" placeholder="Email" required />
          <input v-model="form.password" class="input" type="password" placeholder="Password" required />
          <button class="btn-primary" type="submit" :disabled="loading">
            Create Admin
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const users = ref([])
const loading = ref(false)

const form = ref({
  username: '',
  email: '',
  password: '',
})

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

async function toggleRole(user) {
  loading.value = true
  try {
    const { data } = await api.patch(`/admin/users/${user.id}/role`, { is_admin: !user.is_admin })
    const idx = users.value.findIndex(u => u.id === data.id)
    if (idx !== -1) users.value[idx] = data
  } catch (e) {
    window.$toast?.(e.response?.data?.detail || 'Failed to update role', 'error')
  } finally {
    loading.value = false
  }
}

async function createAdmin() {
  loading.value = true
  try {
    const { data } = await api.post('/admin/users', {
      username: form.value.username.trim(),
      email: form.value.email.trim(),
      password: form.value.password,
      is_admin: true,
    })
    users.value.unshift(data)
    form.value = { username: '', email: '', password: '' }
    window.$toast?.('Admin created', 'success')
  } catch (e) {
    window.$toast?.(e.response?.data?.detail || 'Failed to create admin', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(fetchUsers)
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

.admin-header h1 {
  font-family: var(--font-display);
  font-size: 1.8rem;
}

.admin-actions {
  display: flex;
  gap: 10px;
}

.admin-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 18px;
}

.muted {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin-bottom: 14px;
}

.table {
  display: grid;
  gap: 8px;
}

.row {
  display: grid;
  grid-template-columns: 1fr 1.5fr 0.7fr 1fr;
  gap: 10px;
  align-items: center;
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-color);
}

.row.header {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  font-size: 0.75rem;
}
.badge.admin {
  background: rgba(108,99,255,0.2);
  color: #b8b3ff;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.input {
  padding: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
}

.btn-small {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary);
}
.btn-small:hover { color: var(--text-primary); border-color: var(--accent-primary); }

.btn-secondary {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
}
</style>
