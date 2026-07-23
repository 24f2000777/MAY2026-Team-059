<script setup>
defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  trend: {
    type: String,
    default: ''
  },
  tone: {
    type: String,
    default: 'accent'
  }
})
</script>

<template>
  <div class="stat-card" :class="tone">
    <div class="stat-top">
      <span class="stat-label">{{ label }}</span>

      <span
        v-if="trend"
        class="stat-trend"
      >
        {{ trend }}
      </span>
    </div>

    <div class="stat-value">
      {{ value }}
    </div>

    <div
      v-if="subtitle"
      class="stat-subtitle"
    >
      {{ subtitle }}
    </div>

    <div class="stat-line"></div>
  </div>
</template>

<style scoped>
.stat-card{
    min-height:145px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    background:#fff;
    width:100%;
    border:1px solid var(--border);
    border-radius:18px;
    padding:22px;
    position:relative;
    overflow:hidden;
    transition:.25s;
    box-shadow:0 8px 22px rgba(0,0,0,.05);
}

.stat-card:hover{
    transform:translateY(-5px);
    box-shadow:0 14px 30px rgba(0,0,0,.08);
}

.stat-top{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:10px;
}

.stat-label{
    font-size:13px;
    text-transform:uppercase;
    letter-spacing:.08em;
    color:var(--text-dim);
    font-weight:700;
}

.stat-value{
    font-size:40px;
    font-weight:900;
    color:var(--text);
    line-height:1;
    margin-bottom:10px;
}

.stat-subtitle{
    color:var(--text-dim);
    font-size:14px;
}

.stat-trend{
    font-size:12px;
    font-weight:700;
}

.stat-line{
    position:absolute;
    left:0;
    bottom:0;
    width:100%;
    height:5px;
}

.accent .stat-line{
    background:#2F8F5B;
}

.ok .stat-line{
    background:#2A9D8F;
}

.warn .stat-line{
    background:#B8860B;
}

.danger .stat-line{
    background:#C0392B;
}

.accent .stat-trend{
    color:#2F8F5B;
}

.ok .stat-trend{
    color:#2A9D8F;
}

.warn .stat-trend{
    color:#B8860B;
}

.danger .stat-trend{
    color:#C0392B;
}
</style>