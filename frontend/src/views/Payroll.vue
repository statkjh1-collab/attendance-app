<script setup>
import { ref, onMounted, watch, computed, nextTick } from 'vue'
import { PayrollAPI, AttendanceAPI } from '../api'
import Chart from 'chart.js/auto'

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const month = ref(currentMonth())
const summary = ref([])
const loading = ref(false)
const expandedId = ref(null)
const details = ref([])
const detailsLoading = ref(false)

const chartCanvas = ref(null)
let chartInstance = null

const avatars = ['🐶', '🐱', '🐹', '🐰', '🐻', '🦊', '🐼', '🐯']
function avatarFor(id) {
  let hash = 0
  for (const ch of String(id)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return avatars[hash % avatars.length]
}

const TAX_RATE = 0.033 // 3.3% 사업소득 원천징수 (소득세 3% + 지방소득세 0.3%)
function taxOf(gross) {
  return Math.floor(gross * TAX_RATE)
}
function netOf(gross) {
  return gross - taxOf(gross)
}

async function load() {
  loading.value = true
  expandedId.value = null
  try {
    summary.value = await PayrollAPI.get(month.value)
  } finally {
    loading.value = false
  }
  await nextTick()
  renderChart()
}

function renderChart() {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  if (!chartCanvas.value || summary.value.length === 0) return

  chartInstance = new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels: summary.value.map((s) => s.employee_name),
      datasets: [
        {
          label: '실지급액 (원)',
          data: summary.value.map((s) => netOf(s.total_pay)),
          backgroundColor: '#7BA88C',
          borderRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const row = summary.value[ctx.dataIndex]
              return [
                `세전 급여: ${row.total_pay.toLocaleString('ko-KR')}원`,
                `3.3% 공제: -${taxOf(row.total_pay).toLocaleString('ko-KR')}원`,
                `실지급액: ${netOf(row.total_pay).toLocaleString('ko-KR')}원`,
              ]
            },
          },
        },
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => Number(v).toLocaleString('ko-KR'),
          },
        },
      },
    },
  })
}

async function toggleDetail(row) {
  if (expandedId.value === row.employee_id) {
    expandedId.value = null
    return
  }
  expandedId.value = row.employee_id
  detailsLoading.value = true
  try {
    details.value = await AttendanceAPI.list({ employee_id: row.employee_id, month: month.value })
  } finally {
    detailsLoading.value = false
  }
}

