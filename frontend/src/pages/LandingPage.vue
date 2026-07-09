<script setup>
import { ref, computed } from 'vue'

const menuOpen = ref(false)
const showChatbot = ref(true)
const heroHeadline = ref('Your complaint, heard and actually resolved.')
const statsResolved = ref((24800).toLocaleString('en-IN') + '+')

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

const mobileNavClass = computed(() => (menuOpen.value ? 'mobile-nav open' : 'mobile-nav'))
</script>

<template>
<div class="landing-page">

<!-- NAVBAR -->
<nav style="position: sticky; top: 0; z-index: 100; background: #1A1A1A; border-bottom: 1px solid rgba(255,255,255,.06);">
  <div class="w" style="display: flex; align-items: center; justify-content: space-between; height: 64px;">

    <!-- Logo -->
    <a href="#" style="display: flex; align-items: center; gap: 10px; text-decoration: none; flex-shrink: 0;">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="3" width="21" height="17" rx="4" fill="#E8752C"></rect>
        <path d="M2 14.5l6 7V14.5H2z" fill="#E8752C"></path>
        <path d="M8 11.5l3.5 3.5 6-8" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path>
      </svg>
      <span style="font-size: 15px; font-weight: 800; letter-spacing: .08em; color: white; text-transform: uppercase;">NAGRIK AI</span>
    </a>

    <!-- Desktop nav links -->
    <div class="navlinks">
      <a href="#how-it-works" class="nl">How it works</a>
      <a href="#features" class="nl">Features</a>
      <a href="#chatbot" class="nl">Nagrik Saathi</a>
      <a href="#officials" class="nl">For Officials</a>
    </div>

    <!-- CTAs + hamburger -->
    <div style="display: flex; align-items: center; gap: 16px;">
      <router-link to="/login" class="nlogin">Log in</router-link>
      <router-link to="/register" class="btn-o">Register</router-link>
      <button class="hamburger" @click="toggleMenu" aria-label="Open menu">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>
    </div>
  </div>

  <!-- Mobile nav -->
  <div :class="mobileNavClass" style="background: #111; padding: 8px 24px 24px; border-top: 1px solid rgba(255,255,255,.08);">
    <a href="#how-it-works" class="mnl" @click="toggleMenu">How it works</a>
    <a href="#features" class="mnl" @click="toggleMenu">Features</a>
    <a href="#chatbot" class="mnl" @click="toggleMenu">Nagrik Saathi</a>
    <a href="#officials" class="mnl" @click="toggleMenu">For Officials</a>
    <div style="padding-top: 20px; display: flex; gap: 12px; flex-wrap: wrap;">
      <router-link to="/login" class="btn-ghost" @click="toggleMenu">Log in</router-link>
      <router-link to="/register" class="btn-o" @click="toggleMenu">Register</router-link>
    </div>
  </div>
</nav>


