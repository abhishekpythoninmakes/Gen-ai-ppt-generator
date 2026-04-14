<template>
  <div class="app-wrapper">
    <NavBar v-if="authStore.isAuthenticated && !isEditorRoute" />
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    <Toast />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import NavBar from './components/NavBar.vue'
import Toast from './components/Toast.vue'

const authStore = useAuthStore()
const route = useRoute()

const isEditorRoute = computed(() => route.name === 'Editor')
</script>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
