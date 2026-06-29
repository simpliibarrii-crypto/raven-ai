// openclinical-ai — v0.5.0
// Multi-tenant. Voice-first. Browser-only. No build step.
// White+red theme, light/dark mode, EN/FR i18n, connector registry, business portal.
// Call bell integration: push notifications + care plan preload per floor.
// Threat model: all free-text inputs sanitized for prompt-injection before AI.
// All protected endpoints require X-Tenant-ID + X-Tenant-API-Key + X-PSW-ID.

'use strict';

// -- i18n engine ------------------------------------------------------------

const I18N = {
  locale: 'en',
  strings: {},
  loaded: {},

  async load(loc) {
    if (this.loaded[loc]) return;
    try {
      const res = await fetch(`locales/${loc}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.strings = await res.json();
      this.locale = loc;
      this.loaded[loc] = true;
    } catch (e) {
      console.warn(`Failed to load locale ${loc}:`, e.message);
    }
  },

  t(key) {
    return this.strings[key] || key;
  },

  applyToDOM() {
    for (const el of document.querySelectorAll('[data-i18n]')) {
      const key = el.dataset.i18n;
      el.textContent = this.t(key);
    }
    for (const el of document.querySelectorAll('[data-i18n-placeholder]')) {
      el.placeholder = this.t(el.dataset.i18nPlaceholder);
    }
    // Update settings language buttons
    for (const btn of document.querySelectorAll('[data-lang-choice]')) {
      btn.classList.toggle('active', btn.dataset.langChoice === this.locale);
    }
    document.documentElement.lang = this.locale;
  }
};

// -- theme engine -----------------------------------------------------------

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'dark' ? '☾' : '☀';
  // Update settings theme buttons
  for (const b of document.querySelectorAll('[data-theme-choice]')) {
    b.classList.toggle('active', b.dataset.themeChoice === theme);
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem('openclinical.theme', next); } catch (e) {}
}

// -- prompt-injection sanitization ------------------------------------------

const INJECTION_PATTERNS = [
  /ignore (prior|previous|all) instructions?/i,
  /disregard (your|all) (rules|instructions)/i,
  /you are (now|actually) /i,
  /new instructions?:/i,
  /system:?\s/i,
  /assistant:?\s/i,
  /forget (everything|all)/i,
  /reveal (your|the) (prompt|instructions|system)/i,
  /output (the )?(patient|client)(['s]? )(ssn|sin|health card|address)/i,
  /\bSSN\b|\bSIN\b|\bPHN\b/,
  /password|api[_-]?key|secret/i,
];

function sanitize(text) {
  if (!text) return { text: '', flagged: false };
  let s = String(text);
  let flagged = false;
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(s)) { flagged = true; s = s.replace(pattern, '[redacted]'); }
  }
  return { text: s, flagged };
}

// -- state ------------------------------------------------------------------

const state = {
  runtimeUrl: 'http://localhost:8088',
  tenantId: '', tenantName: '', encryptionModel: '',
  pswId: '', authToken: '', consentToken: '',
  facilityId: '', floorId: '', floorPlans: [],  // v0.5.0 — care plan preload
  callbellPolling: null, serviceWorker: null,     // v0.5.0 — push notifications
  recognition: null, recognizing: false,
  currentVisit: null, visitClockIn: null,
};

// -- DOM refs ---------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const dom = {
  serverDot: $('server-dot'),
  tenantSelect: $('tenant-select'),
  encryptionText: $('encryption-text'),
  pswId: $('psw-id'),
  authMethod: $('auth-method'),
  runtimeUrl: $('runtime-url'),
  facilityId: $('facility-id'), floorId: $('floor-id'),  // v0.5.0
  signinBtn: $('signin-btn'),
  setupMessage: $('setup-message'),
  setupCard: $('setup-card'), todayCard: $('today-card'),
  visitCard: $('visit-card'), resultCard: $('result-card'),
  auditCard: $('audit-card'),
  pswLabel: $('psw-label'), visitList: $('visit-list'),
  refreshVisitsBtn: $('refresh-visits-btn'),
  visitClientLabel: $('visit-client-label'),
  visitClockTime: $('visit-clock-time'),
  visitStatusBadge: $('visit-status-badge'),
  visitAddress: $('visit-address'), visitGps: $('visit-gps'),
  voiceBtn: $('voice-btn'), voiceBtnText: $('voice-btn-text'),
  voiceStatus: $('voice-status'),
  completeVisitBtn: $('complete-visit-btn'),
  visitMessage: $('visit-message'),
  resultClientLabel: $('result-client-label'),
  resultContent: $('result-content'),
  nextVisitBtn: $('next-visit-btn'),
  auditContent: $('audit-content'),
};

// -- utilities --------------------------------------------------------------

function show(el) { el.classList.remove('hidden'); }
function hide(el) { el.classList.add('hidden'); }
function showMsg(el, text, kind) {
  el.textContent = text; el.className = `message ${kind || 'info'}`;
  show(el); if (kind === 'success') setTimeout(() => hide(el), 4000);
}
function h(s) { return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[c]); }

// -- API --------------------------------------------------------------------

function apiHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Tenant-ID': state.tenantId,
    'X-Tenant-API-Key': state.authToken,
    'X-PSW-ID': state.pswId,
  };
}

async function apiGet(path) {
  const res = await fetch(`${state.runtimeUrl}${path}`, { method: 'GET', headers: apiHeaders() });
  if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `HTTP ${res.status}`); }
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${state.runtimeUrl}${path}`, { method: 'POST', headers: apiHeaders(), body: JSON.stringify(body) });
  if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `HTTP ${res.status}`); }
  return res.json();
}

