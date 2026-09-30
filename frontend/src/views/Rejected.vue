<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
onMounted(async () => {
  // 与主图同一套覆盖判定：每次都现算，改桩后不会沿用旧结果
  const data = await api('/allocate/run?segment_id=1', { method: 'POST' })
  rows.value = data.rejected || []
})
function badgeClass(reason: string) {
  return String(reason).includes('供电') ? 'badge badge-bad' : 'badge badge-warn'
}
</script>
<template>
  <h1>放不下</h1>
  <p class="sub">拒因互斥：空档不够（不跨越挡柱）或供电不足（起止区间未被任一供电桩完全覆盖）</p>
  <div class="card">
    <table>
      <thead><tr><th>摊主</th><th>需求宽度</th><th>原因</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.vendor_id">
          <td>{{ r.vendor_name }}</td><td>{{ r.width_m }}</td>
          <td><span :class="badgeClass(r.reason)">{{ r.reason }}</span></td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">全部放下</p>
  </div>
</template>
