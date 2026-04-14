import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/create',
    name: 'Create',
    component: () => import('../views/CreateView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/editor/generating/:jobId',
    name: 'EditorGenerating',
    component: () => import('../views/EditorView.vue'),
    meta: { requiresAuth: true, generatingMode: true },
  },
  {
    path: '/editor/:id',
    name: 'Editor',
    component: () => import('../views/EditorView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/templates',
    name: 'AdminTemplates',
    component: () => import('../views/AdminTemplatesView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/assets',
    name: 'AdminAssets',
    component: () => import('../views/AdminAssetsView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/templates/generating/:jobId',
    name: 'TemplateEditorGenerating',
    component: () => import('../views/EditorView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, templateEditor: true, generatingMode: true },
  },
  {
    path: '/admin/templates/:id/editor',
    name: 'TemplateEditor',
    component: () => import('../views/EditorView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, templateEditor: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login' })
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next({ name: 'Home' })
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