// -- server health ----------------------------------------------------------

async function checkServer() {
  try {
    const res = await fetch(`${state.runtimeUrl}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    dom.serverDot.className = 'status-dot status-healthy';
    dom.serverDot.title = `runtime v${data.version} · ${data.models_loaded} model(s)`;
    return true;
  } catch (e) {
    dom.serverDot.className = 'status-dot status-error';
    dom.serverDot.title = I18N.t('server.unreachable');
    return false;
  }
}

// -- tenants ----------------------------------------------------------------

async function loadTenants() {
  try {
    const res = await fetch(`${state.runtimeUrl}/v1/tenants`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    dom.tenantSelect.innerHTML =
      `<option value="">— ${I18N.t('setup.select')} —</option>` +
      (data.tenants || []).map(t =>
        `<option value="${h(t.id)}" data-name="${h(t.name)}" data-encryption="${h(t.encryption_model || '')}">${h(t.name)}</option>`
      ).join('');
  } catch (e) {
    dom.tenantSelect.innerHTML = `<option value="">— ${I18N.t('setup.unreachable')} —</option>`;
  }
}

dom.tenantSelect.addEventListener('change', () => {
  const opt = dom.tenantSelect.options[dom.tenantSelect.selectedIndex];
  if (!opt || !opt.value) return;
  const enc = opt.dataset.encryption;
  if (enc === 'agency-byok') dom.encryptionText.textContent = I18N.t('setup.byok');
  else if (enc === 'platform-managed') dom.encryptionText.textContent = I18N.t('setup.platform');
  else dom.encryptionText.textContent = I18N.t('setup.shared');
});

// -- sign in ----------------------------------------------------------------

async function signIn() {
  const opt = dom.tenantSelect.options[dom.tenantSelect.selectedIndex];
  if (!opt || !opt.value) { showMsg(dom.setupMessage, I18N.t('error.signin_failed'), 'error'); return; }

  state.tenantId = opt.value;
  state.tenantName = opt.dataset.name;
  state.encryptionModel = opt.dataset.encryption;
  state.pswId = dom.pswId.value.trim();
  state.runtimeUrl = dom.runtimeUrl.value.trim().replace(/\/$/, '') || 'http://localhost:8088';
  state.facilityId = dom.facilityId.value.trim();
  state.floorId = dom.floorId.value;

  if (!state.pswId) { showMsg(dom.setupMessage, I18N.t('error.signin_failed'), 'error'); return; }
  if (!(await checkServer())) { showMsg(dom.setupMessage, I18N.t('setup.unreachable'), 'error'); return; }

  try {
    const body = { tenant_id: state.tenantId, psw_id: state.pswId, method: dom.authMethod.value };
    if (state.facilityId) body.facility_id = state.facilityId;
    if (state.floorId) body.floor_id = state.floorId;

    const auth = await apiPost('/v1/auth/signin', body);
    state.authToken = auth.token;
    state.consentToken = auth.consent_token || '';
    state.facilityId = auth.facility_id || state.facilityId;
    state.floorId = auth.floor_id || state.floorId;
    state.floorPlans = auth.floor_plans || [];
    persistSession();
    hide(dom.setupCard); show(dom.todayCard); show(dom.auditCard);
    dom.pswLabel.textContent = `${state.pswId}${state.floorId ? ' · Floor ' + state.floorId : ''}`;
    if (state.floorPlans.length > 0) {
      renderFloorPlans();
      startCallbellPolling();
    }
    await loadVisits();
    await loadAudit();
  } catch (e) {
    showMsg(dom.setupMessage, `${I18N.t('error.signin_failed')}: ${e.message}`, 'error');
  }
}

function persistSession() {
  try {
    localStorage.setItem('openclinical.session', JSON.stringify({
      runtimeUrl: state.runtimeUrl, tenantId: state.tenantId, tenantName: state.tenantName,
      encryptionModel: state.encryptionModel, pswId: state.pswId,
      authToken: state.authToken, consentToken: state.consentToken,
      facilityId: state.facilityId, floorId: state.floorId, floorPlans: state.floorPlans,
    }));
  } catch (e) {}
}

function restoreSession() {
  try {
    const raw = localStorage.getItem('openclinical.session');
    if (!raw) return false;
    const sess = JSON.parse(raw);
    if (!sess.tenantId || !sess.pswId || !sess.authToken) return false;
    Object.assign(state, sess);
    dom.runtimeUrl.value = sess.runtimeUrl;
    dom.pswId.value = sess.pswId;
    if (sess.facilityId) dom.facilityId.value = sess.facilityId;
    if (sess.floorId) dom.floorId.value = sess.floorId;
    if (sess.floorPlans) state.floorPlans = sess.floorPlans;
    return true;
  } catch (e) { return false; }
}

function signOut() {
  try { localStorage.removeItem('openclinical.session'); } catch (e) {}
  location.reload();
}

// -- visits ----------------------------------------------------------------

async function loadVisits() {
  dom.visitList.innerHTML = `<div class="summary-box">${I18N.t('today.loading')}</div>`;
  try {
    const data = await apiGet(`/v1/visits/today?psw_id=${encodeURIComponent(state.pswId)}`);
    renderVisits(data.visits || []);
  } catch (e) {
    dom.visitList.innerHTML = `<div class="summary-box">${I18N.t('error.load_visits')}: ${h(e.message)}</div>`;
  }
}

function renderVisits(visits) {
  if (!visits.length) {
    dom.visitList.innerHTML = `<div class="summary-box">${I18N.t('today.no_visits')}</div>`;
    return;
  }
  dom.visitList.innerHTML = visits.map(v => `
    <div class="visit-item" data-visit-id="${h(v.id)}">
      <div class="visit-time">${h(v.scheduled_start)} – ${h(v.scheduled_end)}</div>
      <div class="visit-client">${h(v.client_name)}</div>
      <div class="visit-meta">${h(v.address || '')} · ${h(v.service_type || '')}</div>
    </div>
  `).join('');
  for (const item of dom.visitList.querySelectorAll('.visit-item')) {
    item.addEventListener('click', () => openVisit(item.dataset.visitId));
  }
}

async function openVisit(visitId) {
  try {
    const visit = await apiGet(`/v1/visits/${encodeURIComponent(visitId)}`);
    state.currentVisit = visit;
    state.visitClockIn = new Date().toISOString();

    dom.visitClientLabel.textContent = visit.client_name;
    dom.visitAddress.textContent = visit.address || '';
    dom.visitStatusBadge.textContent = I18N.t('visit.in_progress');

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(pos => {
        const lat = pos.coords.latitude.toFixed(6), lng = pos.coords.longitude.toFixed(6);
        dom.visitGps.textContent = `📍 ${lat}, ${lng}`;
        apiPost('/v1/visits/clock-in', {
          visit_id: visitId, psw_id: state.pswId,
          gps_lat: parseFloat(lat), gps_lng: parseFloat(lng), timestamp: state.visitClockIn,
        }).catch(() => {});
      }, err => { dom.visitGps.textContent = `📍 GPS unavailable (${err.message})`; });
    } else { dom.visitGps.textContent = '📍 GPS not supported'; }

    hide(dom.todayCard); show(dom.visitCard);
    setInterval(() => {
      if (!state.visitClockIn) return;
      const elapsed = Math.floor((Date.now() - new Date(state.visitClockIn).getTime()) / 1000);
      const hh = Math.floor(elapsed / 3600), mm = Math.floor((elapsed % 3600) / 60), ss = elapsed % 60;
      dom.visitClockTime.textContent = `${String(hh).padStart(2,'0')}:${String(mm).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
    }, 1000);
  } catch (e) {
    showMsg(dom.setupMessage, `${I18N.t('error.open_visit')}: ${e.message}`, 'error');
  }
}

