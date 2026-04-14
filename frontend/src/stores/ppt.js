import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'
import { useAuthStore } from './auth'

export const usePptStore = defineStore('ppt', () => {
  const presentations = ref([])
  const currentPpt = ref(null)
  const loading = ref(false)
  const generating = ref(false)

  async function fetchPresentations() {
    loading.value = true
    try {
      const { data } = await api.get('/ppt/list')
      presentations.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchPresentation(id) {
    loading.value = true
    try {
      const { data } = await api.get(`/ppt/${id}`)
      currentPpt.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function startGeneratePpt(prompt, numSlides = 6, slideWidth = 960, slideHeight = 540) {
    generating.value = true
    try {
      const { data } = await api.post('/ppt/generate', {
        prompt,
        num_slides: numSlides,
        slide_width: slideWidth,
        slide_height: slideHeight,
      })
      // data is now a GenerationJobResponse { id, status, stage, progress, ... }
      return data
    } catch (err) {
      generating.value = false
      throw err
    }
  }

  async function fetchGenerationJob(jobId) {
    const { data } = await api.get(`/ppt/generate/${jobId}`)
    // When done, stop generating state
    if (data.status === 'completed' || data.status === 'failed') {
      generating.value = false
    }
    return data
  }

  /**
   * Connect to SSE stream for real-time slide-by-slide generation events.
   * 
   * @param {number} jobId - Generation job ID
   * @param {object} callbacks - Event handlers:
   *   onStage({stage, message, progress})
   *   onTheme({theme, title, total_slides})
   *   onSlide({index, total, slide})
   *   onComplete({ppt_id, title, total_slides})
   *   onError({message})
   * @returns {function} cleanup - Call to close the connection
   */
  function connectToStream(jobId, callbacks = {}) {
    const authStore = useAuthStore()
    const token = authStore.token
    if (!token) {
      callbacks.onError?.({ message: 'Not authenticated' })
      return () => {}
    }

    const baseUrl = window.location.origin
    const url = `${baseUrl}/api/ppt/generate/${jobId}/stream?token=${encodeURIComponent(token)}`

    let eventSource = null
    let reconnectAttempts = 0
    const maxReconnects = 3
    let lastEventIndex = 0
    let closed = false

    function connect() {
      if (closed) return

      const connectUrl = lastEventIndex > 0
        ? `${url}&last_event=${lastEventIndex}`
        : url

      eventSource = new EventSource(connectUrl)
      generating.value = true

      eventSource.addEventListener('stage', (e) => {
        try {
          const data = JSON.parse(e.data)
          lastEventIndex++
          callbacks.onStage?.(data)
        } catch (err) {
          console.error('Failed to parse stage event:', err)
        }
      })

      eventSource.addEventListener('theme', (e) => {
        try {
          const data = JSON.parse(e.data)
          lastEventIndex++
          callbacks.onTheme?.(data)
        } catch (err) {
          console.error('Failed to parse theme event:', err)
        }
      })

      eventSource.addEventListener('slide', (e) => {
        try {
          const data = JSON.parse(e.data)
          lastEventIndex++
          callbacks.onSlide?.(data)
        } catch (err) {
          console.error('Failed to parse slide event:', err)
        }
      })

      eventSource.addEventListener('complete', (e) => {
        try {
          const data = JSON.parse(e.data)
          lastEventIndex++
          generating.value = false
          callbacks.onComplete?.(data)
        } catch (err) {
          console.error('Failed to parse complete event:', err)
        }
        cleanup()
      })

      eventSource.addEventListener('error', (e) => {
        // Named 'error' event from server (not connection error)
        if (e.data) {
          try {
            const data = JSON.parse(e.data)
            generating.value = false
            callbacks.onError?.(data)
          } catch (err) {
            console.error('Failed to parse error event:', err)
          }
          cleanup()
          return
        }

        // Connection error → attempt reconnect
        if (eventSource.readyState === EventSource.CLOSED) {
          reconnectAttempts++
          if (reconnectAttempts <= maxReconnects) {
            console.warn(`SSE reconnecting (attempt ${reconnectAttempts}/${maxReconnects})...`)
            setTimeout(connect, 1000 * reconnectAttempts)
          } else {
            generating.value = false
            callbacks.onError?.({ message: 'Connection lost. Please check your generation status.' })
            cleanup()
          }
        }
      })

      eventSource.onopen = () => {
        reconnectAttempts = 0 // Reset on successful connection
      }
    }

    function cleanup() {
      closed = true
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
    }

    connect()
    return cleanup
  }

  /**
   * Connect to SSE stream for template generation.
   * Same interface as connectToStream but for admin template generation.
   */
  function connectToTemplateStream(jobId, callbacks = {}) {
    const authStore = useAuthStore()
    const token = authStore.token
    if (!token) {
      callbacks.onError?.({ message: 'Not authenticated' })
      return () => {}
    }

    const baseUrl = window.location.origin
    const url = `${baseUrl}/api/admin/templates/generate/${jobId}/stream?token=${encodeURIComponent(token)}`

    let eventSource = null
    let reconnectAttempts = 0
    const maxReconnects = 3
    let lastEventIndex = 0
    let closed = false

    function connect() {
      if (closed) return

      const connectUrl = lastEventIndex > 0
        ? `${url}&last_event=${lastEventIndex}`
        : url

      eventSource = new EventSource(connectUrl)
      generating.value = true

      eventSource.addEventListener('stage', (e) => {
        try { callbacks.onStage?.(JSON.parse(e.data)); lastEventIndex++ } catch {}
      })
      eventSource.addEventListener('theme', (e) => {
        try { callbacks.onTheme?.(JSON.parse(e.data)); lastEventIndex++ } catch {}
      })
      eventSource.addEventListener('slide', (e) => {
        try { callbacks.onSlide?.(JSON.parse(e.data)); lastEventIndex++ } catch {}
      })
      eventSource.addEventListener('complete', (e) => {
        try {
          generating.value = false
          callbacks.onComplete?.(JSON.parse(e.data))
        } catch {}
        cleanup()
      })
      eventSource.addEventListener('error', (e) => {
        if (e.data) {
          try {
            generating.value = false
            callbacks.onError?.(JSON.parse(e.data))
          } catch {}
          cleanup()
          return
        }
        if (eventSource.readyState === EventSource.CLOSED) {
          reconnectAttempts++
          if (reconnectAttempts <= maxReconnects) {
            setTimeout(connect, 1000 * reconnectAttempts)
          } else {
            generating.value = false
            callbacks.onError?.({ message: 'Connection lost.' })
            cleanup()
          }
        }
      })
      eventSource.onopen = () => { reconnectAttempts = 0 }
    }

    function cleanup() {
      closed = true
      if (eventSource) { eventSource.close(); eventSource = null }
    }

    connect()
    return cleanup
  }

  async function createBlank() {
    const { data } = await api.post('/ppt/blank')
    return data
  }

  async function updatePresentation(id, payload) {
    const { data } = await api.put(`/ppt/${id}`, payload)
    currentPpt.value = data
    return data
  }

  async function deletePresentation(id) {
    await api.delete(`/ppt/${id}`)
    presentations.value = presentations.value.filter((p) => p.id !== id)
  }

  return {
    presentations,
    currentPpt,
    loading,
    generating,
    fetchPresentations,
    fetchPresentation,
    startGeneratePpt,
    fetchGenerationJob,
    connectToStream,
    connectToTemplateStream,
    createBlank,
    updatePresentation,
    deletePresentation,
  }
})
