<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const apiBase = ref(import.meta.env.VITE_API_BASE_URL || '/api/v1')
const fileInput = ref(null)
const selectedFile = ref(null)
const processedFile = ref(null)
const localPreviewUrl = ref('')
const processedPreviewUrl = ref('')
const maxWidth = ref(4096)
const compressionQuality = ref(86)
const isPreparing = ref(false)
const asset = ref(null)
const selectedPreset = ref('medium')
const isUploading = ref(false)
const isLoadingMetadata = ref(false)
const isDeleting = ref(false)
const message = ref('Sẵn sàng kết nối Image API.')
const error = ref('')
const health = ref('unknown')

const presets = ['thumb', 'small', 'medium', 'large', 'xlarge']

const normalizedApiBase = computed(() => apiBase.value.trim().replace(/\/$/, ''))
const variantUrl = computed(() => {
  if (!asset.value) return ''
  return `${normalizedApiBase.value}/images/${asset.value.id}/${selectedPreset.value}`
})

function clearError() {
  error.value = ''
}

function showError(text) {
  error.value = text
  message.value = ''
}

async function readError(response) {
  try {
    const body = await response.json()
    return body.detail || body.code || `HTTP ${response.status}`
  } catch {
    return `HTTP ${response.status}`
  }
}

function selectFile(event) {
  clearError()
  const [file] = event.target.files
  selectedFile.value = file || null
  if (localPreviewUrl.value) URL.revokeObjectURL(localPreviewUrl.value)
  if (processedPreviewUrl.value) URL.revokeObjectURL(processedPreviewUrl.value)
  localPreviewUrl.value = file ? URL.createObjectURL(file) : ''
  processedPreviewUrl.value = ''
  processedFile.value = null
  if (file) prepareForUpload()
  else message.value = 'Chưa chọn ảnh.'
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 1) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / (1024 ** index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

function outputName(file) {
  const name = file.name.replace(/\.[^.]+$/, '') || 'image'
  return `${name}-canvas.webp`
}

function canvasToWebp(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('Trình duyệt không thể tạo WebP từ Canvas.'))
    }, 'image/webp', quality)
  })
}

async function prepareForUpload() {
  if (!selectedFile.value) return
  const sourceFile = selectedFile.value
  clearError()
  isPreparing.value = true
  message.value = 'Đang resize bằng HTML5 Canvas…'
  try {
    const bitmap = await createImageBitmap(sourceFile, { imageOrientation: 'from-image' })
    const targetWidth = Math.min(bitmap.width, Number(maxWidth.value))
    const targetHeight = Math.max(1, Math.round((bitmap.height * targetWidth) / bitmap.width))
    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const context = canvas.getContext('2d', { alpha: true })
    context.drawImage(bitmap, 0, 0, targetWidth, targetHeight)
    bitmap.close()

    const blob = await canvasToWebp(canvas, Number(compressionQuality.value) / 100)
    // Ignore a stale result when the user picked another file while Canvas ran.
    if (sourceFile !== selectedFile.value) return
    processedFile.value = new File([blob], outputName(sourceFile), { type: 'image/webp' })
    if (processedPreviewUrl.value) URL.revokeObjectURL(processedPreviewUrl.value)
    processedPreviewUrl.value = URL.createObjectURL(processedFile.value)
    message.value = `Canvas hoàn tất: ${targetWidth} × ${targetHeight} px`
  } catch (processingError) {
    processedFile.value = null
    showError(`Không thể resize ảnh: ${processingError.message}`)
  } finally {
    if (sourceFile === selectedFile.value) isPreparing.value = false
  }
}

async function upload() {
  if (!selectedFile.value) {
    showError('Hãy chọn một ảnh JPEG, PNG hoặc WebP trước.')
    return
  }

  clearError()
  isUploading.value = true
  message.value = 'Đang upload ảnh gốc và tạo đủ 5 variants…'
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const response = await fetch(`${normalizedApiBase.value}/images`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) throw new Error(await readError(response))
    asset.value = await response.json()
    selectedPreset.value = 'medium'
    message.value = `Hoàn tất: ${asset.value.id}`
  } catch (requestError) {
    showError(`Upload thất bại: ${requestError.message}`)
  } finally {
    isUploading.value = false
  }
}

async function loadMetadata() {
  if (!asset.value?.id) return
  clearError()
  isLoadingMetadata.value = true
  try {
    const response = await fetch(`${normalizedApiBase.value}/images/${asset.value.id}`)
    if (!response.ok) throw new Error(await readError(response))
    const metadata = await response.json()
    asset.value = { ...asset.value, ...metadata, presets: metadata.available_presets }
    message.value = 'Đã tải metadata mới nhất.'
  } catch (requestError) {
    showError(`Không lấy được metadata: ${requestError.message}`)
  } finally {
    isLoadingMetadata.value = false
  }
}

async function deleteAsset() {
  if (!asset.value?.id || !confirm(`Xóa ${asset.value.id} và toàn bộ variants?`)) return
  clearError()
  isDeleting.value = true
  try {
    const response = await fetch(`${normalizedApiBase.value}/images/${asset.value.id}`, { method: 'DELETE' })
    if (!response.ok) throw new Error(await readError(response))
    message.value = `Đã xóa ${asset.value.id}.`
    asset.value = null
  } catch (requestError) {
    showError(`Xóa thất bại: ${requestError.message}`)
  } finally {
    isDeleting.value = false
  }
}

