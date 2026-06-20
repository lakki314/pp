const state = {
  selections: [],
  environments: [],
  currentJobId: null,
  pollTimer: null,
  jobComplete: false,
  modalJvms: [],
  selectedJvm: null,
};

const elements = {
  addBtn: document.getElementById('addBtn'),
  removeSelectedBtn: document.getElementById('removeSelectedBtn'),
  restartBtn: document.getElementById('restartBtn'),
  selectionBody: document.getElementById('selectionBody'),
  selectAll: document.getElementById('selectAll'),
  totalCount: document.getElementById('totalCount'),
  envCount: document.getElementById('envCount'),
  lastJob: document.getElementById('lastJob'),
  payloadPreview: document.getElementById('payloadPreview'),
  portalState: document.getElementById('portalState'),
  userDisplay: document.getElementById('userDisplay'),
  modalBackdrop: document.getElementById('modalBackdrop'),
  closeModalBtn: document.getElementById('closeModalBtn'),
  cancelModalBtn: document.getElementById('cancelModalBtn'),
  addForm: document.getElementById('addForm'),
  envSelect: document.getElementById('envSelect'),
  jvmSearch: document.getElementById('jvmSearch'),
  jvmToggle: document.getElementById('jvmToggle'),
  jvmSelect: document.getElementById('jvmSelect'),
  jvmDropdown: document.getElementById('jvmDropdown'),
  jvmSearchHint: document.getElementById('jvmSearchHint'),
  modalMessage: document.getElementById('modalMessage'),
  runtimePanel: document.getElementById('runtimePanel'),
  runtimeSubtitle: document.getElementById('runtimeSubtitle'),
  jobPill: document.getElementById('jobPill'),
  runningBtn: document.getElementById('runningBtn'),
  refreshStatusBtn: document.getElementById('refreshStatusBtn'),
  copyStdoutBtn: document.getElementById('copyStdoutBtn'),
  terminal: document.getElementById('terminal'),
  artifactsBox: document.getElementById('artifactsBox'),
  artifactsPre: document.getElementById('artifactsPre'),
  failureBox: document.getElementById('failureBox'),
  failurePre: document.getElementById('failurePre'),
  activeJobsBody: document.getElementById('activeJobsBody'),
  refreshActiveJobsBtn: document.getElementById('refreshActiveJobsBtn'),
  historyBody: document.getElementById('historyBody'),
  refreshHistoryBtn: document.getElementById('refreshHistoryBtn'),
  toast: document.getElementById('toast'),
};

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[char]));
}