// -- voice dictation --------------------------------------------------------

function initVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { dom.voiceBtn.disabled = true; dom.voiceStatus.textContent = I18N.t('visit.voice_unsupported'); return; }
  state.recognition = new SR();
  state.recognition.continuous = true;
  state.recognition.interimResults = true;
  state.recognition.lang = I18N.locale === 'fr' ? 'fr-CA' : 'en-US';

  let finalTranscript = '';
  state.recognition.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) finalTranscript += event.results[i][0].transcript + ' ';
      else interim += event.results[i][0].transcript;
    }
    const notesEl = document.getElementById('notes');
    notesEl.value = (notesEl.value || '') + (finalTranscript || '') + interim;
    if (finalTranscript) finalTranscript = '';
  };
  state.recognition.onerror = (event) => { dom.voiceStatus.textContent = `${I18N.t('visit.voice_error')}: ${event.error}`; stopVoice(); };
  state.recognition.onend = () => {
    if (state.recognizing) { try { state.recognition.start(); } catch (e) {} }
    else {
      dom.voiceBtn.classList.remove('recording');
      dom.voiceBtnText.textContent = I18N.t('visit.start_dictation');
      dom.voiceStatus.textContent = '';
    }
  };
}

function startVoice() {
  if (!state.recognition) return;
  // Update recognition language to match current locale
  state.recognition.lang = I18N.locale === 'fr' ? 'fr-CA' : 'en-US';
  state.recognizing = true;
  dom.voiceBtn.classList.add('recording');
  dom.voiceBtnText.textContent = I18N.t('visit.stop_dictation');
  dom.voiceStatus.textContent = I18N.t('visit.listening');
  try { state.recognition.start(); } catch (e) { dom.voiceStatus.textContent = e.message; stopVoice(); }
}

