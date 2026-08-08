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
const loading = ref(true)

const now = new Date()
const cursorYear = ref(now.getFullYear())
const cursorMonth = ref(now.getMonth()) // 0-indexed

// records[dateStr][employeeId] = { id, hours, status }
const records = reactive({})

const monthLabel = computed(() => `${cursorYear.value}년 ${cursorMonth.value + 1}월`)
const monthStr = computed(() => `${cursorYear.value}-${pad2(cursorMonth.value + 1)}`)
const todayStr = todayDateStr()

async function loadEmployees() {
  employees.value = await EmployeesAPI.list(true)
}

function blankCell() {
  return { id: null, hours: '', status: 'idle' }
}

function getCell(dateStr, empId) {
  return records[dateStr]?.[empId] || blankCell()
}

async function loadMonth() {
  loading.value = true
  try {
    for (const key of Object.keys(records)) delete records[key]

    const daysInMonth = new Date(cursorYear.value, cursorMonth.value + 1, 0).getDate()
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = toDateStr(cursorYear.value, cursorMonth.value, d)
      const row = {}
      for (const emp of employees.value) row[emp.id] = blankCell()
      records[dateStr] = row
    }

    const list = await AttendanceAPI.list({ month: monthStr.value })
    for (const r of list) {
      if (!records[r.work_date]) continue
      const hours = r.manual_minutes !== null ? r.manual_minutes / 60 : r.worked_minutes / 60
      records[r.work_date][r.employee_id] = { id: r.id, hours, status: 'saved' }
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

async function saveCell(dateStr, empId) {
  const cell = records[dateStr]?.[empId]
  if (!cell) return
  if (cell.hours === '' || cell.hours === null || Number(cell.hours) < 0) {
    if (cell.id) {
      const idToRemove = cell.id
      records[dateStr][empId] = blankCell()
      await AttendanceAPI.remove(idToRemove)
    }
    return
  }
  cell.status = 'saving'
  try {
    const saved = await AttendanceAPI.save({
      employee_id: empId,
      work_date: dateStr,
      manual_minutes: Math.round(Number(cell.hours) * 60),
    })
    cell.id = saved.id
    cell.status = 'saved'
  } catch (e) {
    cell.status = 'error'
  }
}

function markDirty(dateStr, empId) {
  if (records[dateStr]?.[empId]) records[dateStr][empId].status = 'idle'
}

function wageOf(empId) {
  return employees.value.find((e) => e.id === empId)?.hourly_wage || 0
}

function dayTotalPay(dateStr) {
  const row = records[dateStr]
  if (!row) return 0
  return employees.value.reduce(
    (sum, emp) => sum + Math.round((Number(row[emp.id]?.hours) || 0) * emp.hourly_wage),
    0
  )
}

function dayHasHours(dateStr) {
  const row = records[dateStr]
  if (!row) return false
  return Object.values(row).some((c) => Number(c.hours) > 0)
}

const monthlyTotalHours = computed(() => {
  let sum = 0
  for (const row of Object.values(records)) {
    for (const cell of Object.values(row)) sum += Number(cell.hours) || 0
  }
  return sum
})

const monthlyTotalPay = computed(() => {
  let sum = 0
  for (const dateStr of Object.keys(records)) sum += dayTotalPay(dateStr)
  return sum
})

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
        <p class="text-sub">달력의 각 날짜에서 직원 전체의 근무시간을 한 번에 입력하세요.</p>
      </div>
    </div>

    <div v-if="employees.length === 0" class="empty-state card">
      <span class="paw">🐾</span>
      등록된 직원이 없어요. 먼저 "직원" 탭에서 직원을 등록해주세요.
    </div>

    <template v-else>
      <div class="legend">
        <div v-for="emp in employees" :key="emp.id" class="legend-item">
          <span class="legend-avatar">{{ avatarFor(emp.id) }}</span>
          <span class="text-sub">{{ emp.name }}</span>
        </div>
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
          <div class="calendar-scroll">
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
                  filled: dateStr && dayHasHours(dateStr),
                }"
              >
                <template v-if="dateStr">
                  <div class="day-num">{{ Number(dateStr.slice(-2)) }}</div>

                  <div class="day-emp-list">
                    <div v-for="emp in employees" :key="emp.id" class="day-emp-row">
                      <span class="day-emp-avatar">{{ avatarFor(emp.id) }}</span>
                      <span class="day-emp-name">{{ emp.name }}</span>
                      <input
                        class="day-emp-input"
                        type="number"
                        step="0.5"
                        min="0"
                        placeholder="-"
                        v-model="getCell(dateStr, emp.id).hours"
                        @input="markDirty(dateStr, emp.id)"
                        @blur="saveCell(dateStr, emp.id)"
                      />
                      <span
                        v-if="getCell(dateStr, emp.id).status === 'saving'"
                        class="day-emp-status"
                      >···</span>
                      <span
                        v-else-if="getCell(dateStr, emp.id).status === 'error'"
                        class="day-emp-status error"
                      >⚠</span>
                    </div>
                  </div>

                  <div class="day-total" v-if="dayTotalPay(dateStr) > 0">
                    {{ dayTotalPay(dateStr).toLocaleString('ko-KR') }}원
                  </div>
                </template>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div class="card total-bar">
        <div>
          <div class="text-sub">{{ monthLabel }} 전체 직원 합계</div>
          <div class="text-sub">{{ monthlyTotalHours.toFixed(1) }}시간</div>
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

.legend {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 4px;
  margin-bottom: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  flex-shrink: 0;
}

.legend-avatar {
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

.calendar-scroll {
  overflow-x: auto;
}

.weekday-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(148px, 1fr));
  margin-bottom: 6px;
  min-width: 1036px;
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
  grid-template-columns: repeat(7, minmax(148px, 1fr));
  gap: 6px;
  min-width: 1036px;
}

.day-cell {
  position: relative;
  min-height: 100px;
  border-radius: 12px;
  background: var(--bg);
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
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
}

.day-cell.sun .day-num {
  color: #C2694F;
}

.day-cell.sat .day-num {
  color: #5B84C4;
}

.day-emp-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.day-emp-row {
  display: flex;
  align-items: center;
  gap: 3px;
}

.day-emp-avatar {
  font-size: 12px;
  flex-shrink: 0;
}

.day-emp-name {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  color: var(--text-sub);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.day-emp-input {
  width: 30px;
  flex-shrink: 0;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  text-align: right;
  padding: 1px 0;
}

.day-emp-input:focus {
  outline: none;
  background: var(--surface);
  border-radius: 4px;
}

.day-emp-input::-webkit-outer-spin-button,
.day-emp-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.day-emp-status {
  font-size: 9px;
  color: var(--text-sub);
  flex-shrink: 0;
}

.day-emp-status.error {
  color: #C2694F;
}

.day-total {
  margin-top: auto;
  font-size: 10px;
  font-weight: 700;
  color: var(--primary-dark);
  text-align: right;
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
</style>
