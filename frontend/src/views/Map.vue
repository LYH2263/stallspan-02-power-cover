<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const data = ref<any>(null)
const vendors = ref<any[]>([])
async function run() { data.value = await api('/allocate/run?segment_id=1', { method: 'POST' }) }
onMounted(async () => {
  vendors.value = await api('/vendors')
  await run()
})
const colors = ['#e8a87c','#85dcb8','#e27d60','#c38d9e','#41b3a3','#f4a261','#e76f51']
const cells = computed(() => {
  if (!data.value) return []
  const width = data.value.segment.width_m
  const out: any[] = []
  for (const p of data.value.pillars || []) {
    out.push({ type: 'pillar', start: p.position_m - p.thickness_m/2, w: p.thickness_m, label: p.label || '挡柱' })
  }
  // 图上只画引擎判定的合法落位 —— 每个摊的起止区间都已被单桩完全覆盖
  for (const [i, p] of (data.value.placements || []).entries()) {
    out.push({ type: 'stall', start: p.start_m, w: p.width_m, label: p.vendor_name, color: colors[i % colors.length] })
  }
  return out.sort((a,b) => a.start - b.start).map(c => ({ ...c, pct: Math.max((c.w / width) * 100, 2) }))
})
const poles = computed(() => data.value?.power_poles || [])
const segWidth = computed(() => data.value?.segment.width_m || 1)
function poleLeft(p: any) { return (p.position_m / segWidth.value) * 100 + '%' }
function rangeStyle(p: any) {
  const lo = Math.max(0, p.position_m - p.radius_m)
  const hi = Math.min(segWidth.value, p.position_m + p.radius_m)
  return { left: (lo / segWidth.value) * 100 + '%', width: Math.max(((hi - lo) / segWidth.value) * 100, 0.5) + '%' }
}
const rejected = computed(() => data.value?.rejected || [])
const powerRejected = computed(() => rejected.value.filter((r: any) => String(r.reason).includes('供电')))
</script>
<template>
  <div class="ss-street-wrap">
    <h1>街段分配带</h1>
    <p class="sub">沿街一维开间 · 摊位起止区间须被单桩服务区完全盖住 · 底部为摊主排队</p>
    <div style="display:flex;gap:.75rem;align-items:center">
      <button class="btn" @click="run">重新分配</button>
      <RouterLink to="/rejected" class="muted" v-if="rejected.length">
        放不下 {{ rejected.length }} 家<template v-if="powerRejected.length">（供电不足 {{ powerRejected.length }} 家）</template>
      </RouterLink>
    </div>
    <div class="ss-band-ruler" v-if="data">
      <span>0 m</span>
      <span>{{ data.segment.name }} · {{ data.segment.width_m }} m</span>
      <span>{{ data.segment.width_m }} m</span>
    </div>
    <div class="ss-street-band" v-if="data">
      <div class="ss-street-inner">
        <div
          v-for="(c,i) in cells" :key="i"
          class="ss-band-cell"
          :class="{ 'ss-pillar': c.type === 'pillar' }"
          :style="{ width: c.pct + '%', background: c.type === 'pillar' ? undefined : c.color, flex: '0 0 ' + c.pct + '%' }"
        >{{ c.label }}</div>
        <div v-for="(p,i) in poles" :key="'pole'+i" class="ss-pole-marker" :style="{ left: poleLeft(p) }"><i>⚡{{ p.label || '供电桩' }}</i></div>
      </div>
    </div>
    <template v-if="data && poles.length">
      <div class="ss-band-ruler"><span>0 m</span><span>供电覆盖带（单桩服务区间）</span><span>{{ data.segment.width_m }} m</span></div>
      <div class="ss-coverage-strip">
        <div v-for="(p,i) in poles" :key="'cov'+i" class="ss-coverage-range" :style="rangeStyle(p)">{{ p.label || '供电桩' }}</div>
        <div v-for="(p,i) in poles" :key="'tick'+i" class="ss-pole-marker" :style="{ left: poleLeft(p) }"></div>
      </div>
    </template>
    <div class="ss-vendor-queue">
      <div v-for="v in vendors" :key="v.id" class="ss-vendor-chip">
        <strong>{{ v.name }}</strong>
        <span>需 {{ v.stall_width_m }} m · 优先 {{ v.priority }}</span>
      </div>
    </div>
    <div class="card" v-if="data">
      <table>
        <thead><tr><th>摊主</th><th>起点</th><th>终点</th><th>宽度</th></tr></thead>
        <tbody>
          <tr v-for="p in data.placements" :key="p.vendor_id">
            <td>{{ p.vendor_name }}</td><td>{{ p.start_m }}</td><td>{{ p.end_m }}</td><td>{{ p.width_m }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