function stopVoice() {
  state.recognizing = false;
  if (state.recognition) { try { state.recognition.stop(); } catch (e) {} }
  dom.voiceBtn.classList.remove('recording');
  dom.voiceBtnText.textContent = I18N.t('visit.start_dictation');
  dom.voiceStatus.textContent = '';
}

// -- complete visit ---------------------------------------------------------

async function completeVisit() {
  if (!state.currentVisit) return;

  const notesSanitized = sanitize(document.getElementById('notes').value);
  if (notesSanitized.flagged) {
    showMsg(dom.visitMessage, 'Prompt-injection patterns detected in notes — content sanitized before AI processing.', 'info');
  }

  dom.completeVisitBtn.disabled = true;
  dom.completeVisitBtn.textContent = 'Generating…';

  try {
    const res = await apiPost('/v1/inference', {
      tenant_id: state.tenantId, model_id: 'psw-shift-handoff',
      patient_id: state.currentVisit.client_id, consent_token: state.consentToken,
      inputs: {
        resident_id: state.currentVisit.client_id, psw_id: state.pswId,
        visit_id: state.currentVisit.id, timestamp: new Date().toISOString(),
        notes: notesSanitized.text,
        observations: {
          bp: document.getElementById('bp').value || null,
          hr: document.getElementById('hr').value || null,
          temp_c: document.getElementById('temp').value || null,
          spo2: document.getElementById('spo2').value ? `${document.getElementById('spo2').value}%` : null,
          pain: document.getElementById('pain').value || null,
          meal_pct: document.getElementById('meal').value || null,
          ambulation: document.getElementById('ambulation').value || null,
          mood: document.getElementById('mood').value || null,
        },
      },
    });

    // Clock out
    await apiPost('/v1/visits/clock-out', {
      visit_id: state.currentVisit.id, psw_id: state.pswId,
      timestamp: new Date().toISOString(),
      family_visible_note: sanitize(document.getElementById('family-visible').value).text,
    });

    renderResult(res);
    await loadAudit();
  } catch (e) {
    showMsg(dom.visitMessage, `${I18N.t('error.generate')}: ${e.message}`, 'error');
  } finally {
    dom.completeVisitBtn.disabled = false;
    dom.completeVisitBtn.textContent = I18N.t('visit.complete');
  }
}

