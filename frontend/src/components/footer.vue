<template>
  <footer class="app-footer">
    © 2026 NagrikAI • Built for Smart Governance • Developed as part of the IIT Madras BS Degree Software Engineering Project
  </footer>
</template>

<style scoped>
.app-footer{
    position:fixed;
    left:12px;
    right:12px;
    bottom:2px;
    width:auto;
    z-index:1000;

    padding:12px 20px;

    text-align:center;
    font-size:12px;
    font-weight:500;
    color:#fff;

    background:rgba(22,48,31,.68);
    backdrop-filter:blur(18px);
    -webkit-backdrop-filter:blur(18px);

    border:1px solid rgba(255,255,255,.18);
    border-radius:16px;

    box-shadow:
        0 8px 24px rgba(31,107,66,.22),
        inset 0 1px rgba(255, 255, 255, 0.005);
}
</style>