<!-- HERO -->
<section style="background: #F3EFE7; padding: 100px 0 88px;">
  <div class="w">
    <div class="hero-g">

      <!-- Left: copy + CTAs -->
      <div>
        <p style="font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #E8752C; margin-bottom: 18px;">Mumbai's Civic Complaint Platform</p>
        <h1 style="font-size: 58px; font-weight: 900; line-height: 1.07; letter-spacing: -.025em; color: #1A1A1A; margin-bottom: 24px; text-wrap: pretty;">{{ heroHeadline }}</h1>
        <p style="font-size: 18px; line-height: 1.7; color: #6E6858; margin-bottom: 40px; max-width: 510px;">File a civic issue in seconds — attach a photo, share your location. Our AI scores priority, routes it to the right BMC department, and keeps you updated until the job is done.</p>

        <div style="display: flex; gap: 16px; flex-wrap: wrap; align-items: center;">
          <router-link to="/register" class="btn-o-lg">
            <svg width="17" height="17" viewBox="0 0 17 17" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg"><circle cx="8.5" cy="6.5" r="3.5"></circle><path d="M8.5 10c-3.5 0-6 2-6 5h12c0-3-2.5-5-6-5z"></path></svg>
            Report an Issue
          </router-link>
          <a href="#how-it-works" class="btn-ol">See how it works</a>
        </div>

        <!-- Trust signals -->
        <div style="margin-top: 44px; padding-top: 36px; border-top: 1px solid #D9D2C2; display: flex; gap: 32px; flex-wrap: wrap;">
          <div>
            <p style="font-size: 22px; font-weight: 900; color: #1A1A1A; letter-spacing: -.02em;">{{ statsResolved }}</p>
            <p style="font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6E6858; margin-top: 2px;">Complaints resolved</p>
          </div>
          <div style="width: 1px; background: #D9D2C2;"></div>
          <div>
            <p style="font-size: 22px; font-weight: 900; color: #1A1A1A; letter-spacing: -.02em;">24 wards</p>
            <p style="font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6E6858; margin-top: 2px;">BMC coverage</p>
          </div>
          <div style="width: 1px; background: #D9D2C2;"></div>
          <div>
            <p style="font-size: 22px; font-weight: 900; color: #1A1A1A; letter-spacing: -.02em;">3.2 days</p>
            <p style="font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6E6858; margin-top: 2px;">Avg. resolution</p>
          </div>
        </div>
      </div>

      <!-- Right: phone illustration -->
      <div class="hero-vis">
        <svg viewBox="0 0 480 430" width="480" height="430" xmlns="http://www.w3.org/2000/svg" style="max-width: 100%;">
          <ellipse cx="272" cy="212" rx="208" ry="196" fill="#EDE9DF"></ellipse>
          <g stroke="#C4BAA8" stroke-width="0.9" opacity="0.38">
            <line x1="80" y1="38" x2="80" y2="400"></line>
            <line x1="152" y1="38" x2="152" y2="400"></line>
            <line x1="340" y1="38" x2="340" y2="400"></line>
            <line x1="412" y1="38" x2="412" y2="400"></line>
            <line x1="58" y1="96" x2="462" y2="96"></line>
            <line x1="58" y1="164" x2="462" y2="164"></line>
            <line x1="58" y1="296" x2="462" y2="296"></line>
            <line x1="58" y1="364" x2="462" y2="364"></line>
          </g>
          <g opacity="0.08" transform="translate(92,82)">
            <circle cx="0" cy="0" r="26" fill="#E8752C"></circle>
            <rect x="-5" y="22" width="10" height="52" rx="5" fill="#E8752C"></rect>
          </g>
          <rect x="167" y="46" width="170" height="320" rx="20" fill="#1A1A1A" opacity="0.07"></rect>
          <rect x="161" y="40" width="170" height="320" rx="20" fill="white" stroke="#1A1A1A" stroke-width="2"></rect>
          <rect x="163" y="42" width="166" height="40" rx="19" fill="#1A1A1A"></rect>
          <rect x="163" y="60" width="166" height="22" fill="#1A1A1A"></rect>
          <text x="246" y="67" text-anchor="middle" fill="white" font-family="Segoe UI,Arial,sans-serif" font-size="10" font-weight="700" letter-spacing="2">NAGRIK AI</text>
          <text x="173" y="99" fill="#1A1A1A" font-family="Segoe UI,Arial,sans-serif" font-size="12" font-weight="700">Report an Issue</text>
          <line x1="163" y1="107" x2="329" y2="107" stroke="#EDE9DF" stroke-width="1"></line>
          <circle cx="179" cy="121" r="6" fill="none" stroke="#E8752C" stroke-width="1.5"></circle>
          <circle cx="179" cy="119" r="2.5" fill="#E8752C"></circle>
          <line x1="179" y1="125" x2="179" y2="130" stroke="#E8752C" stroke-width="1.5" stroke-linecap="round"></line>
          <text x="191" y="126" fill="#1A1A1A" font-family="Arial,sans-serif" font-size="10">Andheri West, Mumbai</text>
          <line x1="163" y1="137" x2="329" y2="137" stroke="#EDE9DF" stroke-width="1"></line>
          <rect x="169" y="143" width="152" height="78" rx="4" fill="#F7F4EC" stroke="#D9D2C2" stroke-width="1" stroke-dasharray="4 3"></rect>
          <rect x="227" y="164" width="32" height="26" rx="4" fill="none" stroke="#6E6858" stroke-width="1.5"></rect>
          <circle cx="243" cy="177" r="8" fill="none" stroke="#6E6858" stroke-width="1.5"></circle>
          <circle cx="243" cy="177" r="4" fill="#E8752C" opacity="0.55"></circle>
          <rect x="230" y="161" width="10" height="6" rx="2" fill="none" stroke="#6E6858" stroke-width="1.5"></rect>
          <text x="243" y="208" text-anchor="middle" fill="#6E6858" font-family="Arial,sans-serif" font-size="9">Tap to add photo</text>
          <rect x="169" y="231" width="60" height="18" rx="9" fill="#E8752C"></rect>
          <text x="199" y="244" text-anchor="middle" fill="white" font-family="Arial,sans-serif" font-size="8" font-weight="700">POTHOLE</text>
          <rect x="235" y="231" width="60" height="18" rx="9" fill="none" stroke="#D9D2C2" stroke-width="1"></rect>
          <text x="265" y="244" text-anchor="middle" fill="#6E6858" font-family="Arial,sans-serif" font-size="8">DRAINAGE</text>
          <rect x="169" y="259" width="140" height="7" rx="3" fill="#EDE9DF"></rect>
          <rect x="169" y="271" width="108" height="7" rx="3" fill="#EDE9DF"></rect>
          <rect x="169" y="289" width="90" height="20" rx="4" fill="#FFF3EB"></rect>
          <rect x="169" y="289" width="4" height="20" rx="1" fill="#E8752C"></rect>
          <text x="201" y="303" text-anchor="middle" fill="#E8752C" font-family="Arial,sans-serif" font-size="8" font-weight="700">HIGH PRIORITY</text>
          <rect x="169" y="318" width="152" height="32" rx="4" fill="#E8752C"></rect>
          <text x="245" y="338" text-anchor="middle" fill="white" font-family="Arial,sans-serif" font-size="10.5" font-weight="700" letter-spacing="1">SUBMIT REPORT</text>
          <line x1="189" y1="390" x2="319" y2="390" stroke="#D9D2C2" stroke-width="2"></line>
          <circle cx="189" cy="390" r="11" fill="#1A1A1A"></circle>
          <path d="M185 390l3 3 6-7" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
          <text x="189" y="411" text-anchor="middle" fill="#1A1A1A" font-family="Arial,sans-serif" font-size="8" font-weight="600">Filed</text>
          <circle cx="232" cy="390" r="11" fill="#E8752C"></circle>
          <path d="M228 390l3 3 6-7" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
          <text x="232" y="411" text-anchor="middle" fill="#6E6858" font-family="Arial,sans-serif" font-size="8">Routed</text>
          <circle cx="275" cy="390" r="11" fill="none" stroke="#E8752C" stroke-width="2.5"></circle>
          <circle cx="275" cy="390" r="5" fill="#E8752C"></circle>
          <text x="275" y="411" text-anchor="middle" fill="#6E6858" font-family="Arial,sans-serif" font-size="8">In Progress</text>
          <circle cx="319" cy="390" r="11" fill="none" stroke="#D9D2C2" stroke-width="2"></circle>
          <text x="319" y="411" text-anchor="middle" fill="#C8C0B0" font-family="Arial,sans-serif" font-size="8">Resolved</text>
          <rect x="285" y="110" width="108" height="52" rx="6" fill="white" stroke="#D9D2C2" stroke-width="1"></rect>
          <rect x="285" y="110" width="4" height="52" rx="2" fill="#E8752C"></rect>
          <text x="298" y="128" fill="#1A1A1A" font-family="Segoe UI,Arial,sans-serif" font-size="9" font-weight="700">Status Update</text>
          <text x="298" y="142" fill="#6E6858" font-family="Arial,sans-serif" font-size="8">Ward Engineer assigned</text>
          <text x="298" y="155" fill="#3E8E5B" font-family="Arial,sans-serif" font-size="8" font-weight="600">On the way →</text>
        </svg>
      </div>
    </div>
  </div>
