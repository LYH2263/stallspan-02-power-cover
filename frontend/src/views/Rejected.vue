<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
// 与主图同一次引擎判定：/latest 在供电桩变更后会自动按新桩重算，拒因互斥
onMounted(async () => {
  const data = await api('/allocate/latest?segment_id=1')
  rows.value = data.rejected || []
})
function isPower(reason: string) { return reason && reason.startsWith('供电不足') }
</script>
<template>
  <h1>放不下</h1>
  <p class="sub">拒因互斥：要么供电不足（起止闭区间未被单桩服务区间完全盖住），要么无连续空档/跨柱，不会并成一句</p>
  <div class="card">
    <table>
      <thead><tr><th>摊主</th><th>需求宽度</th><th>原因类别</th><th>原因</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.vendor_id">
          <td>{{ r.vendor_name }}</td>
          <td>{{ r.width_m }}</td>
          <td>
            <span class="badge" :class="isPower(r.reason) ? 'badge-bad' : 'badge-warn'">
              {{ isPower(r.reason) ? '供电不足' : '空档/跨柱' }}
            </span>
          </td>
          <td>{{ r.reason }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">全部放下</p>
  </div>
</template>