function showToast(message, type = '') {
  elements.toast.textContent = message;
  elements.toast.className = `toast ${type}`.trim();
  elements.toast.classList.remove('hidden');
  window.setTimeout(() => elements.toast.classList.add('hidden'), 4200);
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 401) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/login?next=${next}`;
    throw new Error('Authentication required');
  }
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : { raw: await response.text() };
  if (!response.ok) {
    const details = data.details ? ` ${JSON.stringify(data.details)}` : '';
    throw new Error(`${data.error || 'Request failed'}${details}`);
  }
  return data;
}

function openModal() {
  elements.modalBackdrop.classList.remove('hidden');
  elements.envSelect.value = '';
  resetJvmSelect('Select JVM name');
  hideModalMessage();
  elements.envSelect.focus();
}

function closeModal() { elements.modalBackdrop.classList.add('hidden'); }
function showModalMessage(message) { elements.modalMessage.textContent = message; elements.modalMessage.classList.remove('hidden'); }
function hideModalMessage() { elements.modalMessage.textContent = ''; elements.modalMessage.classList.add('hidden'); }

function jvmLabel(jvm, env = elements.envSelect.value) {
  const host = jvm.host || '';
  return `${jvm.name} | ${host || '-'} | ${String(env || '').toUpperCase()}`;
}

function closeJvmDropdown() {
  if (!elements.jvmDropdown) return;
  elements.jvmDropdown.classList.add('hidden');
  elements.jvmSearch.setAttribute('aria-expanded', 'false');
}

function openJvmDropdown() {
  if (elements.jvmSearch.disabled || !elements.jvmDropdown) return;
  renderJvmOptions(elements.jvmSearch.value);
  elements.jvmDropdown.classList.remove('hidden');
  elements.jvmSearch.setAttribute('aria-expanded', 'true');
}

function selectJvm(jvm) {
  state.selectedJvm = jvm;
  elements.jvmSearch.value = jvmLabel(jvm);
  elements.jvmSelect.value = jvm.name;
  elements.jvmSelect.dataset.host = jvm.host || '';
  closeJvmDropdown();
  hideModalMessage();
}

function resetJvmSelect(text) {
  state.modalJvms = [];
  state.selectedJvm = null;
  elements.jvmSearch.value = '';
  elements.jvmSearch.placeholder = 'Select environment first';
  elements.jvmSearch.disabled = true;
  elements.jvmSearch.setAttribute('aria-expanded', 'false');
  if (elements.jvmToggle) elements.jvmToggle.disabled = true;
  elements.jvmSelect.value = '';
  elements.jvmSelect.dataset.host = '';
  if (elements.jvmDropdown) {
    elements.jvmDropdown.innerHTML = `<div class="combo-empty">${escapeHtml(text)}</div>`;
    elements.jvmDropdown.classList.add('hidden');
  }
  elements.jvmSearchHint.textContent = '';
  elements.jvmSearchHint.classList.add('hidden');
}

function renderJvmOptions(query = '') {
  const normalizedQuery = query.trim().toLowerCase();
  const env = elements.envSelect.value;
  if (state.selectedJvm && query !== jvmLabel(state.selectedJvm)) {
    state.selectedJvm = null;
    elements.jvmSelect.value = '';
    elements.jvmSelect.dataset.host = '';
  }
  const filtered = state.modalJvms.filter(jvm => {
    const label = jvmLabel(jvm, env).toLowerCase();
    return !normalizedQuery || label.includes(normalizedQuery);
  });
  const maxOptions = 200;
  const visible = filtered.slice(0, maxOptions);
  if (!elements.jvmDropdown) return;
  if (visible.length === 0) {
    elements.jvmDropdown.innerHTML = '<div class="combo-empty">No matching JVMs</div>';
  } else {
    elements.jvmDropdown.innerHTML = visible.map(jvm => {
      const label = jvmLabel(jvm, env);
      return `<button type="button" class="combo-option" role="option" data-name="${escapeHtml(jvm.name)}" data-host="${escapeHtml(jvm.host || '')}">${escapeHtml(label)}</button>`;
    }).join('');
  }
  const total = state.modalJvms.length;
  const shown = visible.length;
  const matched = filtered.length;
  if (total > maxOptions || normalizedQuery) {
    elements.jvmSearchHint.textContent = normalizedQuery
      ? `Showing ${shown} of ${matched} matching JVMs. Type more to narrow the list.`
      : `Showing first ${shown} of ${total} JVMs. Type in the dropdown to narrow the list.`;
    elements.jvmSearchHint.classList.remove('hidden');
  } else {
    elements.jvmSearchHint.textContent = '';
    elements.jvmSearchHint.classList.add('hidden');
  }
}

function selectionKey(item) { return `${item.environment}::${item.host || ''}::${item.jvm_name}`; }

function buildPayloadPreview() {
  const payload = { jvm_restart: { ritm_number: 'RITMTEST', envs: {} } };
  state.selections.forEach(item => {
    const env = String(item.environment || '').toLowerCase();
    const hostname = item.host || item.jvm_name;
    if (!payload.jvm_restart.envs[env]) payload.jvm_restart.envs[env] = { hosts: {} };
    payload.jvm_restart.envs[env].hosts[hostname] = item.jvm_name;
  });
  return payload;
}

function renderTable() {
  if (state.selections.length === 0) {
    elements.selectionBody.innerHTML = `<tr class="empty-row"><td colspan="4"><div class="empty-state"><div class="empty-icon">☁</div><strong>No JVM selected</strong><span>Click Add to choose an environment and JVM name.</span></div></td></tr>`;
    elements.selectAll.checked = false;
    elements.selectAll.disabled = true;
    elements.restartBtn.disabled = true;
    elements.removeSelectedBtn.disabled = true;
  } else {
    elements.selectionBody.innerHTML = state.selections.map((item, index) => `
      <tr>
        <td class="checkbox-col"><input type="checkbox" class="row-check" data-index="${index}" aria-label="Select ${escapeHtml(item.jvm_name)}"></td>
        <td><button class="link-button" data-remove-index="${index}">Remove</button></td>
        <td><span class="env-badge">${escapeHtml(item.environment)}</span></td>
        <td>${escapeHtml(item.jvm_name)}</td>
      </tr>`).join('');
    elements.selectAll.disabled = false;
    elements.restartBtn.disabled = false;
  }
  const envs = new Set(state.selections.map(item => item.environment));
  elements.totalCount.textContent = String(state.selections.length);
  elements.envCount.textContent = String(envs.size);
  elements.payloadPreview.textContent = JSON.stringify(buildPayloadPreview(), null, 2);
}

function syncRemoveSelectedButton() {
  const checkedCount = document.querySelectorAll('.row-check:checked').length;
  elements.removeSelectedBtn.disabled = checkedCount === 0;
}

async function loadSession() {
  if (!elements.userDisplay) return;
  const data = await apiFetch('/api/session');
  elements.userDisplay.textContent = data.display_name || data.username || 'Authenticated user';
}

async function loadEnvironments() {
  const data = await apiFetch('/api/environments');
  state.environments = data.environments || [];
  elements.envSelect.innerHTML = '<option value="">Select environment</option>' + state.environments.map(env => `<option value="${escapeHtml(env)}">${escapeHtml(env)}</option>`).join('');
}

async function loadJvmsForEnv(env) {
  resetJvmSelect('Loading JVM names...');
  hideModalMessage();
  try {
    const data = await apiFetch(`/api/jvms?env=${encodeURIComponent(env)}`);
    const jvms = data.jvms || [];
    if (jvms.length === 0) {
      resetJvmSelect('No JVMs found');
      showModalMessage(`No JVM names found for ${env}.`);
      return;
    }
    state.modalJvms = jvms;
    state.selectedJvm = null;
    elements.jvmSearch.disabled = false;
    if (elements.jvmToggle) elements.jvmToggle.disabled = false;
    elements.jvmSearch.placeholder = 'Search JVM name | UNIX host | environment';
    elements.jvmSearch.value = '';
    elements.jvmSelect.value = '';
    elements.jvmSelect.dataset.host = '';
    renderJvmOptions('');
    openJvmDropdown();
    elements.jvmSearch.focus();
  } catch (error) {
    resetJvmSelect('Unable to load JVMs');
    showModalMessage(error.message);
  }
}

function addSelection(environment, jvmName, host = '') {
  const item = { environment, host, jvm_name: jvmName };
  if (state.selections.some(existing => selectionKey(existing) === selectionKey(item))) {
    showModalMessage('This JVM is already added to the restart table.');
    return false;
  }
  state.selections.push(item);
  renderTable();
  showToast('JVM added to restart table.', 'success');
  return true;
}

function removeSelection(index) { state.selections.splice(index, 1); renderTable(); }
function removeCheckedSelections() {
  const checkedIndexes = Array.from(document.querySelectorAll('.row-check:checked')).map(input => Number(input.dataset.index));
  state.selections = state.selections.filter((_, index) => !checkedIndexes.includes(index));
  elements.selectAll.checked = false;
  renderTable();
}

function formatHistoryTime(value) {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function summarizeHistoryItems(items = []) {
  if (!items.length) return '—';
  return items.map(item => `${item.jvm_name} (${item.host || item.hostname || item.environment})`).join(', ');
}

async function loadActiveJobs() {
  if (!elements.activeJobsBody) return;
  try {
    const data = await apiFetch('/api/active-jobs');
    const activeJobs = data.active_jobs || [];
    if (activeJobs.length === 0) {
      elements.activeJobsBody.innerHTML = '<tr><td colspan="5">No users are currently executing jobs from this portal.</td></tr>';
      return;
    }
    elements.activeJobsBody.innerHTML = activeJobs.map(row => `
      <tr>
        <td>${escapeHtml(formatHistoryTime(row.created_at))}</td>
        <td>${escapeHtml(row.username || '—')}</td>
        <td>${row.job_id ? `#${escapeHtml(row.job_id)}` : '—'}</td>
        <td><span class="status-badge ${escapeHtml(row.status || 'unknown')}">${escapeHtml(row.status || 'unknown')}</span></td>
        <td>${escapeHtml(summarizeHistoryItems(row.selected_items || []))}</td>
      </tr>`).join('');
  } catch (error) {
    elements.activeJobsBody.innerHTML = `<tr><td colspan="5">Unable to load active jobs: ${escapeHtml(error.message)}</td></tr>`;
  }
}

async function loadHistory() {
  if (!elements.historyBody) return;
  try {
    const data = await apiFetch('/api/history');
    const history = data.history || [];
    if (history.length === 0) {
      elements.historyBody.innerHTML = '<tr><td colspan="6">No jobs have been launched from this portal yet.</td></tr>';
      return;
    }
    elements.historyBody.innerHTML = history.map(row => `
      <tr>
        <td>${escapeHtml(formatHistoryTime(row.created_at))}</td>
        <td>${escapeHtml(row.username || '—')}</td>
        <td>${row.job_id ? `#${escapeHtml(row.job_id)}` : '—'}</td>
        <td><span class="status-badge ${escapeHtml(row.status || 'unknown')}">${escapeHtml(row.status || 'unknown')}</span></td>
        <td>${escapeHtml(summarizeHistoryItems(row.selected_items || []))}</td>
        <td>${escapeHtml(row.failure_message || '')}</td>
      </tr>`).join('');
  } catch (error) {
    elements.historyBody.innerHTML = `<tr><td colspan="6">Unable to load history: ${escapeHtml(error.message)}</td></tr>`;
  }
}

function setRuntimeStatus(status, details = {}) {
  const normalized = status || 'unknown';
  elements.jobPill.textContent = normalized;
  elements.jobPill.className = `job-pill ${normalized}`;
  elements.runtimeSubtitle.textContent = details.elapsed ? `Job ${details.id || state.currentJobId} • elapsed ${details.elapsed}s` : `Job ${details.id || state.currentJobId}`;
  if (['successful', 'failed', 'error', 'canceled'].includes(normalized)) {
    elements.runningBtn.disabled = true;
    state.jobComplete = true;
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  } else {
    elements.runningBtn.disabled = false;
    state.jobComplete = false;
  }
}

async function fetchStdout(jobId) {
  const data = await apiFetch(`/api/jobs/${jobId}/stdout`);
  elements.terminal.textContent = data.stdout || '(No stdout returned yet.)';
  elements.terminal.scrollTop = elements.terminal.scrollHeight;
}

async function fetchArtifacts(jobId) {
  const data = await apiFetch(`/api/jobs/${jobId}/artifacts`);
  const artifacts = data.artifacts || {};
  elements.artifactsPre.textContent = JSON.stringify(artifacts, null, 2);
  elements.artifactsBox.classList.toggle('hidden', Object.keys(artifacts).length === 0);
}

async function refreshStatus() {
  if (!state.currentJobId) return;
  try {
    const status = await apiFetch(`/api/jobs/${state.currentJobId}/status`);
    setRuntimeStatus(status.status, status);
    await fetchStdout(state.currentJobId);
    if (status.status === 'successful') {
      elements.portalState.textContent = 'Successful';
      await fetchArtifacts(state.currentJobId);
      showToast('Restart job completed successfully.', 'success');
      await loadHistory();
      await loadActiveJobs();
    }
    if (['failed', 'error', 'canceled'].includes(status.status)) {
      elements.portalState.textContent = 'Failed';
      elements.failurePre.textContent = JSON.stringify({ status: status.status, job_explanation: status.job_explanation, result_traceback: status.result_traceback, artifacts: status.artifacts }, null, 2);
      elements.failureBox.classList.remove('hidden');
      await fetchArtifacts(state.currentJobId);
      showToast('Restart job failed. Review failure information and terminal output.', 'error');
      await loadHistory();
      await loadActiveJobs();
    }
  } catch (error) {
    elements.failurePre.textContent = error.message;
    elements.failureBox.classList.remove('hidden');
    showToast(error.message, 'error');
  }
}

async function launchRestart() {
  if (state.selections.length === 0) return;
  if (!window.confirm(`Launch JVM restart for ${state.selections.length} selected JVM(s)?`)) return;
  elements.restartBtn.disabled = true;
  elements.portalState.textContent = 'Launching';
  elements.runtimePanel.classList.remove('hidden');
  elements.artifactsBox.classList.add('hidden');
  elements.failureBox.classList.add('hidden');
  elements.terminal.textContent = 'Launching Ansible job template...';
  try {
    const result = await apiFetch('/api/restart', { method: 'POST', body: JSON.stringify({ items: state.selections }) });
    state.currentJobId = result.job_id;
    state.jobComplete = false;
    elements.lastJob.textContent = `#${state.currentJobId}`;
    elements.portalState.textContent = 'Running';
    setRuntimeStatus('running', { id: state.currentJobId });
    showToast(`Ansible job #${state.currentJobId} launched.`, 'success');
    await refreshStatus();
    await loadHistory();
    await loadActiveJobs();
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = window.setInterval(refreshStatus, 3500);
  } catch (error) {
    elements.restartBtn.disabled = state.selections.length === 0;
    elements.portalState.textContent = 'Launch failed';
    elements.terminal.textContent = error.message;
    elements.failurePre.textContent = error.message;
    elements.failureBox.classList.remove('hidden');
    showToast(error.message, 'error');
  }
}

