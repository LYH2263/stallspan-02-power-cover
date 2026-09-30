<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

interface Pole { id: number; segment_id: number; position_m: number; radius_m: number; label: string }
interface Segment { id: number; name: string; width_m: number }

const segments = ref<Segment[]>([])
const segmentId = ref<number>(1)
const rows = ref<Pole[]>([])
const error = ref('')
const notice = ref('')

const newLabel = ref('供电桩')
const newPos = ref<number | null>(null)
const newRadius = ref<number | null>(null)

const editingId = ref<number | null>(null)
const editLabel = ref('')
const editPos = ref(0)
const editRadius = ref(0)

const segment = computed(() => segments.value.find(s => s.id === segmentId.value))

function errText(e: any): string {
  try {
    const j = JSON.parse(e?.message || '')
    return j.detail || e.message
  } catch { return e?.message || '操作失败' }
}

async function load() {
  error.value = ''
  rows.value = await api(`/power-poles?segment_id=${segmentId.value}`)
}

async function create() {
  error.value = ''; notice.value = ''
  try {
    await api('/power-poles', {
      method: 'POST',
      body: JSON.stringify({
        segment_id: segmentId.value,
        position_m: Number(newPos.value),
        radius_m: Number(newRadius.value),
        label: newLabel.value || '供电桩',
      }),
    })
    newPos.value = null; newRadius.value = null
    notice.value = '已保存。下一次现算/确认落库将按新桩判定覆盖。'
    await load()
  } catch (e) { error.value = errText(e) }
}

function startEdit(p: Pole) {
  editingId.value = p.id
  editLabel.value = p.label
  editPos.value = p.position_m
  editRadius.value = p.radius_m
  error.value = ''; notice.value = ''
}

async function saveEdit() {
  error.value = ''; notice.value = ''
  try {
    await api(`/power-poles/${editingId.value}`, {
      method: 'PUT',
      body: JSON.stringify({
        position_m: Number(editPos.value),
        radius_m: Number(editRadius.value),
        label: editLabel.value || '供电桩',
      }),
    })
    editingId.value = null
    notice.value = '已保存。下一次现算/确认落库将按新桩判定覆盖。'
    await load()
  } catch (e) { error.value = errText(e) }
}

async function remove(id: number) {
  error.value = ''; notice.value = ''
  try {
    await api(`/power-poles/${id}`, { method: 'DELETE' })
    notice.value = '已删除。下一次现算/确认落库将按新桩判定覆盖。'
    await load()
  } catch (e) { error.value = errText(e) }
}

function rangeStyle(p: Pole) {
  const w = segment.value?.width_m || 1
  const lo = Math.max(0, p.position_m - p.radius_m)
  const hi = Math.min(w, p.position_m + p.radius_m)
  return { left: (lo / w) * 100 + '%', width: Math.max(((hi - lo) / w) * 100, 0.5) + '%' }
}

onMounted(async () => {
  segments.value = await api('/segments')
  if (segments.value.length && !segments.value.some(s => s.id === segmentId.value)) {
    segmentId.value = segments.value[0].id
  }
  await load()
})
</script>

<template>
  <h1>供电桩</h1>
  <p class="sub">每桩一个位置米标 + 服务半径 · 摊位起止闭区间须被单桩服务区完全盖住，否则进放不下（供电不足）</p>

  <div class="card" v-if="segments.length > 1" style="display:flex;gap:.5rem;align-items:center">
    <label>街段</label>
    <select v-model.number="segmentId" @change="load">
      <option v-for="s in segments" :key="s.id" :value="s.id">{{ s.name }}（{{ s.width_m }} m）</option>
    </select>
  </div>

  <div v-if="error" class="ss-error">写入被拒绝：{{ error }}。列表与分配结果保持改前合法态。</div>
  <div v-if="notice" class="ss-notice">{{ notice }}</div>

  <div class="card">
    <div class="ss-form">
      <input v-model="newLabel" placeholder="名称" class="ss-label-in" />
      <input v-model.number="newPos" type="number" step="0.1" placeholder="位置(m)" />
      <input v-model.number="newRadius" type="number" step="0.1" placeholder="半径(m)" />
      <button class="btn" @click="create">新增供电桩</button>
      <span class="muted" v-if="segment">半径须 &gt; 0，位置须在 0~{{ segment.width_m }} m 内</span>
    </div>
    <table>
      <thead><tr><th>名称</th><th>位置(m)</th><th>半径(m)</th><th>覆盖区间</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <template v-if="editingId === r.id">
            <td><input v-model="editLabel" class="ss-label-in" /></td>
            <td><input v-model.number="editPos" type="number" step="0.1" /></td>
            <td><input v-model.number="editRadius" type="number" step="0.1" /></td>
            <td>[{{ Math.max(0, editPos - editRadius).toFixed(1) }}, {{ Math.min(segment?.width_m ?? 0, editPos + editRadius).toFixed(1) }}]</td>
            <td>
              <button class="btn btn-small" @click="saveEdit">保存</button>
              <button class="btn btn-small btn-ghost" @click="editingId = null">取消</button>
            </td>
          </template>
          <template v-else>
            <td>{{ r.label }}</td>
            <td>{{ r.position_m }}</td>
            <td>{{ r.radius_m }}</td>
            <td>[{{ Math.max(0, r.position_m - r.radius_m).toFixed(1) }}, {{ Math.min(segment?.width_m ?? 0, r.position_m + r.radius_m).toFixed(1) }}]</td>
            <td>
              <button class="btn btn-small" @click="startEdit(r)">改</button>
              <button class="btn btn-small btn-ghost" @click="remove(r.id)">删</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">未配置供电桩：该街段按绿仓处理，不加供电覆盖限制。</p>
  </div>

  <template v-if="segment && rows.length">
    <div class="ss-band-ruler"><span>0 m</span><span>{{ segment.name }} 供电覆盖带</span><span>{{ segment.width_m }} m</span></div>
    <div class="ss-coverage-strip">
      <div v-for="p in rows" :key="p.id" class="ss-coverage-range" :style="rangeStyle(p)">{{ p.label }}</div>
      <div v-for="p in rows" :key="'m' + p.id" class="ss-pole-marker" :style="{ left: (p.position_m / segment.width_m) * 100 + '%' }"><i>⚡{{ p.position_m }}m</i></div>
    </div>
  </template>
</template>