function formatHm(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const totalPay = computed(() => summary.value.reduce((sum, s) => sum + s.total_pay, 0))
const totalDays = computed(() => summary.value.reduce((sum, s) => sum + s.work_days, 0))
const totalTax = computed(() => summary.value.reduce((sum, s) => sum + taxOf(s.total_pay), 0))
const totalNet = computed(() => summary.value.reduce((sum, s) => sum + netOf(s.total_pay), 0))

watch(month, load)
onMounted(load)
</script>

<template>
  <div>
    <div class="header-row">
      <div>
        <h1 class="title">월급 정산</h1>
        <p class="text-sub">월을 선택하면 직원별 근무 내역과 급여가 계산됩니다.</p>
      </div>
      <input class="input month-input" type="month" v-model="month" />
    </div>

    <div v-if="loading" class="text-sub" style="padding: 20px 0">불러오는 중...</div>

    <div v-else-if="summary.length === 0" class="empty-state card">
      <span class="paw">🦴</span>
      {{ month }}에는 아직 출퇴근 기록이 없어요.
    </div>

    <template v-else>
      <div class="card total-card">
        <div class="total-main">
          <div class="text-sub">실지급 총액 (3.3% 공제 후)</div>
          <div class="amount total-amount">{{ totalNet.toLocaleString('ko-KR') }}원</div>
        </div>
        <div class="total-breakdown">
          <div class="total-breakdown-row">
            <span class="text-sub">세전 총 급여</span>
            <span>{{ totalPay.toLocaleString('ko-KR') }}원</span>
          </div>
          <div class="total-breakdown-row">
            <span class="text-sub">3.3% 공제액</span>
            <span>-{{ totalTax.toLocaleString('ko-KR') }}원</span>
          </div>
          <div class="total-breakdown-row">
            <span class="text-sub">근무일 합계</span>
            <span>{{ totalDays }}일</span>
          </div>
        </div>
      </div>

      <div class="card chart-card">
        <div class="chart-wrap">
          <canvas ref="chartCanvas"></canvas>
        </div>
      </div>

      <div class="list">
        <div v-for="row in summary" :key="row.employee_id" class="card emp-row">
          <div class="emp-row-top" @click="toggleDetail(row)">
            <div class="avatar">{{ avatarFor(row.employee_id) }}</div>
            <div class="emp-row-info">
              <div class="emp-row-name">{{ row.employee_name }}</div>
              <div class="text-sub">
                근무 {{ row.work_days }}일 · {{ row.total_hours }}시간 · 시급 {{ row.hourly_wage.toLocaleString('ko-KR') }}원
              </div>
            </div>
            <div class="emp-row-pay">
              <div class="emp-row-pay-main">
                <span class="amount">{{ netOf(row.total_pay).toLocaleString('ko-KR') }}원</span>
                <span class="text-sub emp-row-pay-sub">
                  세전 {{ row.total_pay.toLocaleString('ko-KR') }}원 · 3.3% 공제 -{{ taxOf(row.total_pay).toLocaleString('ko-KR') }}원
                </span>
              </div>
              <span class="chevron">{{ expandedId === row.employee_id ? '▲' : '▼' }}</span>
            </div>
          </div>

          <div v-if="expandedId === row.employee_id" class="detail-panel">
            <div v-if="detailsLoading" class="text-sub">불러오는 중...</div>
            <table v-else class="detail-table">
              <thead>
                <tr>
                  <th>날짜</th>
                  <th>출근</th>
                  <th>퇴근</th>
                  <th>근무시간</th>
                  <th>급여</th>
                  <th>3.3% 공제</th>
                  <th>실지급액</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in details" :key="d.id">
                  <td>{{ d.work_date }}</td>
                  <td>{{ d.check_in ? formatHm(d.check_in) : '-' }}</td>
                  <td>{{ d.check_out ? formatHm(d.check_out) : '-' }}</td>
                  <td>{{ (d.worked_minutes / 60).toFixed(1) }}시간</td>
                  <td>{{ d.pay.toLocaleString('ko-KR') }}원</td>
                  <td>-{{ taxOf(d.pay).toLocaleString('ko-KR') }}원</td>
                  <td class="amount">{{ netOf(d.pay).toLocaleString('ko-KR') }}원</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px;
}

.month-input {
  width: auto;
  min-width: 160px;
  font-weight: 600;
}

.total-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 14px;
}

.total-amount {
  font-size: 26px;
}

.total-breakdown {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}

.total-breakdown-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.chart-card {
  margin-bottom: 14px;
}

.chart-wrap {
  position: relative;
  width: 100%;
  height: 220px;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.emp-row {
  padding: 0;
  overflow: hidden;
}

.emp-row-top {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  cursor: pointer;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.emp-row-info {
  flex: 1;
}

.emp-row-name {
  font-weight: 600;
  font-size: 15px;
}

.emp-row-pay {
  display: flex;
  align-items: center;
  gap: 10px;
}

.emp-row-pay-main {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.emp-row-pay-sub {
  font-size: 11px;
}

.chevron {
  color: var(--text-sub);
  font-size: 11px;
}

.detail-panel {
  border-top: 1px solid var(--border);
  padding: 14px 20px 18px;
  background: var(--bg);
  overflow-x: auto;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.detail-table th {
  text-align: left;
  color: var(--text-sub);
  font-weight: 500;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}

.detail-table td {
  padding: 8px;
  border-bottom: 1px solid var(--border);
}
</style>