function renderResult(data) {
  const handoff = data.outputs?.shift_handoff || {};
  const concerns = handoff.concerns || [];

  dom.resultContent.innerHTML = `
    <div class="result-section"><h3>${I18N.t('result.summary')}</h3>
      <div class="summary-box">${h(handoff.summary || I18N.t('result.no_summary'))}</div></div>
    <div class="result-section"><h3>${I18N.t('result.concerns')}</h3>
      ${concerns.length ? concerns.map(c => `<div class="concern ${h(c.severity)}"><span class="severity">${h(c.severity)}</span> <strong>${h(c.type)}</strong>: ${h(c.detail)}</div>`).join('') : `<div class="summary-box">${I18N.t('result.no_concerns')}</div>`}</div>
    <div class="result-section"><h3>${I18N.t('result.audit')}</h3>
      <div class="summary-box"><code>inference_id: ${h(data.inference_id)}</code><br><code>latency: ${data.latency_ms}ms</code></div></div>
  `;
  dom.resultClientLabel.textContent = state.currentVisit.client_name;
  hide(dom.visitCard); show(dom.resultCard);
}

function resetVisits() {
  state.currentVisit = null; state.visitClockIn = null;
  hide(dom.visitCard); hide(dom.resultCard); show(dom.todayCard);
  for (const id of ['bp','hr','temp','spo2','pain','meal','ambulation','mood','notes','family-visible']) {
    const el = document.getElementById(id); if (el) el.value = '';
  }
  hide(dom.visitMessage); if (dom.visitGps) dom.visitGps.textContent = '';
  loadVisits();
}

// -- audit ------------------------------------------------------------------

async function loadAudit() {
  try {
    const res = await apiGet(`/audit/events?tenant_id=${encodeURIComponent(state.tenantId)}&limit=10`);
    const events = res.events || [];
    dom.auditContent.innerHTML = events.length
      ? events.map(e => `<div class="audit-event"><span class="badge ${h(e.event_type)}">${h(e.event_type)}</span> <code>${h(e.timestamp)}</code> · ${h(e.model_id || e.event_type)}</div>`).join('')
      : `<div class="summary-box">${I18N.t('audit.none')}</div>`;
  } catch (e) {
    dom.auditContent.innerHTML = `<div class="summary-box">${I18N.t('error.audit_unavailable')}: ${h(e.message)}</div>`;
  }
}

// -- connectors -------------------------------------------------------------

const CONNECTORS = [
  { name: 'Epic (FHIR R4)', type: 'EHR', status: 'planned' },
  { name: 'Cerner / Oracle Health', type: 'EHR', status: 'planned' },
  { name: 'Meditech Expanse', type: 'EHR', status: 'planned' },
  { name: 'Athenahealth', type: 'EHR', status: 'planned' },
  { name: 'PointClickCare', type: 'LTC EHR', status: 'in-development' },
  { name: 'AlayaCare', type: 'Home Care', status: 'in-development' },
  { name: 'FHIR R4 (native)', type: 'Standard', status: 'available' },
  { name: 'HL7v2 (MLLP)', type: 'Standard', status: 'in-development' },
  { name: 'DICOMweb', type: 'Imaging', status: 'planned' },
  { name: 'Twist Bioscience', type: 'Synthesis', status: 'available' },
  { name: 'IDT (Integrated DNA Tech)', type: 'Synthesis', status: 'available' },
  { name: 'GenScript', type: 'Synthesis', status: 'available' },
  { name: 'Benchling', type: 'Lab Informatics', status: 'community' },
  { name: 'REDCap', type: 'Research', status: 'community' },
  { name: 'SMART on FHIR', type: 'App Platform', status: 'planned' },
  { name: 'OpenMRS', type: 'Open Source EHR', status: 'community' },
  { name: 'Oscar EMR', type: 'Canadian EMR', status: 'planned' },
  { name: 'Telus Health (MedAccess)', type: 'Canadian EMR', status: 'planned' },
];

