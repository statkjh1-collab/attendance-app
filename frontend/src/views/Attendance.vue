<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { EmployeesAPI, AttendanceAPI } from '../api'

const avatars = ['🐶', '🐱', '🐹', '🐰', '🐻', '🦊', '🐼', '🐯']
function avatarFor(id) {
  let hash = 0
  for (const ch of String(id)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return avatars[hash % avatars.length]
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

function pad2(n) {
  return String(n).padStart(2, '0')
}

function toDateStr(y, m, d) {
  return `${y}-${pad2(m + 1)}-${pad2(d)}`
}

function todayDateStr() {
  const d = new Date()
  return toDateStr(d.getFullYear(), d.getMonth(), d.getDate())
}

const employees = ref([])
const selectedId = ref(null)
const loading = ref(false)

const now = new Date()
const cursorYear = ref(now.getFullYear())
const cursorMonth = ref(now.getMonth()) // 0-indexed

const dayData = reactive({}) // 'YYYY-MM-DD' -> { id, hours, status }

const selectedEmployee = computed(() => employees.value.find((e) => e.id === selectedId.value))
const monthLabel = computed(() => `${cursorYear.value}년 ${cursorMonth.value + 1}월`)
const monthStr = computed(() => `${cursorYear.value}-${pad2(cursorMonth.value + 1)}`)
const todayStr = todayDateStr()

async function loadEmployees() {
  employees.value = await EmployeesAPI.list(true)
  if (!selectedId.value && employees.value.length) {
    selectedId.value = employees.value[0].id
  }
}

function resetDayData() {
  for (const key of Object.keys(dayData)) delete dayData[key]
}

function getDay(dateStr) {
  return dayData[dateStr] || { id: null, hours: '', status: 'idle' }
}

async function loadMonth() {
  resetDayData()
  if (!selectedId.value) return
  loading.value = true
  try {
    const daysInMonth = new Date(cursorYear.value, cursorMonth.value + 1, 0).getDate()
    for (let d = 1; d <= daysInMonth; d++) {
      dayData[toDateStr(cursorYear.value, cursorMonth.value, d)] = { id: null, hours: '', status: 'idle' }
    }
    const records = await AttendanceAPI.list({ employee_id: selectedId.value, month: monthStr.value })
    for (const r of records) {
      const hours = r.manual_minutes !== null ? r.manual_minutes / 60 : r.worked_minutes / 60
      dayData[r.work_date] = { id: r.id, hours, status: 'saved' }
    }
  } finally {
    loading.value = false
  }
}

function prevMonth() {
  if (cursorMonth.value === 0) {
    cursorMonth.value = 11
    cursorYear.value -= 1
  } else {
    cursorMonth.value -= 1
  }
}

function nextMonth() {
  if (cursorMonth.value === 11) {
    cursorMonth.value = 0
    cursorYear.value += 1
  } else {
    cursorMonth.value += 1
  }
}

function goToday() {
  cursorYear.value = now.getFullYear()
  cursorMonth.value = now.getMonth()
}

const calendarCells = computed(() => {
  const firstDay = new Date(cursorYear.value, cursorMonth.value, 1)
  const startOffset = firstDay.getDay()
  const daysInMonth = new Date(cursorYear.value, cursorMonth.value + 1, 0).getDate()
  const cells = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push(toDateStr(cursorYear.value, cursorMonth.value, d))
  }
  return cells
})

async function saveDay(dateStr) {
  const day = getDay(dateStr)
  if (day.hours === '' || day.hours === null || Number(day.hours) < 0) {
    if (day.id) {
      const idToRemove = day.id
      dayData[dateStr] = { id: null, hours: '', status: 'idle' }
      await AttendanceAPI.remove(idToRemove)
    }
    return
  }
  day.status = 'saving'
  try {
    const saved = await AttendanceAPI.save({
      employee_id: selectedId.value,
      work_date: dateStr,
      manual_minutes: Math.round(Number(day.hours) * 60),
    })
    day.id = saved.id
    day.status = 'saved'
  } catch (e) {
    day.status = 'error'
  }
}

function markDirty(dateStr) {
  getDay(dateStr).status = 'idle'
}

function payFor(dateStr) {
  const day = dayData[dateStr]
  if (!day || !day.hours || !selectedEmployee.value) return 0
  return Math.round(Number(day.hours) * selectedEmployee.value.hourly_wage)
}

const monthlyTotalHours = computed(() =>
  Object.values(dayData).reduce((sum, d) => sum + (Number(d.hours) || 0), 0)
)
const monthlyWorkDays = computed(
  () => Object.values(dayData).filter((d) => Number(d.hours) > 0).length
)
const monthlyTotalPay = computed(() =>
  Math.round(monthlyTotalHours.value * (selectedEmployee.value?.hourly_wage || 0))
)

watch(selectedId, loadMonth)
watch([cursorYear, cursorMonth], loadMonth)

onMounted(async () => {
  await loadEmployees()
  await loadMonth()
})
</script>

<template>
  <div>
    <div class="header-row">
      <div>
        <h1 class="title">출퇴근 입력</h1>
        <p class="text-sub">선생님을 선택하고 날짜별로 근무시간만 입력하세요.</p>
      </div>
    </div>

    <div v-if="employees.length === 0" class="empty-state card">
      <span class="paw">🐾</span>
      등록된 직원이 없어요. 먼저 "직원" 탭에서 직원을 등록해주세요.
    </div>

    <template v-else>
      <div class="emp-picker">
        <button
          v-for="emp in employees"
          :key="emp.id"
          class="emp-chip"
          :class="{ active: selectedId === emp.id }"
          @click="selectedId = emp.id"
        >
          <span class="emp-chip-avatar">{{ avatarFor(emp.id) }}</span>
          <span>{{ emp.name }}</span>
        </button>
      </div>

      <div class="card month-card">
        <div class="month-nav">
          <button class="btn btn-ghost btn-sm" @click="prevMonth">‹ 이전달</button>
          <div class="month-nav-center">
            <span class="month-label">{{ monthLabel }}</span>
            <button class="btn btn-ghost btn-sm" @click="goToday">오늘</button>
          </div>
          <button class="btn btn-ghost btn-sm" @click="nextMonth">다음달 ›</button>
        </div>

        <div v-if="loading" class="text-sub" style="padding: 20px 0; text-align: center">
          불러오는 중...
        </div>

        <template v-else>
          <div class="weekday-row">
            <div
              v-for="(w, i) in WEEKDAYS"
              :key="w"
              class="weekday"
              :class="{ sun: i === 0, sat: i === 6 }"
            >
              {{ w }}
            </div>
          </div>

          <div class="calendar-grid">
            <div
              v-for="(dateStr, idx) in calendarCells"
              :key="idx"
              class="day-cell"
              :class="{
                empty: !dateStr,
                today: dateStr === todayStr,
                sun: dateStr && new Date(dateStr).getDay() === 0,
                sat: dateStr && new Date(dateStr).getDay() === 6,
                filled: dateStr && Number(getDay(dateStr).hours) > 0,
              }"
            >
              <template v-if="dateStr">
                <div class="day-num">{{ Number(dateStr.slice(-2)) }}</div>
                <input
                  class="day-input"
                  type="number"
                  step="0.5"
                  min="0"
                  placeholder="-"
                  v-model="getDay(dateStr).hours"
                  @input="markDirty(dateStr)"
                  @blur="saveDay(dateStr)"
                />
                <div class="day-pay" v-if="Number(getDay(dateStr).hours) > 0">
                  {{ payFor(dateStr).toLocaleString('ko-KR') }}
                </div>
                <div
                  class="day-status"
                  v-if="getDay(dateStr).status === 'saving'"
                >
                  ···
                </div>
                <div
                  class="day-status error"
                  v-else-if="getDay(dateStr).status === 'error'"
                >
                  ⚠
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <div class="card total-bar">
        <div>
          <div class="text-sub">{{ selectedEmployee?.name }} · {{ monthLabel }}</div>
          <div class="text-sub">근무 {{ monthlyWorkDays }}일 · {{ monthlyTotalHours.toFixed(1) }}시간</div>
        </div>
        <div class="amount total-amount">{{ monthlyTotalPay.toLocaleString('ko-KR') }}원</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.header-row {
  margin-bottom: 16px;
}