async function checkHealth() {
  clearError()
  try {
    const response = await fetch('/healthz')
    if (!response.ok) throw new Error(await readError(response))
    health.value = 'online'
    message.value = 'Image API đang hoạt động.'
  } catch (requestError) {
    health.value = 'offline'
    showError('Không kết nối được Image API. Hãy chạy Django ở cổng 8000.')
  }
}

onBeforeUnmount(() => {
  if (localPreviewUrl.value) URL.revokeObjectURL(localPreviewUrl.value)
  if (processedPreviewUrl.value) URL.revokeObjectURL(processedPreviewUrl.value)
})
</script>

<template>
  <main class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Standalone Django + pyvips</p>
        <h1>Image API Lab</h1>
        <p class="subtitle">Upload một ảnh, kiểm tra variants WebP đã pregenerate và xóa asset khi cần.</p>
      </div>
      <button class="health" :class="health" type="button" @click="checkHealth">
        <span></span>{{ health === 'online' ? 'API online' : health === 'offline' ? 'API offline' : 'Kiểm tra API' }}
      </button>
    </header>

    <section class="configuration card">
      <label for="api-base">API base URL</label>
      <input id="api-base" v-model="apiBase" spellcheck="false" />
      <small>Dùng <code>/api/v1</code> khi chạy Vite local; proxy sẽ chuyển tiếp đến Django cổng 8000.</small>
    </section>

    <section class="workspace">
      <article class="card upload-card">
        <div class="section-heading"><p class="step">01</p><h2>Upload ảnh</h2></div>
        <input ref="fileInput" class="file-input" type="file" accept="image/jpeg,image/png,image/webp" @change="selectFile" />
        <div v-if="selectedFile" class="canvas-controls">
          <label>Chiều rộng tối đa <strong>{{ maxWidth }} px</strong><input v-model.number="maxWidth" type="range" min="1280" max="8192" step="128" @change="prepareForUpload" /></label>
          <label>Chất lượng WebP <strong>{{ compressionQuality }}%</strong><input v-model.number="compressionQuality" type="range" min="50" max="100" step="1" @change="prepareForUpload" /></label>
        </div>
        <div class="canvas-comparison">
          <div class="file-preview">
            <img v-if="localPreviewUrl" :src="localPreviewUrl" alt="Ảnh gốc đã chọn" />
            <p v-else>Chọn JPEG, PNG hoặc WebP.<br />Giới hạn mặc định: 100 MB.</p>
            <span v-if="selectedFile" class="size-chip">Gốc: {{ formatBytes(selectedFile.size) }}</span>
          </div>
          <div class="file-preview processed">
            <img v-if="processedPreviewUrl" :src="processedPreviewUrl" alt="Ảnh sau khi resize Canvas" />
            <p v-else>{{ isPreparing ? 'Canvas đang xử lý…' : 'Chờ ảnh sau Canvas' }}</p>
            <span v-if="processedFile" class="size-chip accent">Sau Canvas: {{ formatBytes(processedFile.size) }}</span>
          </div>
        </div>
        <p v-if="selectedFile && processedFile" class="compression-summary">Bản gốc {{ formatBytes(selectedFile.size) }} sẽ được lưu lên Image API; WebP Canvas {{ formatBytes(processedFile.size) }} chỉ dùng để xem trước.</p>
        <button class="primary" type="button" :disabled="isUploading || isPreparing || !selectedFile" @click="upload">
          {{ isUploading ? 'Đang xử lý…' : 'Upload original & pregenerate' }}
        </button>
      </article>

      <article class="card result-card">
        <div class="section-heading"><p class="step">02</p><h2>Asset kết quả</h2></div>
        <template v-if="asset">
          <div class="asset-id"><span>Asset ID</span><code>{{ asset.id }}</code></div>
          <dl>
            <div><dt>Trạng thái</dt><dd class="ready">{{ asset.status }}</dd></div>
            <div><dt>Original</dt><dd>{{ asset.width }} × {{ asset.height }} px</dd></div>
            <div><dt>Variants</dt><dd>{{ asset.presets?.length || 5 }} WebP</dd></div>
          </dl>
          <div class="actions">
            <button type="button" :disabled="isLoadingMetadata" @click="loadMetadata">{{ isLoadingMetadata ? 'Đang tải…' : 'Làm mới metadata' }}</button>
            <button class="danger" type="button" :disabled="isDeleting" @click="deleteAsset">{{ isDeleting ? 'Đang xóa…' : 'Xóa asset' }}</button>
          </div>
        </template>
        <p v-else class="empty">Sau upload, asset ID và metadata sẽ xuất hiện ở đây.</p>
      </article>
    </section>

    <section v-if="asset" class="card variants">
      <div class="section-heading"><p class="step">03</p><h2>Kiểm tra preset</h2></div>
      <div class="preset-buttons">
        <button v-for="preset in presets" :key="preset" type="button" :class="{ active: selectedPreset === preset }" @click="selectedPreset = preset">{{ preset }}</button>
      </div>
      <div class="variant-preview">
        <img :src="variantUrl" :alt="`${selectedPreset} variant`" />
        <div>
          <p class="label">URL đang dùng</p>
          <code>{{ variantUrl }}</code>
          <a :href="variantUrl" target="_blank" rel="noreferrer">Mở file WebP ↗</a>
        </div>
      </div>
    </section>

    <p v-if="message" class="notice success">{{ message }}</p>
    <p v-if="error" class="notice error">{{ error }}</p>
  </main>
</template>