</section>


<!-- STATS -->
<section style="background: #F7F4EC; border-top: 1px solid #D9D2C2; border-bottom: 1px solid #D9D2C2;">
  <div class="w">
    <div class="stats-g">
      <div class="stile">
        <p style="font-size: 42px; font-weight: 900; color: #1A1A1A; letter-spacing: -.025em; line-height: 1.05;">{{ statsResolved }}</p>
        <p style="font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: #6E6858; margin-top: 8px;">Complaints Resolved</p>
      </div>
      <div class="stile">
        <p style="font-size: 42px; font-weight: 900; color: #1A1A1A; letter-spacing: -.025em; line-height: 1.05;">3.2 days</p>
        <p style="font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: #6E6858; margin-top: 8px;">Avg. Resolution Time</p>
      </div>
      <div class="stile">
        <p style="font-size: 42px; font-weight: 900; color: #1A1A1A; letter-spacing: -.025em; line-height: 1.05;">24</p>
        <p style="font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: #6E6858; margin-top: 8px;">BMC Wards Covered</p>
      </div>
      <div class="stile">
        <p style="font-size: 42px; font-weight: 900; color: #1A1A1A; letter-spacing: -.025em; line-height: 1.05;">4.6 / 5</p>
        <p style="font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: #6E6858; margin-top: 8px;">Citizen Satisfaction</p>
      </div>
    </div>
  </div>
</section>


<!-- HOW IT WORKS -->
<section id="how-it-works" style="background: white; padding: 96px 0;">
  <div class="w">
    <p style="font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #E8752C; margin-bottom: 12px;">Simple, transparent process</p>
    <h2 style="font-size: 40px; font-weight: 900; line-height: 1.1; letter-spacing: -.015em; margin-bottom: 60px; max-width: 560px;">From complaint filed to problem fixed</h2>

    <div class="steps-g">
      <div>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
          <div style="width: 36px; height: 36px; border-radius: 50%; background: #E8752C; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <span style="font-size: 15px; font-weight: 800; color: white; line-height: 1;">1</span>
          </div>
          <div style="flex: 1; height: 1px; background: #D9D2C2;"></div>
        </div>
        <div style="margin-bottom: 16px; color: #E8752C;">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#E8752C" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="8" width="24" height="18" rx="3"></rect>
            <circle cx="16" cy="17" r="5"></circle>
            <path d="M12 8V6l2-2h4l2 2v2"></path>
            <circle cx="22" cy="12" r="1.5" fill="#E8752C" stroke="none"></circle>
          </svg>
        </div>
        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">Describe and photograph</h3>
        <p style="font-size: 14px; color: #6E6858; line-height: 1.65;">Tap to report, attach a photo, and confirm your location. Under a minute start to finish.</p>
      </div>

      <div>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
          <div style="width: 36px; height: 36px; border-radius: 50%; background: #E8752C; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <span style="font-size: 15px; font-weight: 800; color: white; line-height: 1;">2</span>
          </div>
          <div style="flex: 1; height: 1px; background: #D9D2C2;"></div>
        </div>
        <div style="margin-bottom: 16px;">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#E8752C" stroke-width="1.75" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="5"></circle>
            <path d="M16 4v4M16 24v4M4 16h4M24 16h4M7.03 7.03l2.83 2.83M22.14 22.14l2.83 2.83M7.03 24.97l2.83-2.83M22.14 9.86l2.83-2.83"></path>
          </svg>
        </div>
        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">AI scores and routes it</h3>
        <p style="font-size: 14px; color: #6E6858; line-height: 1.65;">The AI reads your report, scores its urgency, and sends it straight to the right ward department.</p>
      </div>

      <div>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
          <div style="width: 36px; height: 36px; border-radius: 50%; background: #E8752C; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <span style="font-size: 15px; font-weight: 800; color: white; line-height: 1;">3</span>
          </div>
          <div style="flex: 1; height: 1px; background: #D9D2C2;"></div>
        </div>
        <div style="margin-bottom: 16px;">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#E8752C" stroke-width="1.75" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="12"></circle>
            <path d="M16 9v7l4 3"></path>
          </svg>
        </div>
        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">Track in real time</h3>
        <p style="font-size: 14px; color: #6E6858; line-height: 1.65;">Watch every status change — Approved, In Progress, Resolved — as it happens.</p>
      </div>

      <div>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
          <div style="width: 36px; height: 36px; border-radius: 50%; background: #E8752C; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <span style="font-size: 15px; font-weight: 800; color: white; line-height: 1;">4</span>
          </div>
          <div style="flex: 1; height: 1px; background: transparent;"></div>
        </div>
        <div style="margin-bottom: 16px;">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#E8752C" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <polygon points="16,4 19.5,12.5 29,12.5 21.8,18.2 24.5,27 16,21.5 7.5,27 10.2,18.2 3,12.5 12.5,12.5"></polygon>
          </svg>
        </div>
        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">Rate the resolution</h3>
        <p style="font-size: 14px; color: #6E6858; line-height: 1.65;">After closure, rate the work. Your feedback builds a public accountability record.</p>
      </div>
    </div>
  </div>
