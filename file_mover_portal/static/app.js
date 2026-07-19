"use strict";

(function () {
  const context = document.getElementById("selection-context");
  const moveForm = document.getElementById("move-form");
  if (!context || !moveForm) return;

  const username = context.dataset.username || "anonymous";
  const maxSelection = Number.parseInt(context.dataset.maxSelection || "200", 10);
  const storageKey = `file-mover:selected:${username}`;
  const csrfToken = moveForm.querySelector('input[name="csrf_token"]').value;
  const checkboxes = Array.from(document.querySelectorAll(".file-check"));
  const selectAll = document.getElementById("select-all");
  const countElement = document.getElementById("selected-count");
  const moveButton = document.getElementById("move-button");
  const clearButton = document.getElementById("clear-selection");

  const confirmModal = document.getElementById("confirm-modal");
  const progressModal = document.getElementById("progress-modal");
  const completionModal = document.getElementById("completion-modal");
  const cancelMove = document.getElementById("cancel-move");
  const confirmMove = document.getElementById("confirm-move");
  const returnButton = document.getElementById("return-to-files");

  function loadSelection() {
    try {
      const parsed = JSON.parse(window.sessionStorage.getItem(storageKey) || "[]");
      return new Set(Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : []);
    } catch (_error) {
      return new Set();
    }
  }

  let selected = loadSelection();
  let running = false;
  let timerId = null;

  function saveSelection() {
    window.sessionStorage.setItem(storageKey, JSON.stringify(Array.from(selected)));
  }

  function setModal(modal, visible) {
    modal.hidden = !visible;
    document.body.classList.toggle("modal-open", visible);
  }

  function updatePageCheckboxes() {
    checkboxes.forEach((checkbox) => {
      checkbox.checked = selected.has(checkbox.value);
      checkbox.disabled = running;
    });
    if (selectAll) {
      selectAll.checked = checkboxes.length > 0 && checkboxes.every((checkbox) => checkbox.checked);
      selectAll.indeterminate = checkboxes.some((checkbox) => checkbox.checked) && !selectAll.checked;
      selectAll.disabled = running;
    }
  }

  function updateSummary() {
    const count = selected.size;
    countElement.textContent = String(count);
    moveButton.textContent = running ? "Move in progress…" : `Move selected files (${count})`;
    moveButton.disabled = running || count === 0;
    clearButton.disabled = running || count === 0;
  }

  function refreshUi() {
    updatePageCheckboxes();
    updateSummary();
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        "Accept": "application/json"
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({ error: "Unexpected server response" }));
    if (!response.ok) throw new Error(data.error || "Request failed");
    return data;
  }

  function elapsedText(startedAt) {
    const seconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  }

  function updateProgress(completed, total, moved, failed, filename) {
    const percent = total ? Math.round((completed / total) * 100) : 0;
    document.getElementById("progress-completed").textContent = String(completed);
    document.getElementById("progress-total").textContent = String(total);
    document.getElementById("progress-moved").textContent = String(moved);
    document.getElementById("progress-failed").textContent = String(failed);
    document.getElementById("progress-percent").textContent = `${percent}%`;
    document.getElementById("progress-bar").style.width = `${percent}%`;
    document.getElementById("current-file").textContent = filename || "Finalizing report…";
    document.getElementById("progress-message").textContent = completed < total ? "Files are being moved safely." : "Generating the Excel report and sending email.";
  }

  function showCompletion(summary) {
    document.getElementById("completion-batch").textContent = summary.batch_id;
    document.getElementById("completion-requested").textContent = String(summary.requested);
    document.getElementById("completion-moved").textContent = String(summary.moved);
    document.getElementById("completion-failed").textContent = String(summary.failed);
    document.getElementById("completion-email").textContent = summary.email_status.replaceAll("_", " ");
    document.getElementById("download-report").href = summary.download_url;

    const icon = document.getElementById("completion-icon");
    const title = document.getElementById("completion-title");
    icon.textContent = summary.failed === 0 ? "✓" : "!";
    icon.classList.toggle("warning", summary.failed > 0);
    title.textContent = summary.failed === 0 ? "Move completed successfully" : "Move completed with failures";

    const failurePanel = document.getElementById("failure-panel");
    const failureList = document.getElementById("failure-list");
    failureList.replaceChildren();
    const failures = summary.results.filter((item) => item.status === "FAILED");
    failurePanel.hidden = failures.length === 0;
    failures.slice(0, 20).forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `${item.filename} — ${item.message}`;
      failureList.appendChild(li);
    });
    if (failures.length > 20) {
      const li = document.createElement("li");
      li.textContent = `And ${failures.length - 20} more. See the Excel report.`;
      failureList.appendChild(li);
    }
    setModal(completionModal, true);
  }

  async function executeMove() {
    const filenames = Array.from(selected).sort();
    setModal(confirmModal, false);
    setModal(progressModal, true);
    running = true;
    refreshUi();

    const startedClock = Date.now();
    timerId = window.setInterval(() => {
      document.getElementById("progress-elapsed").textContent = elapsedText(startedClock);
    }, 1000);

    try {
      const batch = await postJson(context.dataset.startUrl, { selected_files: filenames });
      let completed = 0;
      let moved = 0;
      let failed = 0;
      updateProgress(0, filenames.length, 0, 0, filenames[0]);

      for (const filename of filenames) {
        document.getElementById("current-file").textContent = filename;
        const status = await postJson(context.dataset.fileUrl, { batch_id: batch.batch_id, filename });
        completed = status.completed;
        moved = status.moved;
        failed = status.failed;
        updateProgress(completed, filenames.length, moved, failed, filenames[completed] || "");
      }

      const summary = await postJson(context.dataset.completeUrl, { batch_id: batch.batch_id });
      selected.clear();
      saveSelection();
      refreshUi();
      setModal(progressModal, false);
      showCompletion(summary);
    } catch (error) {
      setModal(progressModal, false);
      window.alert(`The move could not be completed: ${error.message}`);
    } finally {
      running = false;
      if (timerId) window.clearInterval(timerId);
      timerId = null;
      refreshUi();
    }
  }

  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
      if (checkbox.checked) {
        if (!selected.has(checkbox.value) && selected.size >= maxSelection) {
          checkbox.checked = false;
          window.alert(`You can select a maximum of ${maxSelection} ZIP files per move.`);
          return;
        }
        selected.add(checkbox.value);
      } else {
        selected.delete(checkbox.value);
      }
      saveSelection();
      refreshUi();
    });
  });

  selectAll.addEventListener("change", function () {
    if (selectAll.checked) {
      const additional = checkboxes.filter((checkbox) => !selected.has(checkbox.value));
      if (selected.size + additional.length > maxSelection) {
        selectAll.checked = false;
        window.alert(`Selecting this page would exceed the ${maxSelection}-file limit.`);
        return;
      }
      checkboxes.forEach((checkbox) => selected.add(checkbox.value));
    } else {
      checkboxes.forEach((checkbox) => selected.delete(checkbox.value));
    }
    saveSelection();
    refreshUi();
  });

  clearButton.addEventListener("click", function () {
    selected.clear();
    saveSelection();
    refreshUi();
  });

  moveForm.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!selected.size || running) return;
    document.getElementById("confirm-count").textContent = String(selected.size);
    setModal(confirmModal, true);
  });

  cancelMove.addEventListener("click", () => setModal(confirmModal, false));
  confirmMove.addEventListener("click", executeMove);
  returnButton.addEventListener("click", function () {
    setModal(completionModal, false);
    window.location.reload();
  });

  refreshUi();
})();
