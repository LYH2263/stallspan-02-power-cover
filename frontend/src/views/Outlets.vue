<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

interface Outlet { id: number; segment_id: number; position_m: number; radius_m: number; label: string }
interface Segment { id: number; name: string; width_m: number }

const rows = ref<Outlet[]>([])
const segments = ref<Segment[]>([])
const segmentId = ref(1)
const error = ref('')
const ok = ref('')

const draftPos = ref('')
const draftRadius = ref('')
const draftLabel = ref('')
// edits keyed by outlet id; null fields mean "unchanged"
const edits = ref<Record<number, { position_m: string; radius_m: string }>>({})

const currentSegment = computed(() => segments.value.find(s => s.id === segmentId.value))
const shown = computed(() => rows.value.filter(r => r.segment_id === segmentId.value))

async function load() {
  const [segs, outs] = await Promise.all([api<Segment[]>('/segments'), api<Outlet[]>('/outlets')])
  segments.value = segs
  rows.value = outs
  if (!segs.find(s => s.id === segmentId.value) && segs.length) segmentId.value = segs[0].id
}
onMounted(load)

function flash(msg: string) {
  ok.value = msg
  setTimeout(() => { ok.value = '' }, 2500)
}

async function add() {
  error.value = ''
  const position_m = Number(draftPos.value)
  const radius_m = Number(draftRadius.value)
  try {
    const created = await api<Outlet>('/outlets', {
      method: 'POST',
      body: JSON.stringify({
        segment_id: segmentId.value,
        position_m,
        radius_m,
        label: draftLabel.value || '供电桩',
      }),
    })
    rows.value = [...rows.value, created]
    // clear draft only after the legal write landed
    draftPos.value = ''; draftRadius.value = ''; draftLabel.value = ''
    flash('已新增供电桩')
  } catch (e: any) {
    // invalid write rejected server-side: list and coverage stay on prior legal state
    error.value = message(e)
  }
}

function startEdit(r: Outlet) {
  edits.value[r.id] = { position_m: String(r.position_m), radius_m: String(r.radius_m) }
}

async function saveEdit(r: Outlet) {
  error.value = ''
  const e = edits.value[r.id]
  if (!e) return
  const position_m = Number(e.position_m)
  const radius_m = Number(e.radius_m)
  try {
    const updated = await api<Outlet>(`/outlets/${r.id}`, {
      method: 'PUT',
      body: JSON.stringify({ segment_id: r.segment_id, position_m, radius_m, label: r.label }),
    })
    rows.value = rows.value.map(x => (x.id === r.id ? updated : x))
    delete edits.value[r.id]
    // next run/latest recomputes against the new post; never reuse old coverage
    flash('已保存，下一次现算/确认落库按新桩判定')
  } catch (e2: any) {
    error.value = message(e2)
  }
}

function cancelEdit(r: Outlet) { delete edits.value[r.id]; error.value = '' }

async function remove(r: Outlet) {
  error.value = ''
  const prior = rows.value
  // optimistic removal is reverted if the server rejects so no dirty view remains
  rows.value = rows.value.filter(x => x.id !== r.id)
  try {
    await api(`/outlets/${r.id}`, { method: 'DELETE' })
    delete edits.value[r.id]
    flash('已删除供电桩')
  } catch (e: any) {
    rows.value = prior
    error.value = message(e)
  }
}

function message(e: any) {
  try {
    const parsed = JSON.parse(e.message)
    if (parsed && parsed.detail) return String(parsed.detail)
  } catch { /* raw text below */ }
  return e.message || '写入被拒绝'
}
</script>
<template>
  <h1>供电桩</h1>
  <p class="sub">每桩登记位置米标与服务半径 · 摊位起止闭区间须被单桩服务区完全盖住，只盖中点或一端外露一律拒绝</p>

  <div class="card">
    <label>街段
      <select v-model.number="segmentId">
        <option v-for="s in segments" :key="s.id" :value="s.id">{{ s.name }}（宽 {{ s.width_m }} m）</option>
      </select>
    </label>
  </div>

  <p v-if="error" class="badge badge-bad" style="font-size:0.82rem">{{ error }}</p>
  <p v-if="ok" class="badge badge-ok" style="font-size:0.82rem">{{ ok }}</p>

  <div class="card">
    <table>
      <thead><tr><th>名称</th><th>位置(m)</th><th>服务半径(m)</th><th>覆盖区间(m)</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in shown" :key="r.id">
          <template v-if="edits[r.id]">
            <td>{{ r.label }}</td>
            <td><input v-model="edits[r.id].position_m" type="number" step="0.1" style="width:6rem"></td>
            <td><input v-model="edits[r.id].radius_m" type="number" step="0.1" style="width:6rem"></td>
            <td class="muted">—</td>
            <td>
              <button class="btn" style="padding:0.2rem 0.6rem" @click="saveEdit(r)">保存</button>
              <button class="btn btn-ghost" style="padding:0.2rem 0.6rem" @click="cancelEdit(r)">取消</button>
            </td>
          </template>
          <template v-else>
            <td>{{ r.label }}</td>
            <td>{{ r.position_m }}</td>
            <td>{{ r.radius_m }}</td>
            <td>[{{ Math.max(0, r.position_m - r.radius_m) }}, {{ r.position_m + r.radius_m }}]</td>
            <td>
              <button class="btn" style="padding:0.2rem 0.6rem" @click="startEdit(r)">改</button>
              <button class="btn btn-danger" style="padding:0.2rem 0.6rem" @click="remove(r)">删</button>
            </td>
          </template>
        </tr>
        <tr v-if="!shown.length"><td colspan="5" class="muted">本街段未配置供电桩，行为与绿仓相同（不做供电约束）</td></tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <strong>新增供电桩</strong>
    <div class="outlet-form">
      <label>名称 <input v-model="draftLabel" :placeholder="'供电桩'"></label>
      <label>位置(m) <input v-model="draftPos" type="number" step="0.1" :min="0" :max="currentSegment?.width_m"></label>
      <label>半径(m) <input v-model="draftRadius" type="number" step="0.1"></label>
      <button class="btn" @click="add">登记</button>
    </div>
    <p v-if="currentSegment" class="muted" style="margin-bottom:0">合法范围：0 ≤ 位置 ≤ {{ currentSegment.width_m }}，半径 &gt; 0；越界或半径≤0 的写入一律拒绝。</p>
  </div>
</template>

<style scoped>
.outlet-form { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; margin: 0.6rem 0; }
.outlet-form label { display: flex; flex-direction: column; font-size: 0.78rem; color: var(--ss-muted); gap: 0.2rem; }
input, select {
  background: #fff; border: 1.5px solid var(--ss-curb); border-radius: 3px;
  padding: 0.35rem 0.5rem; font-size: 0.85rem; color: #2c2620;
}
input { width: 7.5rem; }
.btn-ghost { background: transparent; color: #2c2620; box-shadow: none; border: 1.5px solid var(--ss-curb); }
.btn-danger { background: var(--ss-bad); }
</style>
