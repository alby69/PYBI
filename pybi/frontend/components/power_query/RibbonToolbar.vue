<template>
  <nicegui-PowerQueryRibbon @action="$emit('action', $event)" />
</template>

<script>
export default {
  name: 'RibbonToolbar',
  emits: ['action']
};
</script>
