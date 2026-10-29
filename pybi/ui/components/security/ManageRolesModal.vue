<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card style="width: 900px; max-width: 90vw;">
      <q-card-section class="row items-center bg-primary text-white q-py-sm">
        <div class="text-h6">Gestione Ruoli e Sicurezza RLS</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section class="q-pa-none">
        <div class="row style-container" style="height: 500px;">
          <!-- Left Panel: Roles List -->
          <div class="col-4 border-right q-pa-sm bg-grey-1">
            <div class="row items-center justify-between q-mb-sm">
              <span class="text-subtitle2 text-bold">Ruoli</span>
              <q-btn icon="add" label="Nuovo" color="primary" size="sm" dense @click="addRole" />
            </div>
            <q-list separator class="bg-white rounded-borders">
              <q-item
                v-for="role in roles"
                :key="role.role_id"
                clickable
                :active="selectedRoleId === role.role_id"
                active-class="bg-blue-1 text-primary text-bold"
                @click="selectedRoleId = role.role_id"
              >
                <q-item-section>
                  <q-item-label>{{ role.role_name }}</q-item-label>
                  <q-item-label caption>{{ role.description || 'Nessuna descrizione' }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn icon="delete" flat dense round color="negative" size="sm" @click.stop="deleteRole(role.role_id)" />
                </q-item-section>
              </q-item>
            </q-list>
          </div>

          <!-- Center/Right Panel: Tables & DAX/SQL Filter Rule Editor -->
          <div class="col-8 q-pa-md" v-if="selectedRole">
            <div class="q-mb-md">
              <q-input v-model="selectedRole.role_name" label="Nome Ruolo" dense outlined class="q-mb-sm" />
              <q-input v-model="selectedRole.description" label="Descrizione" dense outlined />
            </div>

            <q-separator class="q-my-md" />

            <div class="text-subtitle2 q-mb-xs">Regole di Filtro Tabella (RLS)</div>
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-6">
                <q-select
                  v-model="selectedTable"
                  :options="tables"
                  label="Seleziona Tabella"
                  dense
                  outlined
                  emit-value
                  map-options
                />
              </div>
              <div class="col-6 row items-center justify-end">
                <q-btn label="Aggiungi Regola" color="secondary" size="sm" icon="add" @click="addTableRule" :disabled="!selectedTable" />
              </div>
            </div>

            <!-- Table Filter List & Formula Editor -->
            <q-scroll-area style="height: 240px;">
              <div v-for="(rule, idx) in selectedRole.table_filters" :key="idx" class="q-mb-sm q-pa-sm border-grey rounded-borders">
                <div class="row items-center justify-between q-mb-xs">
                  <span class="text-bold text-secondary">{{ rule.table_name }}</span>
                  <div>
                    <q-toggle v-model="rule.is_active" label="Attivo" dense class="q-mr-sm" />
                    <q-btn icon="delete" flat dense round color="negative" size="sm" @click="removeRule(idx)" />
                  </div>
                </div>
                <q-input
                  v-model="rule.filter_expression"
                  type="textarea"
                  rows="2"
                  label="Espressione DAX / SQL (es. [Region] = 'EMEA' o [SalesPerson] = USERNAME())"
                  dense
                  outlined
                />
              </div>
            </q-scroll-area>
          </div>
        </div>
      </q-card-section>

      <q-separator />

      <q-card-actions align="right" class="q-pa-md">
        <q-btn label="Annulla" flat v-close-popup />
        <q-btn label="Salva Ruoli" color="primary" @click="saveRoles" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const props = defineProps({
  modelValue: Boolean
});

const emit = defineEmits(['update:modelValue', 'saved']);

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const roles = ref([]);
const selectedRoleId = ref(null);
const selectedTable = ref('Sales');
const tables = ref(['Sales', 'Customer', 'Calendar', 'Product', 'Region']);

const selectedRole = computed(() => roles.value.find(r => r.role_id === selectedRoleId.value));

onMounted(async () => {
  await fetchRoles();
});

async function fetchRoles() {
  try {
    const res = await fetch('/api/v1/security/roles');
    if (res.ok) {
      roles.value = await res.json();
      if (roles.value.length > 0 && !selectedRoleId.value) {
        selectedRoleId.value = roles.value[0].role_id;
      }
    }
  } catch (e) {
    console.error('Failed to fetch roles:', e);
  }
}

function addRole() {
  const newId = `role_${Date.now()}`;
  const newRole = {
    role_id: newId,
    role_name: 'Nuovo Ruolo',
    description: '',
    table_filters: []
  };
  roles.value.push(newRole);
  selectedRoleId.value = newId;
}

async function deleteRole(roleId) {
  try {
    await fetch(`/api/v1/security/roles/${roleId}`, { method: 'DELETE' });
    roles.value = roles.value.filter(r => r.role_id !== roleId);
    if (selectedRoleId.value === roleId) {
      selectedRoleId.value = roles.value[0]?.role_id || null;
    }
  } catch (e) {
    console.error('Failed to delete role:', e);
  }
}

function addTableRule() {
  if (!selectedRole.value || !selectedTable.value) return;
  selectedRole.value.table_filters.push({
    table_name: selectedTable.value,
    filter_expression: `[${selectedTable.value}] = USERNAME()`,
    is_active: true
  });
}

function removeRule(index) {
  if (selectedRole.value) {
    selectedRole.value.table_filters.splice(index, 1);
  }
}

async function saveRoles() {
  for (const role of roles.value) {
    await fetch('/api/v1/security/roles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(role)
    });
  }
  emit('saved', roles.value);
  isOpen.value = false;
}
</script>

<style scoped>
.border-right {
  border-right: 1px solid #e0e0e0;
}
.border-grey {
  border: 1px solid #e0e0e0;
}
</style>