</section>


<!-- FEATURE GRID -->
<section id="features" style="background: #F3EFE7; padding: 96px 0;">
  <div class="w">
    <p style="font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #E8752C; margin-bottom: 12px;">What it does</p>
    <h2 style="font-size: 40px; font-weight: 900; line-height: 1.1; letter-spacing: -.015em; margin-bottom: 56px; max-width: 600px;">Everything a complaint needs to actually get resolved.</h2>

    <div class="feat-g">
      <div class="fcard">
        <div style="margin-bottom: 18px;">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#1A1A1A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="7" width="22" height="16" rx="3"></rect>
            <circle cx="14" cy="15" r="4.5"></circle>
            <path d="M11 7V5.5L12.5 4h3L17 5.5V7"></path>
            <circle cx="20.5" cy="11" r="1.5" fill="#1A1A1A" stroke="none"></circle>
          </svg>
        </div>
        <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">Photo + location filing</h3>
        <p style="font-size: 13px; color: #6E6858; line-height: 1.65;">Attach evidence and pin the exact location on a map. No ambiguity, no back-and-forth with the office.</p>
      </div>

      <div class="fcard">
        <div style="margin-bottom: 18px;">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#1A1A1A" stroke-width="1.5" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg">
            <circle cx="14" cy="14" r="5"></circle>
            <path d="M14 3v3M14 22v3M3 14h3M22 14h3M5.93 5.93l2.12 2.12M19.95 19.95l2.12 2.12M5.93 22.07l2.12-2.12M19.95 8.05l2.12-2.12"></path>
          </svg>
        </div>
        <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">AI priority scoring</h3>
        <p style="font-size: 13px; color: #6E6858; line-height: 1.65;">Every complaint is automatically scored Low, Medium, or High — so dangerous issues skip the queue.</p>
      </div>

      <div class="fcard">
        <div style="margin-bottom: 18px;">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#1A1A1A" stroke-width="1.5" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg">
            <circle cx="14" cy="14" r="11"></circle>
            <path d="M14 8v6l4 3"></path>
          </svg>
        </div>
        <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">Real-time status tracking</h3>
        <p style="font-size: 13px; color: #6E6858; line-height: 1.65;">Every status change — Filed, Approved, In Progress, Resolved — visible to you the moment it happens.</p>
      </div>

      <div class="fcard">
        <div style="margin-bottom: 18px;">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#1A1A1A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 4h19a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H7l-6 5V6a2 2 0 0 1 2-2z"></path>
            <circle cx="9" cy="13" r="1.4" fill="#1A1A1A" stroke="none"></circle>
            <circle cx="14" cy="13" r="1.4" fill="#1A1A1A" stroke="none"></circle>
            <circle cx="19" cy="13" r="1.4" fill="#1A1A1A" stroke="none"></circle>
          </svg>
        </div>
        <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">Nagrik Saathi AI assistant</h3>
        <p style="font-size: 13px; color: #6E6858; line-height: 1.65;">A helpful local AI guide — answers questions, helps you file, and connects you to 1916 when you need a human.</p>
      </div>

      <div class="fcard">
        <div style="margin-bottom: 18px;">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#1A1A1A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <circle cx="5" cy="14" r="3"></circle>
            <circle cx="23" cy="7" r="3"></circle>
            <circle cx="23" cy="21" r="3"></circle>
            <path d="M8 14h6l6-7M14 14l8 7"></path>
          </svg>
        </div>
        <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">Department auto-routing</h3>
        <p style="font-size: 13px; color: #6E6858; line-height: 1.65;">Complaints go directly to roads, drainage, sanitation, or electrical — no manual triage or phone tag needed.</p>
      </div>

      <div class="fcard">
        <div style="margin-bottom: 18px;">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#1A1A1A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
            <polygon points="14,3 17.5,11.5 27,11.5 19.7,17.3 22.5,26 14,20.5 5.5,26 8.3,17.3 1,11.5 10.5,11.5"></polygon>
          </svg>
        </div>
        <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">Ratings and accountability</h3>
        <p style="font-size: 13px; color: #6E6858; line-height: 1.65;">Rate resolution quality after closure. Scores build a public record that holds departments accountable.</p>
      </div>
    </div>
  </div>
</section>