function renderConnectors() {
  const grid = document.getElementById('connector-grid');
  grid.innerHTML = CONNECTORS.map(c => `
    <div class="connector-card">
      <div class="connector-name">${h(c.name)}</div>
      <div class="connector-type">${h(c.type)}</div>
      <span class="connector-status ${c.status}">${I18N.t('connectors.' + c.status) || c.status}</span>
    </div>
  `).join('');
}

// -- business portal --------------------------------------------------------

async function submitBusinessApp() {
  const org = document.getElementById('biz-org').value.trim();
  const email = document.getElementById('biz-email').value.trim();
  if (!org || !email) {
    showMsg(document.getElementById('biz-message'), I18N.t('business.form_error'), 'error');
    return;
  }

  const sub = document.getElementById('biz-submit');
  sub.disabled = true; sub.textContent = 'Submitting…';

  try {
    await fetch(`${state.runtimeUrl}/v1/business/apply`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        org_name: org, contact_email: email,
        org_type: document.getElementById('biz-type').value,
        estimated_volume: document.getElementById('biz-tier').value,
      }),
    });
    showMsg(document.getElementById('biz-message'), I18N.t('business.form_success'), 'success');
    document.getElementById('biz-org').value = '';
    document.getElementById('biz-email').value = '';
  } catch (e) {
    showMsg(document.getElementById('biz-message'), `${I18N.t('business.form_error')}: ${e.message}`, 'error');
  } finally {
    sub.disabled = false; sub.textContent = I18N.t('business.form_submit');
  }
}

// -- tab navigation ---------------------------------------------------------

function switchTab(name) {
  for (const panel of document.querySelectorAll('.tab-panel')) panel.classList.remove('active');
  for (const btn of document.querySelectorAll('[data-tab]')) btn.classList.remove('active');
  const panel = document.getElementById(`panel-${name}`);
  if (panel) panel.classList.add('active');
  const button = document.querySelector(`[data-tab="${name}"]`);
  if (button) button.classList.add('active');
}

// -- biology news -----------------------------------------------------------

