<script setup>
import { ref, onMounted, computed } from 'vue'
import { EmployeesAPI } from '../api'

const employees = ref([])
const loading = ref(false)
const showInactive = ref(false)
const showModal = ref(false)
const editingId = ref(null)
const savingId = ref(null)

const form = ref({ name: '', hourly_wage: 10030, phone: '', memo: '' })

const avatars = ['🐶', '🐱', '🐹', '🐰', '🐻', '🦊', '🐼', '🐯']
function avatarFor(id) {
  let hash = 0
  for (const ch of String(id)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return avatars[hash % avatars.length]
}

async function load() {
  loading.value = true
  try {
    employees.value = await EmployeesAPI.list(showInactive.value ? undefined : true)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { name: '', hourly_wage: 10030, phone: '', memo: '' }
  showModal.value = true
}

function openEdit(emp) {
  editingId.value = emp.id
  form.value = { name: emp.name, hourly_wage: emp.hourly_wage, phone: emp.phone || '', memo: emp.memo || '' }
  showModal.value = true
}

async function submitForm() {
  if (!form.value.name.trim()) return
  const payload = {
    name: form.value.name.trim(),
    hourly_wage: Number(form.value.hourly_wage),
    phone: form.value.phone.trim() || null,
    memo: form.value.memo.trim() || null,
  }
  if (editingId.value) {
    await EmployeesAPI.update(editingId.value, payload)
  } else {
    await EmployeesAPI.create(payload)
  }
  showModal.value = false
  await load()
}

async function updateWage(emp, value) {
  const wage = Number(value)
  if (!wage || wage === emp.hourly_wage) return
  savingId.value = emp.id
  try {
    await EmployeesAPI.update(emp.id, { hourly_wage: wage })
    emp.hourly_wage = wage
  } finally {
    savingId.value = null
  }
}

async function deactivate(emp) {
  if (!confirm(`${emp.name}님을 비활성화할까요? (기록은 남아있습니다)`)) return
  await EmployeesAPI.remove(emp.id)
  await load()
}

async function reactivate(emp) {
  await EmployeesAPI.update(emp.id, { is_active: true })
  await load()
}

const activeCount = computed(() => employees.value.filter((e) => e.is_active).length)

onMounted(load)
</script>

<template>
  <div>
    <div class="header-row">
      <div>
        <h1 class="title">직원 관리</h1>
        <p class="text-sub">현재 {{ activeCount }}명 근무 중</p>
      </div>
      <button class="btn" @click="openCreate">+ 직원 등록</button>
    </div>

    <label class="toggle-inactive">
      <input type="checkbox" v-model="showInactive" @change="load" />
      비활성 직원도 보기
    </label>

    <div v-if="loading" class="text-sub" style="padding: 20px 0">불러오는 중...</div>

    <div v-else-if="employees.length === 0" class="empty-state card">
      <span class="paw">🐾</span>
      아직 등록된 직원이 없어요.<br />
      "+ 직원 등록" 으로 첫 직원을 추가해보세요.
    </div>

    <div v-else class="emp-grid">
      <div v-for="emp in employees" :key="emp.id" class="card emp-card" :class="{ inactive: !emp.is_active }">
        <div class="emp-top">
          <div class="avatar">{{ avatarFor(emp.id) }}</div>
          <div class="emp-info">
            <div class="emp-name">
              {{ emp.name }}
              <span v-if="!emp.is_active" class="badge-inactive">비활성</span>
            </div>
            <div class="text-sub" v-if="emp.phone">{{ emp.phone }}</div>
          </div>
        </div>

        <div class="wage-row">
          <span class="text-sub">시급</span>
          <div class="wage-input-wrap">
            <input
              class="input wage-input"
              type="number"
              step="10"
              :value="emp.hourly_wage"
              :disabled="!emp.is_active"
              @change="updateWage(emp, $event.target.value)"
            />
            <span class="text-sub">원</span>
          </div>
        </div>

        <p v-if="emp.memo" class="text-sub emp-memo">{{ emp.memo }}</p>

        <div class="emp-actions">
          <button class="btn btn-ghost btn-sm" @click="openEdit(emp)">수정</button>
          <button v-if="emp.is_active" class="btn btn-danger btn-sm" @click="deactivate(emp)">비활성화</button>
          <button v-else class="btn btn-ghost btn-sm" @click="reactivate(emp)">다시 활성화</button>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal-backdrop" @click.self="showModal = false">
      <div class="card modal">
        <h2 class="modal-title">{{ editingId ? '직원 정보 수정' : '새 직원 등록' }}</h2>
        <div class="form-field">
          <label>이름</label>
          <input class="input" v-model="form.name" placeholder="예: 김민지" />
        </div>
        <div class="form-field">
          <label>시급 (원)</label>
          <input class="input" type="number" step="10" v-model="form.hourly_wage" />
        </div>
        <div class="form-field">
          <label>연락처 (선택)</label>
          <input class="input" v-model="form.phone" placeholder="010-0000-0000" />
        </div>
        <div class="form-field">
          <label>메모 (선택)</label>
          <input class="input" v-model="form.memo" placeholder="담당 업무 등" />
        </div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="showModal = false">취소</button>
          <button class="btn" @click="submitForm">저장</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px;
}

.toggle-inactive {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-sub);
  margin-bottom: 16px;
  cursor: pointer;
}

.emp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.emp-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.emp-card.inactive {
  opacity: 0.55;
}

.emp-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.emp-name {
  font-weight: 600;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge-inactive {
  font-size: 11px;
  background: var(--border);
  color: var(--text-sub);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.wage-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.wage-input-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.wage-input {
  width: 110px;
  text-align: right;
  padding: 8px 10px;
}

.emp-memo {
  margin: 0;
}

.emp-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(58, 58, 56, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 100;
}

.modal {
  width: 100%;
  max-width: 400px;
}

.modal-title {
  margin: 0 0 16px;
  font-size: 18px;
}

.form-field {
  margin-bottom: 14px;
}

.form-field label {
  display: block;
  font-size: 13px;
  color: var(--text-sub);
  margin-bottom: 6px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
