<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const data = ref<any>(null)
const vendors = ref<any[]>([])
async function run() {
  // 现算：始终按最新挡柱与供电桩重算，绝不沿用改桩前的覆盖结果
  data.value = await api('/allocate/run?segment_id=1', { method: 'POST' })
}
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
  // placements 来自与「放不下」同一次引擎判定：能出现在这里的都是覆盖合法摊
  for (const [i, p] of (data.value.placements || []).entries()) {
    out.push({ type: 'stall', start: p.start_m, w: p.width_m, label: p.vendor_name, color: colors[i % colors.length] })
  }
  return out.sort((a,b) => a.start - b.start).map(c => ({ ...c, pct: Math.max((c.w / width) * 100, 2) }))
})
// power coverage intervals clipped to the segment, positioned by percentage
const coverage = computed(() => {
  if (!data.value) return []
  const width = data.value.segment.width_m
  return (data.value.outlets || []).map((o: any) => {
    const lo = Math.max(0, o.position_m - o.radius_m)
    const hi = Math.min(width, o.position_m + o.radius_m)
    return { left: (lo / width) * 100, width: Math.max(((hi - lo) / width) * 100, 0.5), label: o.label || '供电桩', lo, hi }
  })
})
const hasOutlets = computed(() => (data.value?.outlets || []).length > 0)
</script>
<template>
  <div class="ss-street-wrap">
    <h1>街段分配带</h1>
    <p class="sub">沿街一维开间 · 挡柱为竖直阻断 · 绿色为供电服务区，摊位起止闭区间须被单桩完全盖住 · 底部为摊主排队</p>
    <button class="btn" @click="run">重新分配</button>
    <div class="ss-band-ruler" v-if="data">
      <span>0 m</span>
      <span>{{ data.segment.name }} · {{ data.segment.width_m }} m</span>
      <span>{{ data.segment.width_m }} m</span>
    </div>

    <div class="ss-coverage-band" v-if="data && hasOutlets">
      <div
        v-for="(c,i) in coverage" :key="i"
        class="ss-coverage-zone"
        :style="{ left: c.left + '%', width: c.width + '%' }"
        :title="c.label + ' 覆盖 [' + c.lo + ', ' + c.hi + '] m'"
      >⚡ {{ c.label }}</div>
    </div>
    <div class="card ss-coverage-empty" v-if="data && !hasOutlets">
      本街段未配置供电桩，按绿仓处理：无供电约束，只受挡柱与空档限制。
    </div>

    <div class="ss-street-band" v-if="data">
      <div class="ss-street-inner">
        <div
          v-for="(c,i) in cells" :key="i"
          class="ss-band-cell"
          :class="{ 'ss-pillar': c.type === 'pillar' }"
          :style="{ width: c.pct + '%', background: c.type === 'pillar' ? undefined : c.color, flex: '0 0 ' + c.pct + '%' }"
        >{{ c.label }}</div>
      </div>
    </div>
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

<style scoped>
.ss-coverage-band {
  position: relative; height: 34px; margin: 0.5rem 0;
  border: 1.5px dashed rgba(58,122,74,0.65); border-radius: 4px;
  background: rgba(58,122,74,0.06); overflow: hidden;
}
.ss-coverage-zone {
  position: absolute; top: 0; bottom: 0;
  background: rgba(58,122,74,0.28);
  border-left: 2px solid var(--ss-ok, #3a7a4a);
  border-right: 2px solid var(--ss-ok, #3a7a4a);
  font-size: 0.68rem; color: #1f4d2c; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  white-space: nowrap; overflow: hidden;
}
.ss-coverage-empty { font-size: 0.82rem; color: var(--ss-muted); padding: 0.5rem 0.8rem; }
</style>