<!-- SAATHI -->
<section v-if="showChatbot" id="chatbot" style="background: white; padding: 96px 0;">
  <div class="w">
    <div class="chat-g">

      <div>
        <p style="font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #E8752C; margin-bottom: 12px;">Your civic aide</p>
        <h2 style="font-size: 40px; font-weight: 900; line-height: 1.1; letter-spacing: -.015em; margin-bottom: 20px;">Meet Nagrik Saathi</h2>
        <p style="font-size: 17px; line-height: 1.75; color: #6E6858; margin-bottom: 20px;">A plain-spoken AI guide built right into the app. Ask it anything about your complaint, get help filing a new one, or let it connect you to the BMC helpline when you need a real person.</p>
        <p style="font-size: 17px; line-height: 1.75; color: #6E6858; margin-bottom: 40px;">Short answers. Plain language. Never jargon-heavy.</p>
        <a href="#" class="btn-o-lg">Try Nagrik Saathi</a>
      </div>

      <div>
        <div style="background: #F3EFE7; border-radius: 8px; border: 1px solid #D9D2C2; overflow: hidden;">

          <div style="background: #1A1A1A; padding: 14px 20px; display: flex; align-items: center; gap: 12px;">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: #E8752C; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
                <path d="M1.5 2.5h14a.5.5 0 0 1 .5.5v9a.5.5 0 0 1-.5.5H4.5L1 16V3a.5.5 0 0 1 .5-.5z"></path>
              </svg>
            </div>
            <div>
              <p style="font-size: 13px; font-weight: 700; color: white; letter-spacing: .02em;">Nagrik Saathi</p>
              <p style="font-size: 11px; color: rgba(255,255,255,.5); display: flex; align-items: center; gap: 5px; margin-top: 1px;">
                <span style="display: inline-block; width: 6px; height: 6px; background: #3E8E5B; border-radius: 50%;"></span> Online
              </p>
            </div>
          </div>

          <div style="padding: 20px; display: flex; flex-direction: column; gap: 16px;">

            <div style="display: flex; justify-content: flex-end;">
              <div style="background: #E8752C; color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; font-size: 13px; line-height: 1.55; max-width: 82%;">
                There's a huge pothole near Linking Road, Bandra. Cars are swerving around it.
              </div>
            </div>

            <div style="display: flex; gap: 9px; align-items: flex-start;">
              <div style="width: 28px; height: 28px; border-radius: 50%; background: #E8752C; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg"><path d="M1 2h11a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-.5.5H4L.5 12.5V2.5A.5.5 0 0 1 1 2z"></path></svg>
              </div>
              <div style="background: white; border: 1px solid #D9D2C2; padding: 10px 14px; border-radius: 2px 12px 12px 12px; font-size: 13px; line-height: 1.55; max-width: 82%; color: #1A1A1A;">
                Got it — pothole near Linking Road, Bandra. Can you share a quick photo so we can log the severity?
              </div>
            </div>

            <div style="display: flex; justify-content: flex-end;">
              <div style="background: #E8752C; color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; font-size: 13px; line-height: 1.55; max-width: 82%;">
                Done. When will it be fixed?
              </div>
            </div>

            <div style="display: flex; gap: 9px; align-items: flex-start;">
              <div style="width: 28px; height: 28px; border-radius: 50%; background: #E8752C; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg"><path d="M1 2h11a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-.5.5H4L.5 12.5V2.5A.5.5 0 0 1 1 2z"></path></svg>
              </div>
              <div style="background: white; border: 1px solid #D9D2C2; padding: 10px 14px; border-radius: 2px 12px 12px 12px; font-size: 13px; line-height: 1.55; max-width: 82%; color: #1A1A1A;">
                Complaint <span style="font-weight: 700; color: #E8752C;">#BK-2847</span> filed and sent to the Bandra Ward road team. You'll hear back within 24 hours.
              </div>
            </div>
          </div>

          <div style="padding: 12px 16px; border-top: 1px solid #D9D2C2; display: flex; gap: 10px; align-items: center; background: white;">
            <div style="flex: 1; background: #F7F4EC; border: 1px solid #D9D2C2; border-radius: 4px; padding: 9px 14px; font-size: 13px; color: #6E6858;">Type your message...</div>
            <button style="background: #E8752C; border: none; border-radius: 4px; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0;">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg"><path d="M13.5 1.5L7 8M13.5 1.5L8.5 14 7 8 1 6.5 13.5 1.5z"></path></svg>
            </button>
          </div>
        </div>

        <div style="margin-top: 16px; background: #F7F4EC; border: 1px solid #D9D2C2; border-radius: 4px; padding: 14px 18px; display: flex; align-items: center; gap: 14px;">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#6E6858" stroke-width="1.5" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg"><path d="M3.5 4a2 2 0 0 1 2-2h.5a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H6A7.5 7.5 0 0 0 13.5 14h-.5a1 1 0 0 1-1-1v-.5a1 1 0 0 1 1-1h.5a2 2 0 0 1 2 2v.5a2 2 0 0 1-2 2H13A10 10 0 0 1 3 5.5V4z"></path></svg>
          <div>
            <p style="font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #6E6858; margin-bottom: 2px;">BMC Helpline</p>
            <p style="font-size: 18px; font-weight: 900; color: #1A1A1A; letter-spacing: .02em;">1916</p>
          </div>
          <p style="font-size: 13px; color: #6E6858; margin-left: 4px; line-height: 1.5;">When Nagrik Saathi isn't enough, call directly.</p>
        </div>
      </div>
    </div>
  </div>
</section>


