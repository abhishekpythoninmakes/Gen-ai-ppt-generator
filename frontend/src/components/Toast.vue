<template>
  <Teleport to="body">
    <transition name="toast-anim">
      <div v-if="visible" :class="['toast', `toast-${type}`]" @click="dismiss">
        {{ message }}
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
const message = ref('')
const type = ref('info')
let timer = null

function show(msg, t = 'info', duration = 4000) {
  message.value = msg
  type.value = t
  visible.value = true
  clearTimeout(timer)
  timer = setTimeout(() => { visible.value = false }, duration)
}

function dismiss() {
  visible.value = false
}

// Global event bus for toast
function handleToast(e) {
  show(e.detail.message, e.detail.type, e.detail.duration)
}

onMounted(() => {
  window.addEventListener('app-toast', handleToast)
})

onUnmounted(() => {
  window.removeEventListener('app-toast', handleToast)
})

// Export helper
window.$toast = (msg, t = 'info', duration = 4000) => {
  window.dispatchEvent(new CustomEvent('app-toast', {
    detail: { message: msg, type: t, duration }
  }))
}
</script>

<style scoped>
.toast-anim-enter-active {
  transition: all 0.3s ease-out;
}
.toast-anim-leave-active {
  transition: all 0.2s ease-in;
}
.toast-anim-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.toast-anim-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.95);
}
</style>
