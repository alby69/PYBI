<template>
  <div v-if="isSimulating" class="bg-amber-2 border-bottom q-px-md q-py-xs row items-center justify-between text-black">
    <div class="row items-center q-gutter-sm">
      <q-icon name="visibility" color="warning" size="sm" />
      <span class="text-bold">Modalità simulazione "Visualizza come ruolo" attiva:</span>

      <q-select
        v-model="simulatedRoles"
        :options="availableRoleOptions"
        multiple
        dense
        outlined
        bg-color="white"
        label="Ruoli Simulati"
        style="min-width: 200px;"
      />

      <q-input
        v-model="simulatedUsername"
        dense
        outlined
        bg-color="white"
        placeholder="Simula USERNAME()..."
        style="width: 200px;"
      />
    </div>

    <div>
      <q-btn label="Interrompi simulazione" color="negative" size="sm" icon="stop" @click="stopSimulation" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const emit = defineEmits(['simulation-changed']);

const isSimulating = ref(false);
const simulatedRoles = ref([]);
const simulatedUsername = ref('mario.rossi@pybi.org');
const availableRoles = ref([]);

const availableRoleOptions = computed(() =>
  availableRoles.value.map(r => ({ label: r.role_name, value: r.role_id }))
);

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/security/roles');
    if (res.ok) {
      availableRoles.value = await res.json();
    }
  } catch (e) {
    console.error('Failed to load roles for simulation:', e);
  }
});

function startSimulation(rolesList, username = 'mario.rossi@pybi.org') {
  simulatedRoles.value = rolesList;
  simulatedUsername.value = username;
  isSimulating.value = true;
  notifyChange();
}

function stopSimulation() {
  isSimulating.value = false;
  simulatedRoles.value = [];
  notifyChange();
}

function notifyChange() {
  emit('simulation-changed', {
    isSimulating: isSimulating.value,
    roles: simulatedRoles.value,
    username: simulatedUsername.value
  });
}

defineExpose({
  startSimulation,
  stopSimulation
});
</script>

<style scoped>
.border-bottom {
  border-bottom: 2px solid #f57c00;
}
</style>