<!-- OFFICIALS -->
<section id="officials" style="background: #F7F4EC; padding: 96px 0; border-top: 1px solid #D9D2C2;">
  <div class="w">
    <div class="off-g">

      <div>
        <p style="font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #E8752C; margin-bottom: 12px;">For municipal staff</p>
        <h2 style="font-size: 40px; font-weight: 900; line-height: 1.1; letter-spacing: -.015em; margin-bottom: 20px;">A clearer view of every ward's workload</h2>
        <p style="font-size: 17px; line-height: 1.75; color: #6E6858; margin-bottom: 36px;">Officers and admins get a separate dashboard — complaint volumes by department, SLA breach alerts, field worker assignment, and resolution rate tracking across all wards.</p>

        <div style="display: flex; flex-direction: column; gap: 16px; margin-bottom: 40px;">
          <div style="display: flex; align-items: flex-start; gap: 14px;">
            <div style="width: 20px; height: 20px; border-radius: 50%; background: #E8752C; flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center;">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg"><path d="M2 5l2.5 2.5 4-5"></path></svg>
            </div>
            <p style="font-size: 15px; color: #1A1A1A; line-height: 1.55;">Analytics dashboard with complaint trends and resolution rates</p>
          </div>
          <div style="display: flex; align-items: flex-start; gap: 14px;">
            <div style="width: 20px; height: 20px; border-radius: 50%; background: #E8752C; flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center;">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg"><path d="M2 5l2.5 2.5 4-5"></path></svg>
            </div>
            <p style="font-size: 15px; color: #1A1A1A; line-height: 1.55;">Automatic SLA alerts before deadlines are breached</p>
          </div>
          <div style="display: flex; align-items: flex-start; gap: 14px;">
            <div style="width: 20px; height: 20px; border-radius: 50%; background: #E8752C; flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center;">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg"><path d="M2 5l2.5 2.5 4-5"></path></svg>
            </div>
            <p style="font-size: 15px; color: #1A1A1A; line-height: 1.55;">Workload distribution across field workers and departments</p>
          </div>
          <div style="display: flex; align-items: flex-start; gap: 14px;">
            <div style="width: 20px; height: 20px; border-radius: 50%; background: #E8752C; flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center;">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg"><path d="M2 5l2.5 2.5 4-5"></path></svg>
            </div>
            <p style="font-size: 15px; color: #1A1A1A; line-height: 1.55;">Citizen satisfaction scores per ward and department</p>
          </div>
        </div>

        <router-link to="/login" class="btn-ol-sm">Municipal staff login</router-link>
      </div>

      <div>
        <div style="background: white; border: 1px solid #D9D2C2; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.06);">

          <div style="background: #1A1A1A; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between;">
            <p style="font-size: 12px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: white;">Ward Analytics — Andheri</p>
            <p style="font-size: 11px; color: rgba(255,255,255,.4);">July 2026</p>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); border-bottom: 1px solid #F0EBE0;">
            <div style="padding: 16px 20px; border-right: 1px solid #F0EBE0;">
              <p style="font-size: 28px; font-weight: 900; color: #1A1A1A; letter-spacing: -.02em;">142</p>
              <p style="font-size: 10px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6E6858; margin-top: 2px;">Open</p>
            </div>
            <div style="padding: 16px 20px; border-right: 1px solid #F0EBE0;">
              <p style="font-size: 28px; font-weight: 900; color: #E8752C; letter-spacing: -.02em;">28</p>
              <p style="font-size: 10px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6E6858; margin-top: 2px;">SLA Breach</p>
            </div>
            <div style="padding: 16px 20px;">
              <p style="font-size: 28px; font-weight: 900; color: #3E8E5B; letter-spacing: -.02em;">89%</p>
              <p style="font-size: 10px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6E6858; margin-top: 2px;">Resolved</p>
            </div>
          </div>

          <div style="padding: 20px;">
            <p style="font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #6E6858; margin-bottom: 14px;">Complaints by Department</p>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                  <span style="font-size: 12px; color: #1A1A1A; font-weight: 600;">Roads</span>
                  <span style="font-size: 12px; color: #6E6858;">48</span>
                </div>
                <div style="height: 8px; background: #F0EBE0; border-radius: 4px; overflow: hidden;">
                  <div style="height: 100%; width: 68%; background: #E8752C; border-radius: 4px;"></div>
                </div>
              </div>
              <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                  <span style="font-size: 12px; color: #1A1A1A; font-weight: 600;">Drainage</span>
                  <span style="font-size: 12px; color: #6E6858;">35</span>
                </div>
                <div style="height: 8px; background: #F0EBE0; border-radius: 4px; overflow: hidden;">
                  <div style="height: 100%; width: 49%; background: #E8752C; border-radius: 4px;"></div>
                </div>
              </div>
              <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                  <span style="font-size: 12px; color: #1A1A1A; font-weight: 600;">Sanitation</span>
                  <span style="font-size: 12px; color: #6E6858;">29</span>
                </div>
                <div style="height: 8px; background: #F0EBE0; border-radius: 4px; overflow: hidden;">
                  <div style="height: 100%; width: 41%; background: #E8752C; border-radius: 4px;"></div>
                </div>
              </div>
              <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                  <span style="font-size: 12px; color: #1A1A1A; font-weight: 600;">Electrical</span>
                  <span style="font-size: 12px; color: #6E6858;">18</span>
                </div>
                <div style="height: 8px; background: #F0EBE0; border-radius: 4px; overflow: hidden;">
                  <div style="height: 100%; width: 26%; background: #E8752C; border-radius: 4px;"></div>
                </div>
              </div>
            </div>
          </div>

          <div style="border-top: 1px solid #F0EBE0;">
            <div style="padding: 10px 20px; background: #F7F4EC; display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #6E6858;">Recent Complaints</span>
              <span style="font-size: 11px; color: #E8752C; font-weight: 600; cursor: pointer;">View all</span>
            </div>
            <div style="padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #F7F4EC;">
              <div>
                <p style="font-size: 12px; font-weight: 600; color: #1A1A1A;">#AN-1093 · Pothole, Andheri W</p>
                <p style="font-size: 11px; color: #6E6858; margin-top: 1px;">Roads · 2 h ago</p>
              </div>
              <span style="font-size: 10px; font-weight: 700; padding: 3px 8px; background: #FFF3EB; color: #E8752C; border-radius: 4px; letter-spacing: .06em; white-space: nowrap;">HIGH</span>
            </div>
            <div style="padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #F7F4EC;">
              <div>
                <p style="font-size: 12px; font-weight: 600; color: #1A1A1A;">#BK-2847 · Drainage overflow</p>
                <p style="font-size: 11px; color: #6E6858; margin-top: 1px;">Drainage · 5 h ago</p>
              </div>
              <span style="font-size: 10px; font-weight: 700; padding: 3px 8px; background: #F0FAF4; color: #3E8E5B; border-radius: 4px; letter-spacing: .06em; white-space: nowrap;">RESOLVED</span>
            </div>
            <div style="padding: 10px 20px; display: flex; align-items: center; justify-content: space-between;">
              <div>
                <p style="font-size: 12px; font-weight: 600; color: #1A1A1A;">#DN-0441 · Street light out</p>
                <p style="font-size: 11px; color: #6E6858; margin-top: 1px;">Electrical · 1 d ago</p>
              </div>
              <span style="font-size: 10px; font-weight: 700; padding: 3px 8px; background: #FFFBEB; color: #B8860B; border-radius: 4px; letter-spacing: .06em; white-space: nowrap;">IN PROGRESS</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>