function wireEvents() {
  elements.addBtn.addEventListener('click', openModal);
  elements.closeModalBtn.addEventListener('click', closeModal);
  elements.cancelModalBtn.addEventListener('click', closeModal);
  elements.modalBackdrop.addEventListener('click', event => { if (event.target === elements.modalBackdrop) closeModal(); });
  elements.envSelect.addEventListener('change', event => { const env = event.target.value; if (!env) { resetJvmSelect('Select JVM name'); return; } loadJvmsForEnv(env); });
  elements.jvmSearch.addEventListener('input', event => { renderJvmOptions(event.target.value); openJvmDropdown(); });
  elements.jvmSearch.addEventListener('focus', openJvmDropdown);
  if (elements.jvmToggle) {
    elements.jvmToggle.addEventListener('click', () => {
      if (elements.jvmDropdown.classList.contains('hidden')) openJvmDropdown(); else closeJvmDropdown();
    });
  }
  if (elements.jvmDropdown) {
    elements.jvmDropdown.addEventListener('click', event => {
      const button = event.target.closest('.combo-option');
      if (!button) return;
      selectJvm({ name: button.dataset.name, host: button.dataset.host || '' });
    });
  }
  document.addEventListener('click', event => {
    if (!event.target.closest('.combo-select')) closeJvmDropdown();
  });
  elements.addForm.addEventListener('submit', event => {
    event.preventDefault();
    const env = elements.envSelect.value;
    const jvmName = elements.jvmSelect.value;
    const host = elements.jvmSelect.dataset.host || jvmName;
    if (!env || !jvmName) { showModalMessage('Select both environment and JVM name from the dropdown list.'); return; }
    if (addSelection(env, jvmName, host)) closeModal();
  });
  elements.selectionBody.addEventListener('click', event => { const removeIndex = event.target.getAttribute('data-remove-index'); if (removeIndex !== null) removeSelection(Number(removeIndex)); });
  elements.selectionBody.addEventListener('change', syncRemoveSelectedButton);
  elements.selectAll.addEventListener('change', event => { document.querySelectorAll('.row-check').forEach(input => { input.checked = event.target.checked; }); syncRemoveSelectedButton(); });
  elements.removeSelectedBtn.addEventListener('click', removeCheckedSelections);
  elements.restartBtn.addEventListener('click', launchRestart);
  elements.refreshStatusBtn.addEventListener('click', refreshStatus);
  elements.copyStdoutBtn.addEventListener('click', async () => { await navigator.clipboard.writeText(elements.terminal.textContent || ''); showToast('Terminal output copied.', 'success'); });
  if (elements.refreshActiveJobsBtn) elements.refreshActiveJobsBtn.addEventListener('click', loadActiveJobs);
  if (elements.refreshHistoryBtn) elements.refreshHistoryBtn.addEventListener('click', loadHistory);
}

async function init() {
  wireEvents();
  renderTable();
  try {
    await loadSession();
    await loadEnvironments();
    await loadHistory();
    await loadActiveJobs();
    window.setInterval(loadActiveJobs, 15000);
    window.setInterval(loadHistory, 30000);
  } catch (error) {
    showToast(error.message, 'error');
  }
}

init();