async function loadBioNews() {
  try {
    const res = await fetch(`${state.runtimeUrl}/v1/bio-news`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderBioNews(data);
  } catch (e) {
    console.warn('Bio news fetch failed:', e.message);
  }
}

function renderBioNews(data) {
  // Top stories
  const storiesEl = document.getElementById('news-stories');
  if (storiesEl && data.top_stories) {
    storiesEl.innerHTML = data.top_stories.map(s => `
      <div class="news-card story">
        <div class="news-meta">
          <span class="news-source">${h(s.source)}</span>
          <span class="news-date">${h(s.date)}</span>
          <span class="badge" style="background:var(--brand-crimson-bg);color:var(--brand-crimson-dark)">${h((data.categories || {})[s.category] || s.category)}</span>
        </div>
        <div class="news-title">${h(s.title)}</div>
        <div class="news-summary">${h(s.summary)}</div>
      </div>
    `).join('');
  }

  // Companies to watch
  const companiesEl = document.getElementById('news-companies');
  if (companiesEl && data.companies_to_watch) {
    companiesEl.innerHTML = data.companies_to_watch.map(c => `
      <div class="company-card">
        <div class="company-name">${h(c.name)}</div>
        <div class="company-location">${h(c.location)}</div>
        <div class="company-focus"><strong>Focus:</strong> ${h(c.focus)}</div>
        <div class="company-work">${h(c.what_they_are_working_on)}</div>
        <div class="company-stage">${h(c.stage)}</div>
      </div>
    `).join('');
  }

  // What to look forward to
  const upcomingEl = document.getElementById('news-upcoming');
  if (upcomingEl && data.what_to_look_forward_to) {
    upcomingEl.innerHTML = data.what_to_look_forward_to.map(u => {
      const typeLabels = { conference: '📅 Conference', regulatory: '⚖ Regulatory', milestone: '🎯 Milestone' };
      return `
        <div class="news-card upcoming">
          <div class="news-meta">
            <span class="news-date">${h(u.date)}</span>
            <span class="badge">${typeLabels[u.type] || u.type}</span>
          </div>
          <div class="news-title">${h(u.event)}</div>
          <div class="news-summary">${h(u.description)}</div>
        </div>
      `;
    }).join('');
  }
}

// -- care plan display + call bell (v0.5.0) -----------------------------------

function renderFloorPlans() {
  // Show a summary of care plans loaded for this floor
  const summary = document.createElement('div');
  summary.className = 'summary-box floor-plans-summary';
  summary.id = 'floor-plans-summary';
  const highRisk = state.floorPlans.filter(p => p.fall_risk === 'high').length;
  const dnrs = state.floorPlans.filter(p => p.dnr_status).length;
  summary.innerHTML = [
    `${I18N.t('today.plans_loaded')}: ${state.floorPlans.length} ${I18N.t('today.residents')}`,
    highRisk > 0 ? `${highRisk} ${I18N.t('today.high_fall_risk')}` : '',
    dnrs > 0 ? `${dnrs} DNR` : '',
  ].filter(Boolean).join(' · ');
  const setupCard = $('setup-card');
  if (setupCard && setupCard.parentNode) {
    setupCard.parentNode.insertBefore(summary, $('today-card'));
  }

  // Render care plan cards for quick reference
  const planCards = state.floorPlans.map(p => `
    <div class="careplan-minicard" data-plan-id="${h(p.id)}" data-room="${h(p.room_number)}">
      <div class="careplan-minicard-header">
        <strong>${h(p.resident_name)}</strong>
        <span class="badge room">Room ${h(p.room_number)}</span>
      </div>
      <div class="careplan-minicard-body">
        <span class="careplan-tag fall-${p.fall_risk}">${I18N.t('careplan.fall_risk')}: ${h(p.fall_risk)}</span>
        ${p.conditions.slice(0, 2).map(c => `<span class="careplan-tag">${h(c)}</span>`).join('')}
        ${p.behavioral_flags.length > 0 ? `<span class="careplan-tag flag">⚠ ${h(p.behavioral_flags[0])}</span>` : ''}
      </div>
      <div class="careplan-minicard-footer">
        ${p.mobility ? `<span>🚶 ${h(p.mobility)}</span>` : ''}
        ${p.communication ? `<span>💬 ${h(p.communication)}</span>` : ''}
      </div>
    </div>
  `).join('');

  const planEl = document.createElement('div');
  planEl.id = 'floor-plans-grid';
  planEl.className = 'careplan-grid';
  planEl.innerHTML = planCards;
  const todayCard = $('today-card');
  if (todayCard && todayCard.parentNode) {
    todayCard.parentNode.insertBefore(planEl, todayCard);
  }
}

async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) { console.log('[sw] not supported'); return; }
  try {
    const registration = await navigator.serviceWorker.register('/psw/sw.js', { scope: '/psw/' });
    state.serviceWorker = registration;
    console.log('[sw] registered, scope:', registration.scope);

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      const perm = await Notification.requestPermission();
      console.log('[sw] notification permission:', perm);
    }

    // Send notification subscription to server (if push is configured)
    if (registration.pushManager) {
      try {
        const sub = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: null, // MVP: use polling; push keys configured later
        });
        console.log('[sw] push subscribed');
      } catch (e) {
        console.log('[sw] push subscription skipped (no VAPID key configured):', e.message);
      }
    }
  } catch (e) {
    console.warn('[sw] registration failed:', e.message);
  }
}

function startCallbellPolling() {
  if (!state.facilityId || !state.floorId) return;
  if (state.callbellPolling) clearInterval(state.callbellPolling);

  // Poll every 5 seconds for call bell events
  state.callbellPolling = setInterval(async () => {
    try {
      const res = await apiGet(`/v1/callbell/queue?facility_id=${encodeURIComponent(state.facilityId)}&floor_id=${encodeURIComponent(state.floorId)}`);
      const events = res.events || [];
      for (const event of events) {
        showCallbellNotification(event);
      }
    } catch (e) {
      // Silently skip — server may be restarting
    }
  }, 5000);
}