<!-- FOOTER -->
<footer style="background: #1A1A1A; padding: 64px 0 0;">
  <div class="w">
    <div class="foot-g" style="padding-bottom: 52px; border-bottom: 1px solid rgba(255,255,255,.08);">

      <div>
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="3" width="21" height="17" rx="4" fill="#E8752C"></rect>
            <path d="M2 14.5l6 7V14.5H2z" fill="#E8752C"></path>
            <path d="M8 11.5l3.5 3.5 6-8" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
          <span style="font-size: 14px; font-weight: 800; letter-spacing: .08em; color: white; text-transform: uppercase;">NAGRIK AI</span>
        </div>
        <p style="font-size: 13px; color: rgba(255,255,255,.48); line-height: 1.7; max-width: 210px; margin-bottom: 28px;">Civic complaint management for Mumbai's residents, built for the BMC ecosystem.</p>
        <p style="font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: rgba(255,255,255,.32); margin-bottom: 4px;">BMC Helpline</p>
        <p style="font-size: 26px; font-weight: 900; color: white; letter-spacing: .02em;">1916</p>
      </div>

      <div>
        <p style="font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: rgba(255,255,255,.3); margin-bottom: 20px;">Product</p>
        <div style="display: flex; flex-direction: column; gap: 13px;">
          <a href="#how-it-works" class="flink">How it works</a>
          <a href="#features" class="flink">Features</a>
          <a href="#chatbot" class="flink">Nagrik Saathi</a>
          <a href="#officials" class="flink">For Officials</a>
        </div>
      </div>

      <div>
        <p style="font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: rgba(255,255,255,.3); margin-bottom: 20px;">For Citizens</p>
        <div style="display: flex; flex-direction: column; gap: 13px;">
          <a href="#" class="flink">File a complaint</a>
          <a href="#" class="flink">Track your complaint</a>
          <router-link to="/register" class="flink">Register</router-link>
          <router-link to="/login" class="flink">Log in</router-link>
        </div>
      </div>

      <div>
        <p style="font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: rgba(255,255,255,.3); margin-bottom: 20px;">For Officials</p>
        <div style="display: flex; flex-direction: column; gap: 13px;">
          <router-link to="/login" class="flink">Staff login</router-link>
          <a href="#" class="flink">Admin dashboard</a>
          <a href="#" class="flink">Ward analytics</a>
          <a href="#" class="flink">Field worker app</a>
        </div>
      </div>

      <div>
        <p style="font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: rgba(255,255,255,.3); margin-bottom: 20px;">Help &amp; Legal</p>
        <div style="display: flex; flex-direction: column; gap: 13px;">
          <a href="#" class="flink">FAQ</a>
          <a href="#" class="flink">Privacy policy</a>
          <a href="#" class="flink">Terms of service</a>
          <a href="#" class="flink">Contact us</a>
        </div>
      </div>
    </div>

    <div style="padding: 20px 0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
      <p style="font-size: 12px; color: rgba(255,255,255,.28);">© 2026 Nagrik AI. Built for Mumbai's residents.</p>
      <p style="font-size: 12px; color: rgba(255,255,255,.28);">Part of the BMC Digital Services ecosystem.</p>
    </div>
  </div>
</footer>

</div>
</template>

