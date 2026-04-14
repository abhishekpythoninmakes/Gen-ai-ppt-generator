<template>
  <div class="admin-page">
    <div class="admin-header">
      <div>
        <h1>Assets Manager</h1>
        <p class="subtext">Upload brand visuals once, then reuse them in AI slides and templates.</p>
      </div>
      <div class="admin-actions">
        <button class="btn-primary" @click="openUploadModal">Upload Asset</button>
        <router-link class="btn-secondary" to="/admin">Back to Admin</router-link>
      </div>
    </div>

    <div class="asset-toolbar glass">
      <input
        v-model="searchQuery"
        class="search-input"
        placeholder="Search assets by label..."
      />
      <span class="count-pill">{{ filteredAssets.length }} assets</span>
    </div>

    <div v-if="loading" class="muted">Loading assets...</div>

    <div v-else class="assets-grid">
      <div v-for="asset in filteredAssets" :key="asset.id" class="asset-card">
        <div class="thumb">
          <img :src="asset.url" :alt="asset.label" v-if="asset.asset_type === 'image' || asset.asset_type === 'svg'" />
        </div>
        <div class="asset-info">
          <div class="label" :title="asset.label">{{ asset.label || 'Untitled Asset' }}</div>
          <div class="type">{{ asset.asset_type }}</div>
        </div>
        <div class="asset-actions">
          <button class="btn-small danger" @click="deleteAsset(asset.id)">Delete</button>
        </div>
      </div>
      <div v-if="!filteredAssets.length" class="muted">No assets found.</div>
    </div>

    <Teleport to="body">
      <div v-if="showUploadModal" class="modal-overlay" @click.self="closeUploadModal">
        <div class="modal-card">
          <div class="modal-head">
            <h3>Upload Asset</h3>
            <p class="muted">Use drag-and-drop, file picker, or paste an image URL.</p>
          </div>

          <div class="source-tabs">
            <button class="tab-btn" :class="{ active: sourceMode === 'file' }" @click="sourceMode = 'file'">File Upload</button>
            <button class="tab-btn" :class="{ active: sourceMode === 'url' }" @click="sourceMode = 'url'">Image URL</button>
          </div>

          <div v-if="sourceMode === 'file'" class="source-panel">
            <div
              class="dropzone"
              :class="{ dragging: isDragging }"
              @click="fileInput?.click()"
              @dragenter.prevent="onDragEnter"
              @dragover.prevent="onDragOver"
              @dragleave.prevent="onDragLeave"
              @drop.prevent="onDrop"
            >
              <div class="dz-icon">⬆</div>
              <div class="dz-title">Drop image here or click to browse</div>
              <div class="dz-hint">PNG, JPG, JPEG, SVG</div>
            </div>
            <input
              type="file"
              ref="fileInput"
              @change="onFileChange"
              accept="image/*,.svg"
              style="display: none"
            />
          </div>

          <div v-else class="source-panel">
            <label class="field-label">Image URL</label>
            <input
              v-model="formUrl"
              class="input"
              placeholder="https://example.com/image.png"
            />
          </div>

          <div class="meta-grid">
            <div>
              <label class="field-label">Asset Label</label>
              <input v-model="formLabel" class="input" placeholder="e.g., modern office team" />
            </div>
            <div>
              <label class="field-label">Type</label>
              <select v-model="assetType" class="input">
                <option value="image">image</option>
                <option value="svg">svg</option>
              </select>
            </div>
          </div>

          <div class="preview-box" v-if="previewSrc">
            <div class="preview-head">
              <span>Preview</span>
              <span class="file-meta" v-if="fileMeta">{{ fileMeta }}</span>
            </div>
            <img :src="previewSrc" alt="Preview" />
          </div>

          <p v-if="validationError" class="error-text">{{ validationError }}</p>

          <div class="modal-actions">
            <button class="btn-secondary" @click="closeUploadModal">Cancel</button>
            <button class="btn-primary" :disabled="!canUpload || uploading" @click="uploadAsset">
              {{ uploading ? 'Uploading...' : 'Save Asset' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '../api'

const assets = ref([])
const loading = ref(false)
const showUploadModal = ref(false)
const uploading = ref(false)
const searchQuery = ref('')

const sourceMode = ref('file')
const isDragging = ref(false)
const fileInput = ref(null)
const selectedFile = ref(null)
const fileData = ref('')
const formUrl = ref('')
const formLabel = ref('')
const assetType = ref('image')
const validationError = ref('')

const filteredAssets = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return assets.value
  return assets.value.filter(a => (a.label || '').toLowerCase().includes(q))
})

const previewSrc = computed(() => {
  if (sourceMode.value === 'file') return fileData.value
  return formUrl.value.trim()
})

const fileMeta = computed(() => {
  if (!selectedFile.value) return ''
  const sizeKb = Math.max(1, Math.round(selectedFile.value.size / 1024))
  return `${selectedFile.value.name} • ${sizeKb} KB`
})

const canUpload = computed(() => {
  const hasSource = sourceMode.value === 'file' ? !!fileData.value : !!formUrl.value.trim()
  return !!formLabel.value.trim() && hasSource
})