function showCallbellNotification(event) {
  const brief = event.brief || event.matched_plan || {};
  const residentName = brief.resident_name || event.matched_plan?.resident_name || 'Unknown resident';
  const room = brief.room_number || event.room_number || '?';
  const eventLabel = { call_bell: 'Call Bell', bathroom_alert: 'Bathroom', wander_alert: 'Wander', emergency: 'EMERGENCY' }[event.event_type] || event.event_type;

  const card = $('callbell-notification');
  const msg = $('callbell-msg');
  const detail = $('callbell-detail');

  msg.textContent = `🔔 ${eventLabel} — ${residentName} (Room ${room})`;
  const details = [];
  if (brief.conditions && brief.conditions.length > 0) details.push(brief.conditions.slice(0, 2).join(', '));
  if (brief.mobility) details.push(brief.mobility);
  if (brief.fall_risk === 'high') details.push('⚠ High fall risk');
  if (brief.behavioral_flags && brief.behavioral_flags.length > 0) details.push(`Flag: ${brief.behavioral_flags[0]}`);
  if (brief.communication) details.push(brief.communication);
  detail.textContent = details.join(' · ');

  card.classList.remove('hidden');
  card.classList.add('callbell-active');

  // Vibrate if supported
  if (navigator.vibrate) {
    navigator.vibrate([200, 100, 200, 100, 400]);
  }

  // Show browser notification if permission granted
  if ('Notification' in window && Notification.permission === 'granted' && state.serviceWorker) {
    state.serviceWorker.showNotification(`${eventLabel}: ${residentName}`, {
      body: `Room ${room} · ${brief.conditions ? brief.conditions.slice(0, 1).join(', ') : ''}`,
      icon: '/psw/icon-192.png',
      badge: '/psw/icon-72.png',
      tag: `callbell-${room}`,
      requireInteraction: true,
      vibrate: [200, 100, 200, 100, 400],
      data: { url: `/psw/`, room: room, resident_name: residentName, event_type: event.event_type },
    });
  }
}

// Dismiss call bell notification
function dismissCallbell() {
  const card = $('callbell-notification');
  card.classList.add('hidden');
  card.classList.remove('callbell-active');
}

// -- wiring -----------------------------------------------------------------

async function init() {
  // Restore theme
  const savedTheme = (() => { try { return localStorage.getItem('openclinical.theme'); } catch (e) { return null; } })();
  applyTheme(savedTheme || 'light');

  // Restore language
  const savedLang = (() => { try { return localStorage.getItem('openclinical.lang'); } catch (e) { return null; } })();
  await I18N.load(savedLang || 'en');
  I18N.applyToDOM();

  // Load connectors (always visible on Connect tab)
  renderConnectors();

  // Wire theme toggle
  document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
  for (const b of document.querySelectorAll('[data-theme-choice]')) {
    b.addEventListener('click', () => applyTheme(b.dataset.themeChoice));
  }

  // Wire language switcher
  for (const b of document.querySelectorAll('[data-lang-choice]')) {
    b.addEventListener('click', async () => {
      await I18N.load(b.dataset.langChoice);
      I18N.applyToDOM();
      try { localStorage.setItem('openclinical.lang', I18N.locale); } catch (e) {}
      renderConnectors(); // re-render with new language
    });
  }

  // Wire tab navigation
  for (const b of document.querySelectorAll('[data-tab]')) {
    b.addEventListener('click', () => switchTab(b.dataset.tab));
  }

  // Wire PSW flow
  dom.signinBtn.addEventListener('click', signIn);
  dom.refreshVisitsBtn.addEventListener('click', loadVisits);
  dom.completeVisitBtn.addEventListener('click', completeVisit);
  dom.nextVisitBtn.addEventListener('click', resetVisits);
  dom.voiceBtn.addEventListener('click', () => { if (state.recognizing) stopVoice(); else startVoice(); });
  document.getElementById('settings-signout').addEventListener('click', signOut);
  document.getElementById('biz-submit').addEventListener('click', submitBusinessApp);
  document.getElementById('callbell-dismiss').addEventListener('click', dismissCallbell);

  // Register service worker for push notifications (v0.5.0)
  registerServiceWorker();

  // Periodic health check
  setInterval(checkServer, 5000);

  // Init voice
  initVoice();

  // Load tenants + check server + bio news
  checkServer();
  loadTenants();
  loadBioNews();

  // Restore session if available
  if (restoreSession()) {
    hide(dom.setupCard); show(dom.todayCard); show(dom.auditCard);
    dom.pswLabel.textContent = state.pswId;
    checkServer(); loadVisits(); loadAudit();
  }
}

document.addEventListener('DOMContentLoaded', init);