.title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px;
}

.emp-picker {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  margin-bottom: 16px;
}

.emp-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-sub);
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  flex-shrink: 0;
}

.emp-chip.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.emp-chip-avatar {
  font-size: 16px;
}

.month-card {
  margin-bottom: 14px;
}

.month-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.month-nav-center {
  display: flex;
  align-items: center;
  gap: 10px;
}

.month-label {
  font-weight: 700;
  font-size: 16px;
}

.weekday-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: 6px;
}

.weekday {
  text-align: center;
  font-size: 12px;
  color: var(--text-sub);
  font-weight: 600;
  padding-bottom: 6px;
}

.weekday.sun {
  color: #C2694F;
}

.weekday.sat {
  color: #5B84C4;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
}

.day-cell {
  position: relative;
  aspect-ratio: 1 / 1;
  min-height: 64px;
  border-radius: 12px;
  background: var(--bg);
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 4px 2px;
}

.day-cell.empty {
  background: transparent;
}

.day-cell.today {
  border-color: var(--primary);
}

.day-cell.filled {
  background: #EAF2ED;
}

.day-num {
  font-size: 11px;
  color: var(--text-sub);
  position: absolute;
  top: 6px;
  left: 8px;
}

.day-cell.sun .day-num {
  color: #C2694F;
}

.day-cell.sat .day-num {
  color: #5B84C4;
}

.day-input {
  width: 80%;
  border: none;
  background: transparent;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  padding: 0;
  margin-top: 6px;
}

.day-input:focus {
  outline: none;
}

.day-input::-webkit-outer-spin-button,
.day-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.day-pay {
  font-size: 10px;
  color: var(--primary-dark);
  font-weight: 600;
}

.day-status {
  position: absolute;
  top: 4px;
  right: 6px;
  font-size: 10px;
  color: var(--text-sub);
}

.day-status.error {
  color: #C2694F;
}

.total-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  bottom: 16px;
}

.total-amount {
  font-size: 20px;
}

@media (max-width: 560px) {
  .day-cell {
    min-height: 52px;
    border-radius: 10px;
  }
  .day-input {
    font-size: 14px;
  }
  .day-pay {
    display: none;
  }
}
</style>