<style scoped>
.landing-page { /* isolates from the app-wide .app-content max-width/padding rules */ }

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { background: #F3EFE7; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #1A1A1A; line-height: 1.6; }
a { color: #E8752C; text-decoration: none; }
a:hover { color: #C7601E; }
*:focus-visible { outline: 2px solid #E8752C; outline-offset: 1px; }

.navlinks { display: flex; align-items: center; gap: 32px; }
.nl { color: rgba(255,255,255,.68); font-size: 13px; font-weight: 500; letter-spacing: .05em; text-transform: uppercase; text-decoration: none; transition: color .15s; }
.nl:hover { color: #fff; }
.nlogin { color: rgba(255,255,255,.68); font-size: 13px; font-weight: 600; text-decoration: none; transition: color .15s; }
.nlogin:hover { color: #fff; }

.btn-o    { display: inline-flex; align-items: center; gap: 7px; background: #E8752C; color: #fff; font-weight: 700; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; padding: 9px 20px; border-radius: 4px; border: none; cursor: pointer; text-decoration: none; transition: background .15s; white-space: nowrap; }
.btn-o:hover  { background: #C7601E; color: #fff; }
.btn-o-lg { display: inline-flex; align-items: center; gap: 8px; background: #E8752C; color: #fff; font-weight: 700; font-size: 14px; letter-spacing: .04em; text-transform: uppercase; padding: 14px 28px; border-radius: 4px; border: none; cursor: pointer; text-decoration: none; transition: background .15s; white-space: nowrap; }
.btn-o-lg:hover { background: #C7601E; color: #fff; }
.btn-ol   { display: inline-flex; align-items: center; gap: 8px; background: transparent; color: #1A1A1A; font-weight: 700; font-size: 14px; letter-spacing: .04em; text-transform: uppercase; padding: 13px 26px; border-radius: 4px; border: 2px solid #1A1A1A; cursor: pointer; text-decoration: none; transition: background .15s, color .15s; }
.btn-ol:hover  { background: #1A1A1A; color: #fff; }
.btn-ghost { display: inline-flex; align-items: center; background: transparent; color: #fff; font-weight: 700; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; padding: 8px 18px; border-radius: 4px; border: 1.5px solid rgba(255,255,255,.4); cursor: pointer; text-decoration: none; transition: border-color .15s; }
.btn-ghost:hover { border-color: #fff; }
.btn-ol-sm { display: inline-flex; align-items: center; background: transparent; color: #1A1A1A; font-weight: 700; font-size: 12px; letter-spacing: .04em; text-transform: uppercase; padding: 9px 20px; border-radius: 4px; border: 2px solid #1A1A1A; cursor: pointer; text-decoration: none; transition: background .15s, color .15s; }
.btn-ol-sm:hover { background: #1A1A1A; color: #fff; }

.hamburger { display: none; background: none; border: none; cursor: pointer; padding: 4px; color: white; line-height: 0; }
.mobile-nav { display: none; }
.mobile-nav.open { display: flex; flex-direction: column; }
.mnl { color: rgba(255,255,255,.72); font-size: 15px; font-weight: 500; letter-spacing: .04em; text-transform: uppercase; text-decoration: none; padding: 14px 0; display: block; border-bottom: 1px solid rgba(255,255,255,.08); transition: color .15s; }
.mnl:hover { color: #fff; }

.hero-vis { display: flex; justify-content: center; align-items: center; }

.fcard { background: white; border: 1px solid #D9D2C2; border-radius: 4px; padding: 28px; transition: box-shadow .2s, border-color .2s; }
.fcard:hover { box-shadow: 0 6px 24px rgba(0,0,0,.07); border-color: #B8AFA0; }

.flink { font-size: 13px; color: rgba(255,255,255,.6); text-decoration: none; transition: color .15s; }
.flink:hover { color: #fff; }

.stile { padding: 32px 40px; border-right: 1px solid #D9D2C2; }
.stile:last-child { border-right: none; }

.w         { max-width: 1320px; margin: 0 auto; padding: 0 48px; }
.hero-g    { display: grid; grid-template-columns: 1fr 1fr; gap: 72px; align-items: center; }
.stats-g   { display: grid; grid-template-columns: repeat(4, 1fr); }
.steps-g   { display: grid; grid-template-columns: repeat(4, 1fr); gap: 28px; }
.feat-g    { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.chat-g    { display: grid; grid-template-columns: 1fr 1fr; gap: 72px; align-items: center; }
.off-g     { display: grid; grid-template-columns: 1fr 1fr; gap: 72px; align-items: center; }
.foot-g    { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 48px; }

section { scroll-margin-top: 64px; }

@media (max-width: 1024px) {
  .w         { padding: 0 24px; }
  .hero-g    { grid-template-columns: 1fr; }
  .hero-vis  { display: none !important; }
  .off-g     { grid-template-columns: 1fr; }
  .chat-g    { grid-template-columns: 1fr; }
  .foot-g    { grid-template-columns: 1fr 1fr; gap: 32px; }
}
@media (max-width: 768px) {
  .navlinks  { display: none !important; }
  .hamburger { display: flex !important; }
  .stats-g   { grid-template-columns: repeat(2, 1fr); }
  .stile     { border-right: none; border-bottom: 1px solid #D9D2C2; }
  .stile:last-child { border-bottom: none; }
  .steps-g   { grid-template-columns: 1fr 1fr; gap: 20px; }
  .feat-g    { grid-template-columns: 1fr 1fr; gap: 16px; }
}
@media (max-width: 480px) {
  .steps-g   { grid-template-columns: 1fr; }
  .feat-g    { grid-template-columns: 1fr; }
  .foot-g    { grid-template-columns: 1fr; gap: 24px; }
}
</style>