watch([fileData, formUrl, sourceMode], () => {
  if (sourceMode.value === 'file' && fileData.value) {
    assetType.value = inferAssetType(fileData.value)
  }
  if (sourceMode.value === 'url' && formUrl.value.trim()) {
    assetType.value = inferAssetType(formUrl.value.trim())
  }
})

function inferAssetType(value) {
  const v = (value || '').toLowerCase()
  if (v.includes('image/svg+xml') || v.endsWith('.svg')) return 'svg'
  return 'image'
}

async function fetchAssets() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/assets')
    assets.value = data
  } finally {
    loading.value = false
  }
}

function openUploadModal() {
  showUploadModal.value = true
  validationError.value = ''
}

function resetForm() {
  sourceMode.value = 'file'
  selectedFile.value = null
  fileData.value = ''
  formUrl.value = ''
  formLabel.value = ''
  assetType.value = 'image'
  validationError.value = ''
  isDragging.value = false
  if (fileInput.value) fileInput.value.value = ''
}

function closeUploadModal() {
  showUploadModal.value = false
  resetForm()
}

function onDragEnter() {
  isDragging.value = true
}

function onDragOver() {
  isDragging.value = true
}

function onDragLeave(e) {
  if (!e.currentTarget.contains(e.relatedTarget)) {
    isDragging.value = false
  }
}

function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  setFile(file)
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  setFile(file)
}

function setFile(file) {
  sourceMode.value = 'file'
  selectedFile.value = file
  validationError.value = ''

  const isImage = file.type.startsWith('image/') || file.name.toLowerCase().endsWith('.svg')
  if (!isImage) {
    validationError.value = 'Only image files are allowed.'
    return
  }

  const reader = new FileReader()
  reader.onload = (ev) => {
    fileData.value = ev.target?.result || ''
  }
  reader.readAsDataURL(file)
}

async function uploadAsset() {
  validationError.value = ''
  if (!canUpload.value) {
    validationError.value = 'Please add a label and select an image source.'
    return
  }

  uploading.value = true
  try {
    const payloadUrl = sourceMode.value === 'file' ? fileData.value : formUrl.value.trim()
    const { data } = await api.post('/admin/assets', {
      url: payloadUrl,
      label: formLabel.value.trim(),
      asset_type: assetType.value,
    })
    assets.value.unshift(data)
    window.$toast?.('Asset uploaded', 'success')
    closeUploadModal()
  } catch {
    validationError.value = 'Failed to upload asset. Please check the URL/file and try again.'
    window.$toast?.('Failed to upload asset', 'error')
  } finally {
    uploading.value = false
  }
}

async function deleteAsset(id) {
  if (!confirm('Delete this asset?')) return
  try {
    await api.delete(`/admin/assets/${id}`)
    assets.value = assets.value.filter(a => a.id !== id)
    window.$toast?.('Asset deleted', 'success')
  } catch {
    window.$toast?.('Failed to delete asset', 'error')
  }
}

onMounted(fetchAssets)
</script>

<style scoped>
.admin-page {
  padding: 32px 24px;
}

.admin-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.subtext {
  color: var(--text-secondary);
  margin-top: 6px;
}

.admin-actions {
  display: flex;
  gap: 10px;
}

.asset-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  margin-bottom: 18px;
}

.search-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: var(--font-sans);
}

.count-pill {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.06);
  white-space: nowrap;
}

.assets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.asset-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.asset-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent-primary);
}

.thumb {
  height: 150px;
  background: linear-gradient(135deg, #11142a, #1c2242);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
}

.asset-info {
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 0.88rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type {
  font-size: 0.68rem;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.1);
  color: var(--text-secondary);
}

.asset-actions {
  padding: 10px 12px 14px;
}

.btn-small {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.78rem;
}

.btn-small.danger {
  border-color: rgba(255,101,132,0.35);
  color: #ff9bb3;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.66);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5000;
}

.modal-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 20px;
  width: 620px;
  max-width: 94vw;
  max-height: 88vh;
  overflow-y: auto;
}

.modal-head h3 {
  margin: 0 0 6px;
}

.source-tabs {
  margin-top: 14px;
  margin-bottom: 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 4px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.tab-btn {
  border: none;
  background: transparent;
  color: var(--text-muted);
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.tab-btn.active {
  background: var(--accent-primary);
  color: #fff;
}

.source-panel {
  margin-bottom: 14px;
}

.dropzone {
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.18s ease;
}

.dropzone:hover,
.dropzone.dragging {
  border-color: var(--accent-primary);
  background: rgba(108, 99, 255, 0.08);
}

.dz-icon {
  font-size: 1.4rem;
  margin-bottom: 8px;
}

.dz-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.dz-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 180px;
  gap: 10px;
}

.field-label {
  display: block;
  font-size: 0.74rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.input {
  width: 100%;
  padding: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
}

.preview-box {
  margin-top: 14px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px;
  background: rgba(255,255,255,0.02);
}

.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.file-meta {
  color: var(--text-muted);
}

.preview-box img {
  width: 100%;
  max-height: 220px;
  object-fit: contain;
  border-radius: 8px;
  background: #121528;
}

.error-text {
  margin-top: 10px;
  color: #ff809d;
  font-size: 0.82rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.muted {
  color: var(--text-muted);
  font-size: 0.85rem;
}

@media (max-width: 760px) {
  .admin-header {
    flex-direction: column;
  }

  .admin-actions {
    width: 100%;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
