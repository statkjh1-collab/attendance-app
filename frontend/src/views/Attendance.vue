<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { EmployeesAPI, AttendanceAPI } from '../api'

function todayStr() {
  const d = new Date()
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - tz).toISOString().slice(0, 10)
}

function isoToHm(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

const selectedDate = ref(todayStr())
const employees = ref([])
const rows = reactive({}) // employee_id -> row state
const loading = ref(false)

const avatars = ['🐶', '🐱', '🐹', '🐰', '🐻', '🦊', '🐼', '🐯']
function avatarFor(id) {
  let hash = 0
  for (const ch of String(id)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return avatars[hash % avatars.length]
}

function blankRow(emp) {
  return {
    id: null,
    mode: 'manual', // 'manual' | 'time'
    hours: '',
    check_in: '',
    check_out: '',
    break_minutes: 0,
    memo: '',
    hourly_wage: emp.hourly_wage,
    status: 'idle', // idle | saving | saved | error
  }
}

async function loadEmployees() {
  employees.value = await EmployeesAPI.list(true)
  for (const emp of employees.value) {
    if (!rows[emp.id]) rows[emp.id] = blankRow(emp)
  }
}

async function loadAttendanceForDate() {
  loading.value = true
  try {
    const records = await AttendanceAPI.list({ work_date: selectedDate.value })
    for (const emp of employees.value) {
      const rec = records.find((r) => r.employee_id === emp.id)
      if (rec) {
        rows[emp.id] = {
          id: rec.id,
          mode: rec.manual_minutes !== null ? 'manual' : 'time',
          hours: rec.manual_minutes !== null ? rec.manual_minutes / 60 : '',
          check_in: isoToHm(rec.check_in),
          check_out: isoToHm(rec.check_out),
          break_minutes: rec.break_minutes || 0,
          memo: rec.memo || '',
          hourly_wage: emp.hourly_wage,
          status: 'saved',
        }
      } else {
        rows[emp.id] = blankRow(emp)
      }
    }
  } finally {
    loading.value = false
  }
}

function estimatedPay(row) {
  if (row.mode === 'manual') {
    const h = Number(row.hours)
    if (!h) return 0
    return Math.round((h * 60) / 60 * row.hourly_wage)
  }
  if (row.check_in && row.check_out) {
    const [ih, im] = row.check_in.split(':').map(Number)
    const [oh, om] = row.check_out.split(':').map(Number)
    let mins = oh * 60 + om - (ih * 60 + im)
    if (mins < 0) mins += 24 * 60
    mins -= Number(row.break_minutes) || 0
    if (mins < 0) mins = 0
    return Math.round((mins / 60) * row.hourly_wage)
  }
  return 0
}

async function saveRow(empId) {
  const row = rows[empId]
  const hasManual = row.mode === 'manual' && row.hours !== '' && Number(row.hours) >= 0
  const hasTime = row.mode === 'time' && row.check_in && row.check_out
  if (!hasManual && !hasTime) return

  row.status = 'saving'
  try {
    const payload = {
      employee_id: empId,
      work_date: selectedDate.value,
      break_minutes: Number(row.break_minutes) || 0,
      memo: row.memo || null,
    }
    if (row.mode === 'manual') {
      payload.manual_minutes = Math.round(Number(row.hours) * 60)
    } else {
      payload.check_in = row.check_in
      payload.check_out = row.check_out
    }
    const saved = await AttendanceAPI.save(payload)
    row.id = saved.id
    row.status = 'saved'
  } catch (e) {
    row.status = 'error'
  }
}

function markDirty(row) {
  row.status = 'idle'
}

async function clearRow(empId) {
  const row = rows[empId]
  if (!row.id) {
    rows[empId] = blankRow({ id: empId, hourly_wage: row.hourly_wage })
    return
  }
  if (!confirm('이 날짜의 기록을 삭제할까요?')) return
  await AttendanceAPI.remove(row.id)
  rows[empId] = blankRow({ id: empId, hourly_wage: row.hourly_wage })
}

const totalPayToday = computed(() =>
  employees.value.reduce((sum, emp) => sum + estimatedPay(rows[emp.id] || blankRow(emp)), 0)
)

watch(selectedDate, loadAttendanceForDate)

onMounted(async () => {
  await loadEmployees()
  await loadAttendanceForDate()
})
</script>

<template>
  <div>
    <div class="header-row">
      <div>
        <h1 class="title">출퇴근 입력</h1>
        <p class="text-sub">날짜를 선택하고 직원별 근무시간을 입력하세요.</p>
      </div>
      <input class="input date-input" type="date" v-model="selectedDate" />
    </div>

    <div v-if="loading" class="text-sub" style="padding: 20px 0">불러오는 중...</div>

    <div v-else-if="employees.length === 0" class="empty-state card">
      <span class="paw">🐾</span>
      등록된 직원이 없어요. 먼저 "직원" 탭에서 직원을 등록해주세요.
    </div>

    <div v-else class="rows">
      <div v-for="emp in employees" :key="emp.id" class="card row-card">
        <div class="row-top">
          <div class="avatar">{{ avatarFor(emp.id) }}</div>
          <div class="row-name">{{ emp.name }}</div>

          <div class="mode-toggle">
            <button
              class="mode-btn"
              :class="{ active: rows[emp.id].mode === 'manual' }"
              @click="rows[emp.id].mode = 'manual'; markDirty(rows[emp.id])"
            >
              시간 입력
            </button>
            <button
              class="mode-btn"
              :class="{ active: rows[emp.id].mode === 'time' }"
              @click="rows[emp.id].mode = 'time'; markDirty(rows[emp.id])"
            >
              출퇴근 시각
            </button>
          </div>
        </div>

        <div class="row-body">
          <template v-if="rows[emp.id].mode === 'manual'">
            <div class="field-group">
              <label class="text-sub">근무시간</label>
              <div class="hour-input-wrap">
                <input
                  class="input hour-input"
                  type="number"
                  step="0.5"
                  min="0"
                  placeholder="8"
                  v-model="rows[emp.id].hours"
                  @input="markDirty(rows[emp.id])"
                  @blur="saveRow(emp.id)"
                />
                <span class="text-sub">시간</span>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="field-group">
              <label class="text-sub">출근</label>
              <input
                class="input time-input"
                type="time"
                v-model="rows[emp.id].check_in"
                @change="markDirty(rows[emp.id]); saveRow(emp.id)"
              />
            </div>
            <div class="field-group">
              <label class="text-sub">퇴근</label>
              <input
                class="input time-input"
                type="time"
                v-model="rows[emp.id].check_out"
                @change="markDirty(rows[emp.id]); saveRow(emp.id)"
              />
            </div>
            <div class="field-group">
              <label class="text-sub">휴게(분)</label>
              <input
                class="input break-input"
                type="number"
                min="0"
                step="5"
                v-model="rows[emp.id].break_minutes"
                @change="markDirty(rows[emp.id]); saveRow(emp.id)"
              />
            </div>
          </template>

          <div class="field-group memo-group">
            <label class="text-sub">메모</label>
            <input
              class="input"
              type="text"
              placeholder="선택"
              v-model="rows[emp.id].memo"
              @change="markDirty(rows[emp.id]); saveRow(emp.id)"
            />
          </div>
        </div>

        <div class="row-footer">
          <div class="pay-preview">
            예상 급여 <span class="amount">{{ estimatedPay(rows[emp.id]).toLocaleString('ko-KR') }}원</span>
          </div>
          <div class="row-actions">
            <span v-if="rows[emp.id].status === 'saving'" class="status saving">저장 중...</span>
            <span v-else-if="rows[emp.id].status === 'saved'" class="status saved">✓ 저장됨</span>
            <span v-else-if="rows[emp.id].status === 'error'" class="status error">저장 실패</span>
            <button class="btn btn-sm" @click="saveRow(emp.id)">저장</button>
            <button class="btn btn-ghost btn-sm" @click="clearRow(emp.id)">지우기</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="employees.length" class="total-bar card">
      <span>{{ selectedDate }} 총 인건비</span>
      <span class="amount total-amount">{{ totalPayToday.toLocaleString('ko-KR') }}원</span>
    </div>
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

.date-input {
  width: auto;
  min-width: 170px;
  font-weight: 600;
}

.rows {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.row-top {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
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

.row-name {
  font-weight: 600;
  font-size: 16px;
  flex: 1;
}

.mode-toggle {
  display: flex;
  background: var(--bg);
  border-radius: var(--radius);
  padding: 3px;
  gap: 2px;
}

.mode-btn {
  background: transparent;
  padding: 7px 12px;
  border-radius: calc(var(--radius) - 4px);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-sub);
}

.mode-btn.active {
  background: var(--primary);
  color: #fff;
}

.row-body {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-group label {
  font-size: 12px;
}

.hour-input-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.hour-input {
  width: 90px;
}

.time-input {
  width: 130px;
}

.break-input {
  width: 90px;
}

.memo-group {
  flex: 1;
  min-width: 140px;
}

.row-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

.pay-preview {
  font-size: 14px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status {
  font-size: 12px;
}

.status.saved {
  color: var(--primary-dark);
}

.status.error {
  color: #C2694F;
}

.total-bar {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  position: sticky;
  bottom: 16px;
}

.total-amount {
  font-size: 18px;
}
</style>
