(function () {
  "use strict";

  function initNavbarShadow() {
    var nav = document.querySelector(".cc-navbar");
    if (!nav) return;
    var update = function () {
      nav.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  function initToasts() {
    var toasts = document.querySelectorAll(".cc-toast");
    toasts.forEach(function (toast) {
      var close = function () {
        toast.classList.add("is-hiding");
        setTimeout(function () {
          toast.remove();
        }, 400);
      };
      var button = toast.querySelector(".btn-close");
      if (button) button.addEventListener("click", close);
      setTimeout(close, 5000);
    });
  }

  function initConfirmForms() {
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });
  }

  function initRoleToggle() {
    var radios = document.querySelectorAll("input[name='role']");
    var doctorFields = document.querySelectorAll("[data-role-section='doctor']");
    var patientFields = document.querySelectorAll("[data-role-section='patient']");
    if (!radios.length) return;
    var apply = function () {
      var role = document.querySelector("input[name='role']:checked").value;
      doctorFields.forEach(function (el) {
        el.classList.toggle("d-none", role !== "doctor");
        el.querySelectorAll("input, select, textarea").forEach(function (input) {
          input.disabled = role !== "doctor";
        });
      });
      patientFields.forEach(function (el) {
        el.classList.toggle("d-none", role !== "patient");
        el.querySelectorAll("input").forEach(function (input) {
          input.disabled = role !== "patient";
        });
      });
    };
    radios.forEach(function (radio) {
      radio.addEventListener("change", apply);
    });
    apply();
  }

  function initBookingSlots() {
    var doctorSelect = document.getElementById("doctorSelect");
    var dateInput = document.getElementById("appointmentDate");
    var slotGrid = document.getElementById("slotGrid");
    if (!doctorSelect || !dateInput || !slotGrid) return;

    var preselected = slotGrid.getAttribute("data-selected");

    var showMessage = function (text, tone) {
      slotGrid.innerHTML = "";
      var note = document.createElement("p");
      note.className = "text-" + tone + " mb-0 small fw-semibold";
      note.textContent = text;
      slotGrid.appendChild(note);
    };

    var loadSlots = function () {
      if (!doctorSelect.value || !dateInput.value) {
        showMessage("Select a doctor and date to see open time slots.", "muted");
        return;
      }
      showMessage("Checking availability...", "muted");
      var url = "/api/doctors/" + encodeURIComponent(doctorSelect.value) + "/slots?date=" + encodeURIComponent(dateInput.value);
      fetch(url, { headers: { Accept: "application/json" } })
        .then(function (response) {
          return response.json().then(function (body) {
            if (!response.ok) throw new Error(body.error || "Could not load time slots.");
            return body;
          });
        })
        .then(function (body) {
          if (!body.available) {
            showMessage("This doctor is not available on the selected day. Please choose another date.", "danger");
            return;
          }
          if (!body.slots.length) {
            showMessage("All slots are booked for this day. Please choose another date.", "danger");
            return;
          }
          slotGrid.innerHTML = "";
          body.slots.forEach(function (slot) {
            var wrapper = document.createElement("label");
            wrapper.className = "cc-slot col";
            var input = document.createElement("input");
            input.type = "radio";
            input.name = "time_slot";
            input.value = slot;
            input.required = true;
            input.checked = slot === preselected;
            var span = document.createElement("span");
            span.textContent = slot;
            wrapper.appendChild(input);
            wrapper.appendChild(span);
            slotGrid.appendChild(wrapper);
          });
          preselected = null;
        })
        .catch(function (error) {
          showMessage(error.message, "danger");
        });
    };

    doctorSelect.addEventListener("change", loadSlots);
    dateInput.addEventListener("change", loadSlots);
    loadSlots();
  }

  function initConsultation() {
    var stage = document.getElementById("consultStage");
    if (!stage) return;

    var timerEl = document.getElementById("callTimer");
    var startBtn = document.getElementById("startSession");
    var cameraBtn = document.getElementById("toggleCamera");
    var micBtn = document.getElementById("toggleMic");
    var endBtn = document.getElementById("endCall");
    var selfPanel = document.getElementById("selfPanel");
    var statusEl = document.getElementById("sessionStatus");
    var chatForm = document.getElementById("chatForm");
    var chatInput = document.getElementById("chatInput");
    var chatLog = document.getElementById("chatLog");
    var replies = [
      "Thank you, that is helpful. Please continue.",
      "Noted. Let me review that with you.",
      "Could you tell me when the symptoms started?",
      "Please keep your prescription handy for later.",
    ];
    var seconds = 0;
    var timer = null;
    var replyIndex = 0;

    var formatTime = function (total) {
      var m = String(Math.floor(total / 60)).padStart(2, "0");
      var s = String(total % 60).padStart(2, "0");
      return m + ":" + s;
    };

    var addBubble = function (who, text) {
      var bubble = document.createElement("div");
      bubble.className = "cc-bubble " + (who === "You" ? "me" : "them");
      var label = document.createElement("small");
      label.textContent = who;
      bubble.appendChild(label);
      bubble.appendChild(document.createTextNode(text));
      chatLog.appendChild(bubble);
      chatLog.scrollTop = chatLog.scrollHeight;
    };

    var setSessionRunning = function (running) {
      if (startBtn) startBtn.classList.toggle("d-none", running);
      if (statusEl) statusEl.textContent = running ? "Simulated session in progress" : "Simulation ready";
      [cameraBtn, micBtn, endBtn].forEach(function (btn) {
        if (btn) btn.disabled = !running;
      });
      if (chatInput) chatInput.disabled = !running;
      if (chatForm) chatForm.querySelector("button[type='submit']").disabled = !running;
    };

    var startTimer = function () {
      if (timer) return;
      timer = setInterval(function () {
        seconds += 1;
        timerEl.textContent = formatTime(seconds);
      }, 1000);
    };

    var stopTimer = function () {
      clearInterval(timer);
      timer = null;
    };

    var setToggle = function (button, panel, onLabel, offLabel, isOn) {
      button.classList.toggle("is-off", !isOn);
      button.setAttribute("aria-pressed", String(isOn));
      button.innerHTML = isOn
        ? '<i class="fa-solid ' + (button.dataset.iconOn) + '"></i>'
        : '<i class="fa-solid ' + (button.dataset.iconOff) + '"></i>';
      button.title = isOn ? onLabel : offLabel;
      if (panel) panel.classList.toggle("is-off", !isOn);
    };

    if (startBtn) {
      startBtn.addEventListener("click", function () {
        setSessionRunning(true);
        startTimer();
        addBubble("Care team", "Simulated session started. This is a demo of the consultation screen only.");
      });
    }

    if (cameraBtn) {
      cameraBtn.addEventListener("click", function () {
        var isOn = cameraBtn.getAttribute("aria-pressed") !== "false";
        setToggle(cameraBtn, selfPanel, "Turn camera off", "Turn camera on", !isOn);
        var label = selfPanel && selfPanel.querySelector(".cc-camera-state");
        if (label) label.textContent = isOn ? "Camera off" : "Camera on (simulated)";
      });
    }

    if (micBtn) {
      micBtn.addEventListener("click", function () {
        var isOn = micBtn.getAttribute("aria-pressed") !== "false";
        setToggle(micBtn, null, "Mute microphone", "Unmute microphone", !isOn);
      });
    }

    if (endBtn) {
      endBtn.addEventListener("click", function () {
        if (!window.confirm("End this simulated consultation?")) return;
        stopTimer();
        setSessionRunning(false);
        if (statusEl) statusEl.textContent = "Simulated session ended after " + formatTime(seconds);
        addBubble("Care team", "Session ended. Thank you for consulting with CareConnect360.");
      });
    }

    if (chatForm) {
      chatForm.addEventListener("submit", function (event) {
        event.preventDefault();
        var text = chatInput.value.trim();
        if (!text) return;
        addBubble("You", text);
        chatInput.value = "";
        setTimeout(function () {
          addBubble("Care team", replies[replyIndex % replies.length]);
          replyIndex += 1;
        }, 900);
      });
    }
  }

  function initPrintButtons() {
    document.querySelectorAll("[data-print]").forEach(function (button) {
      button.addEventListener("click", function () {
        window.print();
      });
    });
  }

  function initDemoAccounts() {
    document.querySelectorAll("[data-fill-email]").forEach(function (button) {
      button.addEventListener("click", function () {
        var form = button.closest("form") || document;
        var email = form.querySelector("input[name='email']");
        var password = form.querySelector("input[name='password']");
        if (email) email.value = button.dataset.fillEmail;
        if (password) password.value = button.dataset.fillPassword || "";
        if (email) email.focus();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initNavbarShadow();
    initToasts();
    initConfirmForms();
    initRoleToggle();
    initBookingSlots();
    initConsultation();
    initPrintButtons();
    initDemoAccounts();
  });
})();
