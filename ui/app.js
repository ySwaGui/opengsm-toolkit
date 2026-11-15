/* OpenGSM Toolkit - front-end (vanilla JS) */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

let selected = null; // {serial, mode, model}

const out = $("#output");
const status = $("#statusMsg");

function setStatus(msg) { status.textContent = msg; }

function esc(s) {
  return String(s ?? "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

// Ponte com o Python nativo (pywebview). Sem servidor HTTP — chamamos
// window.pywebview.api.* diretamente. Mantém a assinatura antiga api(path, opts)
// pra não mexer no resto do código.
async function api(path, opts) {
  const A = window.pywebview && window.pywebview.api;
  if (!A) throw new Error("API nativa indisponível");
  const [p, qs] = path.split("?");
  const params = new URLSearchParams(qs || "");
  const body = (opts && opts.body) ? JSON.parse(opts.body) : {};
  switch (p) {
    case "/api/meta": return A.meta();
    case "/api/devices": return A.devices();
    case "/api/info": return A.info(params.get("serial") || "", params.get("mode") || "adb");
    case "/api/logs": return A.logs();
    case "/api/backends": return A.backends();
    case "/api/tutorials": return A.tutorials();
    case "/api/usb": return A.usb();
    case "/api/compat": return A.compat();
    case "/api/drivers": return A.drivers();
    case "/api/diag": return A.diag(body.serial || "", body.mode || "adb");
    case "/api/backup": return A.backup(body.serial || "");
    case "/api/reboot": return A.reboot(body.serial || "", body.mode || "adb", body.target || "system");
    case "/api/backend/run": return A.backend_run(body.backend || "", body.action || "", body.serial || "");
    case "/api/drivers/install": return A.drivers_install(body.id || "");
  }
  throw new Error("rota desconhecida: " + p);
}

/* ---------- Meta ---------- */
async function loadMeta() {
  try {
    const m = await api("/api/meta");
    $("#brandSub").textContent = m.full;
    $("#verLabel").textContent = `v${m.version}`;
  } catch (e) { /* ignore */ }
}

/* ---------- Devices ---------- */
async function loadDevices() {
  const pill = $("#toolsPill");
  try {
    const data = await api("/api/devices");
    const t = data.tools;
    if (t.adb || t.fastboot) {
      pill.className = "pill ok";
      pill.textContent = `adb ${t.adb ? "✓" : "✗"} · fastboot ${t.fastboot ? "✓" : "✗"}`;
    } else {
      pill.className = "pill bad";
      pill.textContent = "adb/fastboot não encontrados";
    }
    renderDevices(data.devices);
    loadCompat();
  } catch (e) {
    pill.className = "pill bad";
    pill.textContent = "erro ao consultar";
  }
}

function selectDevice(d, devices) {
  selected = d;
  $("#selLabel").textContent = `${d.model || d.serial} (${d.mode})`;
  renderDevices(devices);
  renderActions();
}

function renderDevices(devices) {
  const list = $("#deviceList");
  if (!devices.length) {
    list.innerHTML = '<div class="empty">Nenhum aparelho. Conecte via USB (depuração USB ligada).</div>';
    if (selected !== null) { selected = null; renderActions(); }
    return;
  }

  // Reconcilia a seleção com a lista nova (mantém pelo serial; detecta mudança de modo).
  if (selected) {
    const match = devices.find(x => x.serial === selected.serial);
    if (match) {
      const modeChanged = match.mode !== selected.mode;
      selected = match;
      if (modeChanged) renderActions();
    } else {
      selected = null;
      renderActions();
    }
  }
  // Auto-seleciona quando há só um aparelho (mostra as opções na hora).
  if (!selected && devices.length === 1) {
    selected = devices[0];
    $("#selLabel").textContent = `${selected.model || selected.serial} (${selected.mode})`;
    renderActions();
  }

  list.innerHTML = "";
  devices.forEach(d => {
    const el = document.createElement("div");
    el.className = "device";
    if (selected && selected.serial === d.serial) el.classList.add("sel");
    el.innerHTML = `
      <div class="d-model">${esc(d.model || d.serial)}</div>
      <div class="d-serial">${esc(d.serial)}</div>
      <span class="d-mode ${d.mode}">${d.mode}${d.state && d.state !== d.mode ? " · " + esc(d.state) : ""}</span>`;
    el.onclick = () => selectDevice(d, devices);
    list.appendChild(el);
  });
}

const BK_LABEL = { mtk: "MediaTek (mtkclient)", edl: "Qualcomm (edl)" };

// Monta os botões conforme o MODO do aparelho selecionado (detecção automática).
// União de todas as ações de todos os modos (sem repetir pelo rótulo).
function allActions() {
  const seen = new Set(), all = [];
  const ma = (TUT && TUT.mode_actions) || {};
  Object.values(ma).forEach(arr => arr.forEach(a => {
    if (!seen.has(a.label)) { seen.add(a.label); all.push(a); }
  }));
  return all;
}

function renderActions() {
  const box = $("#actions");
  box.innerHTML = "";
  if (!selected) {
    // Sem aparelho: mostra TODAS as funções (desabilitadas) como prévia.
    const all = allActions();
    const note = document.createElement("div");
    note.className = "actions-note";
    note.textContent = "Nenhum aparelho conectado — todas as funções (conecte um aparelho para usar):";
    box.appendChild(note);
    if (!all.length) {
      box.insertAdjacentHTML("beforeend", '<span class="empty">conecte um aparelho.</span>');
      return;
    }
    all.forEach(a => {
      const b = document.createElement("button");
      b.className = "btn" + (a.danger ? " danger" : "");
      b.textContent = a.label;
      b.disabled = true;
      box.appendChild(b);
    });
    return;
  }
  const acts = (TUT && TUT.mode_actions && TUT.mode_actions[selected.mode]) || null;
  if (acts === null) {
    box.innerHTML = `<span class="empty">Modo <b>${esc(selected.mode)}</b> reconhecido, mas sem mapa de ações.</span>`;
    return;
  }
  if (!acts.length) {
    box.innerHTML = `<span class="empty">Modo <b>${esc(selected.mode)}</b>: sem ações automáticas aqui. Veja o 📘 Guia de modos.</span>`;
    return;
  }
  acts.forEach((a, i) => {
    const b = document.createElement("button");
    b.className = "btn" + (i === 0 ? " primary" : "") + (a.danger ? " danger" : "");
    b.textContent = a.label;
    b.onclick = () => runAction(a);
    box.appendChild(b);
  });
}

/* ---------- Dispatch central de ações ---------- */
function A() { return window.pywebview && window.pywebview.api; }

function showOp(title, d) {
  const txt = d.msg || d.err || d.out || (d.dest ? ("salvo em: " + d.dest) : "") || "(sem saída)";
  out.innerHTML = `<div class="note">
    <p><strong>${esc(title)}</strong> — ${d.ok ? "✓ ok" : "✗ falha"}</p>
    ${d.dest ? `<p class="muted">${esc(d.dest)}</p>` : ""}
    <pre style="white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px;color:var(--text);margin:8px 0 0">${esc(txt)}</pre>
  </div>`;
  setStatus(d.ok ? `${title} concluído.` : `${title} falhou.`);
  loadLogs();
}

const CORE_HANDLERS = {
  info: doInfo, diag: doDiag, backup: doBackup, reboot: doReboot,
  async screenshot() { spinner("Capturando tela…"); showOp("Screenshot", await A().screenshot(selected.serial)); },
  async logcat() { spinner("Coletando logcat…"); showOp("Logcat", await A().logcat(selected.serial)); },
  async props() { spinner("Lendo propriedades…"); showOp("build.prop", await A().props(selected.serial)); },
  async packages() {
    spinner("Listando apps…");
    const d = await A().packages(selected.serial);
    out.innerHTML = `<div class="note"><p><strong>Apps instalados</strong> — ${d.count || 0}</p>
      <pre style="white-space:pre-wrap;font-family:Consolas,monospace;font-size:11.5px;color:var(--text);margin:8px 0 0">${esc((d.packages || []).join("\n"))}</pre></div>`;
    setStatus("apps: " + (d.count || 0));
  },
  async apk_install() { spinner("Escolha o APK…"); showOp("Instalar APK", await A().install_apk(selected.serial, "")); },
  async apk_uninstall() { const p = prompt("Pacote a desinstalar (ex.: com.exemplo.app):"); if (!p) return; spinner("Desinstalando…"); showOp("Desinstalar", await A().uninstall(selected.serial, p)); },
  async pull() { const r = prompt("Caminho no aparelho pra puxar:", "/sdcard/DCIM"); if (!r) return; spinner("Puxando arquivos…"); showOp("Puxar arquivos", await A().pull(selected.serial, r)); },
  async sideload() { if (!confirm("Sideload de OTA/ZIP?\nO aparelho precisa estar em Recovery → 'Apply update from ADB'.")) return; spinner("Escolha o ZIP…"); showOp("Sideload OTA", await A().sideload(selected.serial, "")); },
  async fb_flash() { const p = prompt("Partição (ex.: boot, recovery, vbmeta):"); if (!p) return; spinner("Gravando " + p + "…"); showOp("Flash " + p, await A().fb_flash(selected.serial, p, "")); },
  async fb_erase_frp() { if (!confirm("Apagar FRP (fastboot erase frp)?\nUse SÓ em aparelho seu/autorizado. Requer bootloader destravado.")) return; spinner("Apagando FRP…"); showOp("Apagar FRP", await A().fb_erase(selected.serial, "frp")); },
  async fb_unlock() { if (!confirm("Destravar bootloader?\n⚠ ISSO APAGA TODOS OS DADOS do aparelho. Confirme também na tela do aparelho.")) return; spinner("Destravando…"); showOp("Destravar bootloader", await A().fb_unlock(selected.serial, true)); },
  async fb_lock() { if (!confirm("Retravar bootloader?\nPode apagar dados. Confirme na tela do aparelho.")) return; spinner("Retravando…"); showOp("Retravar bootloader", await A().fb_unlock(selected.serial, false)); },
};

async function dumpPartition(backend) {
  const p = prompt("Partição pra ler (dump) — ex.: boot, persist, nvram, efs:");
  if (!p) return;
  spinner("Lendo partição " + p + "… (aguarde)");
  showOp("Dump " + p, await A().dump(backend, p, selected ? selected.serial : ""));
}

// Loader opcional fornecido pelo usuário (DA/Firehose do aparelho dele).
let userLoader = "";

async function pickLoader(backend) {
  const p = await A().pick_loader();
  if (p) {
    userLoader = p;
    setStatus("Loader definido: " + p.split(/[\\/]/).pop());
    out.innerHTML = `<div class="note"><p><strong>Loader definido</strong> (${esc(BK_LABEL[backend] || backend)})</p><p class="muted">${esc(p)}</p><p>Será usado nas próximas operações. Deixe vazio pra usar o loader automático.</p></div>`;
  }
}

const OP_WARN = {
  unlock: "Destravar bootloader (seccfg)?\n⚠ APAGA TODOS OS DADOS. Use só em aparelho SEU/autorizado.",
  lock: "Retravar bootloader (seccfg)?\nPode apagar dados. Aparelho seu/autorizado.",
  frp: "Apagar a partição FRP?\nUse só em aparelho SEU/autorizado.",
  erase: "Apagar a partição escolhida?\n⚠ Operação destrutiva.",
  write: "Gravar imagem na partição?\n⚠ Imagem errada pode inutilizar o aparelho.",
  reset: "",
};

async function runBackendOp(a) {
  let partition = "";
  if (a.verb === "write" || a.verb === "erase") {
    partition = prompt("Partição (ex.: boot, recovery, vbmeta, userdata):");
    if (!partition) return;
  }
  const warn = OP_WARN[a.verb];
  if (warn && !confirm(warn + (partition ? `\n\nPartição: ${partition}` : "") + (userLoader ? "\nLoader: " + userLoader.split(/[\\/]/).pop() : ""))) return;
  const label = (BK_LABEL[a.backend] || a.backend) + " · " + a.verb + (partition ? " " + partition : "");
  spinner("Executando " + label + "… (aguarde)");
  const d = await A().backend_op(a.backend, a.verb, partition, userLoader, selected ? selected.serial : "");
  showOp(label, d);
}

function runAction(a) {
  if (a.kind === "core") { const h = CORE_HANDLERS[a.id]; if (h) h(); }
  else if (a.kind === "dump") { dumpPartition(a.backend); }
  else if (a.kind === "op2") { runBackendOp(a); }
  else if (a.kind === "loader") { pickLoader(a.backend); }
  else { executeBackend(a.backend, a.action, BK_LABEL[a.backend] || a.backend); }
}

/* ---------- Render de info ---------- */
function renderKV(rows) {
  const body = rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join("");
  out.innerHTML = `<table class="kv">${body}</table>`;
}

function spinner(txt) {
  out.innerHTML = `<div class="placeholder"><div class="spin ph-logo">◠</div><p>${esc(txt)}</p></div>`;
}

/* ---------- Ações ---------- */
async function doInfo() {
  spinner("Lendo informações do aparelho…");
  setStatus("Lendo info…");
  const d = await api(`/api/info?serial=${encodeURIComponent(selected.serial)}&mode=${selected.mode}`);
  renderKV(Object.entries(d.info));
  setStatus("Info lida.");
}

async function doDiag() {
  spinner("Rodando diagnóstico…");
  setStatus("Diagnóstico…");
  const d = await api("/api/diag", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ serial: selected.serial, mode: selected.mode })
  });
  renderKV(d.rows);
  setStatus(`Diagnóstico salvo: ${d.log}`);
  loadLogs();
}

async function doBackup() {
  if (!confirm("Fazer backup de DCIM, Download e Pictures do aparelho para a pasta Backup?")) return;
  spinner("Copiando arquivos (pode demorar)…");
  setStatus("Backup em andamento…");
  const d = await api("/api/backup", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ serial: selected.serial })
  });
  const rows = d.results.map(r => [r.item, (r.ok ? "✓ ok" : "✗ ") + " " + (r.msg || "")]);
  rows.unshift(["Pasta destino", d.dest]);
  renderKV(rows);
  setStatus("Backup concluído.");
}

async function doReboot() {
  let target = "system";
  if (selected.mode === "adb") {
    const c = prompt("Reiniciar para:\nsystem / bootloader / fastboot / recovery / download / edl / sideload", "system");
    if (c === null) return;
    target = c.trim() || "system";
  } else if (selected.mode === "fastboot") {
    const c = prompt("Reiniciar para:\nsystem / bootloader / recovery / edl", "system");
    if (c === null) return;
    target = c.trim() || "system";
  }
  setStatus("Reiniciando…");
  const d = await api("/api/reboot", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ serial: selected.serial, mode: selected.mode, target })
  });
  setStatus(d.ok ? "Comando de reinício enviado." : "Falha: " + d.msg);
}

function doFlash() {
  out.innerHTML = `<div class="note">
    <p><strong>Flash via fastboot</strong> — disponível apenas para aparelhos com
    <em>bootloader destravado</em>, em modo fastboot.</p>
    <p>Por segurança, esta versão não grava partições automaticamente pela interface.
    Para gravar manualmente (exemplo), use no terminal:</p>
    <p style="font-family:Consolas,monospace;color:var(--primary)">
    fastboot flash boot boot.img<br>fastboot reboot</p>
    <p>Gravar firmware incorreto pode inutilizar o aparelho. O OpenGSM Toolkit não reproduz
    os modos proprietários (Qualcomm EDL / MTK BROM / SPRD) de ferramentas comerciais.</p>
  </div>`;
  setStatus("Flash: instruções exibidas.");
}

/* ---------- Backends avançados (EDL/MTK) ---------- */
async function loadBackends() {
  const body = $("#bkBody");
  try {
    const d = await api("/api/backends");
    if (!d.available) {
      body.innerHTML = '<span class="empty">Módulo de backends indisponível.</span>';
      return;
    }
    const bks = d.backends;
    body.innerHTML = "";
    Object.entries(bks).forEach(([key, b]) => {
      const row = document.createElement("div");
      row.className = "bk-row";
      row.dataset.bk = key;
      const on = b.installed;
      row.innerHTML = `
        <span class="bk-dot ${on ? "on" : "off"}"></span>
        <div>
          <div class="bk-name">${esc(b.name)}</div>
          <div class="bk-proto">${esc(b.proto)}</div>
        </div>
        <span class="bk-compat" id="compat-${key}"></span>
        <span class="grow"></span>`;
      if (on) {
        ["gpt", "info"].forEach(act => {
          const btn = document.createElement("button");
          btn.className = "btn sm";
          btn.textContent = act === "gpt" ? "Ler partições" : "Info target";
          btn.onclick = () => runBackend(key, act, b.name);
          row.appendChild(btn);
        });
      } else {
        const tag = document.createElement("span");
        tag.className = "bk-proto";
        tag.style.color = "var(--accent)";
        tag.textContent = "não detectado" + (b.reason ? " — " + b.reason : "") + " · " + b.project;
        row.appendChild(tag);
      }
      body.appendChild(row);
    });
    loadCompat();
  } catch (e) {
    body.innerHTML = '<span class="empty">erro ao consultar backends.</span>';
  }
}

// Marca no painel avançado se o aparelho conectado é compatível com cada backend.
async function loadCompat() {
  try {
    const c = await api("/api/compat");
    const map = { mtk: c.mtk, edl: c.edl };
    const temAparelho = !!(c.mode || c.chipset);
    ["mtk", "edl"].forEach(k => {
      const el = document.getElementById("compat-" + k);
      if (!el) return;
      el.className = "bk-compat";
      if (map[k] === true) {
        el.textContent = "✓ compatível com o aparelho";
        el.classList.add("ok");
        el.title = c.chipset ? ("chipset: " + c.chipset) : (c.mode || "");
      } else if (temAparelho) {
        el.textContent = "aparelho não é deste tipo";
        el.classList.add("no");
      } else {
        el.textContent = "";
      }
    });
  } catch (e) { /* ignore */ }
}

function runBackend(backend, action, label) {
  // Abre o tutorial do(s) modo(s) que esse backend exige; ao confirmar, executa.
  const modes = (TUT && TUT.backend_mode[backend]) || [];
  openModeTutorial(modes, () => executeBackend(backend, action, label));
}

async function executeBackend(backend, action, label) {
  closeModal();
  spinner(`Executando ${label}… (aguarde o aparelho no modo correto)`);
  setStatus(`${label}: ${action}…`);
  const d = await api("/api/backend/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ backend, action, serial: selected ? selected.serial : "" })
  });
  out.innerHTML = `<div class="note">
    <p><strong>${esc(label)} · ${esc(action)}</strong> — ${d.ok ? "✓ ok" : "✗ falha"}</p>
    <pre style="white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px;color:var(--text);margin:8px 0 0">${esc(d.out || d.err || "(sem saída)")}</pre>
  </div>`;
  setStatus(d.ok ? `${label} concluído.` : `${label} falhou.`);
  loadLogs();
}

/* ---------- Tutorial de modo (modal) ---------- */
let TUT = null;              // base de tutoriais
let modalModeKeys = [];      // modos abertos no modal
let modalOnContinue = null;  // callback do botão Continuar

async function loadTutorials() {
  try {
    const d = await api("/api/tutorials");
    if (d.available) TUT = d;
  } catch (e) { /* ignore */ }
}

function closeModal() {
  $("#modeModal").hidden = true;
  modalOnContinue = null;
}

function openModeTutorial(modeKeys, onContinue) {
  if (!TUT) { if (onContinue) onContinue(); return; }
  modalModeKeys = (modeKeys && modeKeys.length) ? modeKeys : Object.keys(TUT.modes);
  modalOnContinue = onContinue || null;

  // selector de marca
  const brandSel = $("#mBrand");
  brandSel.innerHTML = '<option value="">Genérico (qualquer marca)</option>' +
    TUT.brands.map(b => `<option value="${esc(b)}">${esc(b)}</option>`).join("");

  // se houver mais de um modo, injeta um seletor de modo no topo do corpo
  renderModeHeader();
  renderTutorial();
  $("#mContinue").hidden = !modalOnContinue;
  $("#mDetectMsg").textContent = "";
  $("#modeModal").hidden = false;
}

let currentModeKey = null;
function renderModeHeader() {
  currentModeKey = modalModeKeys[0];
  const head = $(".modal-head #mTitle");
  if (modalModeKeys.length > 1) {
    const opts = modalModeKeys.map(k =>
      `<option value="${k}">${esc(TUT.modes[k].name)}</option>`).join("");
    head.innerHTML = `Modo: <select id="mModeSel" style="background:var(--bg-2);color:var(--primary);border:1px solid var(--border);border-radius:6px;padding:2px 6px;font-weight:700">${opts}</select>`;
    setTimeout(() => {
      const sel = $("#mModeSel");
      if (sel) sel.onchange = () => { currentModeKey = sel.value; renderTutorial(); };
    }, 0);
  } else {
    head.textContent = TUT.modes[currentModeKey].name;
  }
}

function renderTutorial() {
  const m = TUT.modes[currentModeKey];
  const brand = $("#mBrand").value;
  $("#mDesc").textContent = m.desc || "";

  // passos: override por marca, senão genérico
  let steps = m.generic || [];
  if (brand && m.brands && m.brands[brand]) steps = m.brands[brand];
  // casa variações de marca (ex.: "Oppo/Realme" ~ "OnePlus/Oppo/Realme")
  else if (brand && m.brands) {
    const hit = Object.keys(m.brands).find(k =>
      k.toLowerCase().includes(brand.toLowerCase().split("/")[0]) ||
      brand.toLowerCase().includes(k.toLowerCase().split("/")[0]));
    if (hit) steps = m.brands[hit];
  }
  $("#mSteps").innerHTML = steps.map(s => `<li>${esc(s)}</li>`).join("");

  // software
  const soft = m.software || [];
  $("#mSoftWrap").hidden = !soft.length;
  $("#mSoft").innerHTML = soft.map(s => `<li>${esc(s)}</li>`).join("");

  // test point
  $("#mTpWrap").hidden = !m.testpoint;
  if (m.testpoint) $("#mTp").textContent = m.testpoint;

  // verify + warn
  $("#mVerify").textContent = m.verify || "";
  const warn = $("#mWarn");
  warn.hidden = !m.warning;
  if (m.warning) warn.textContent = "⚠ " + m.warning;
}

async function detectUsb() {
  const msg = $("#mDetectMsg");
  msg.textContent = "lendo USB…";
  msg.className = "muted";
  try {
    const d = await api("/api/usb");
    const devs = (d.devices || []);
    if (!devs.length) {
      msg.textContent = "Nenhum aparelho conhecido no USB. Conecte e tente de novo.";
      msg.className = "detect-miss";
      return;
    }
    // prioriza um que já esteja num modo
    const inMode = devs.find(x => x.mode);
    const dev = inMode || devs[0];
    // ajusta a marca no select
    const sel = $("#mBrand");
    const opt = [...sel.options].find(o =>
      o.value && (o.value.toLowerCase().includes(dev.brand.toLowerCase()) ||
                  dev.brand.toLowerCase().includes(o.value.toLowerCase().split("/")[0])));
    if (opt) { sel.value = opt.value; renderTutorial(); }

    if (dev.mode) {
      // já está num modo conhecido — se bate com o alvo, avisa que pode continuar
      if (modalModeKeys.includes(dev.mode)) {
        currentModeKey = dev.mode;
        const ms = $("#mModeSel"); if (ms) ms.value = dev.mode;
        renderTutorial();
        msg.innerHTML = `✓ Detectado <b>${esc(dev.brand)}</b> já em <b>${esc(TUT.modes[dev.mode].name)}</b> — pode continuar.`;
        msg.className = "detect-hit";
      } else {
        msg.innerHTML = `Detectado <b>${esc(dev.brand)}</b> em <b>${esc(TUT.modes[dev.mode] ? TUT.modes[dev.mode].name : dev.mode)}</b> (VID ${dev.vid}/${dev.pid}).`;
        msg.className = "detect-hit";
      }
    } else {
      msg.innerHTML = `Detectado <b>${esc(dev.brand)}</b> (VID ${dev.vid}/PID ${dev.pid}) — ainda não está no modo. Siga os passos.`;
      msg.className = "detect-miss";
    }
  } catch (e) {
    msg.textContent = "erro ao ler USB.";
    msg.className = "detect-miss";
  }
}

/* ---------- Instalador de drivers ---------- */
async function openDrivers() {
  $("#drvModal").hidden = false;
  await loadDriversList();
}

async function loadDriversList() {
  const body = $("#drvBody");
  body.innerHTML = '<span class="empty">verificando drivers…</span>';
  try {
    const d = await api("/api/drivers");
    if (!d.available) { body.innerHTML = '<span class="empty">Instalador indisponível.</span>'; return; }
    const groups = {};
    d.drivers.forEach(x => { (groups[x.group] = groups[x.group] || []).push(x); });
    body.innerHTML = "";
    Object.entries(groups).forEach(([g, items]) => {
      const h = document.createElement("div");
      h.className = "tut-label";
      h.textContent = g === "Base" ? "Automáticos (base)" : "Fabricantes (página oficial)";
      body.appendChild(h);
      items.forEach(x => {
        const row = document.createElement("div");
        row.className = "drv-row";
        let right = "";
        if (x.kind === "link") {
          right = `<button class="btn sm" data-drv="${x.id}">🌐 Abrir site</button>`;
        } else if (x.kind === "tool") {
          right = x.present
            ? `<button class="btn sm" data-drv="${x.id}">Abrir</button>`
            : `<span class="drv-st no">ausente da pasta</span>`;
        } else { // auto
          const ok = x.state === "instalado";
          const tag = ok ? `<span class="drv-st ok">✓ instalado</span>` : "";
          right = tag + (x.present
            ? `<button class="btn sm${ok ? "" : " primary"}" data-drv="${x.id}">${ok ? "Reinstalar" : "Instalar"}</button>`
            : `<span class="drv-st no">arquivo ausente</span>`);
        }
        row.innerHTML = `
          <div class="drv-info">
            <div class="drv-name">${esc(x.name)}</div>
            ${x.desc ? `<div class="drv-desc">${esc(x.desc)}</div>` : ""}
          </div>
          <div class="drv-actions">${right}</div>`;
        body.appendChild(row);
      });
    });
    body.querySelectorAll("[data-drv]").forEach(b => {
      b.addEventListener("click", () => installDriver(b.dataset.drv, b));
    });
  } catch (e) {
    body.innerHTML = '<span class="empty">erro ao consultar drivers.</span>';
  }
}

async function installDriver(id, btn) {
  const old = btn.textContent;
  btn.disabled = true; btn.textContent = "…";
  setStatus("Driver: " + id + "…");
  try {
    const d = await api("/api/drivers/install", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id })
    });
    setStatus(d.msg || (d.ok ? "ok" : "falha"));
    alert(d.msg || (d.ok ? "Ação iniciada." : "Falha."));
  } catch (e) {
    setStatus("erro ao instalar driver.");
  } finally {
    btn.disabled = false; btn.textContent = old;
    setTimeout(loadDriversList, 1500); // re-verifica status
  }
}

$("#driversBtn").addEventListener("click", openDrivers);
$("#drvClose").addEventListener("click", () => $("#drvModal").hidden = true);
$("#drvCancel").addEventListener("click", () => $("#drvModal").hidden = true);
$("#drvRefresh").addEventListener("click", loadDriversList);
$("#drvModal").addEventListener("click", (e) => { if (e.target.id === "drvModal") $("#drvModal").hidden = true; });

/* wiring do modal */
$("#mBrand").addEventListener("change", renderTutorial);
$("#mDetect").addEventListener("click", detectUsb);
$("#mClose").addEventListener("click", closeModal);
$("#mCancel").addEventListener("click", closeModal);
$("#mContinue").addEventListener("click", () => { if (modalOnContinue) modalOnContinue(); });
$("#modeModal").addEventListener("click", (e) => {
  if (e.target.id === "modeModal") closeModal();
});

/* ---------- Logs ---------- */
async function loadLogs() {
  try {
    const d = await api("/api/logs");
    const list = $("#logList");
    if (!d.logs.length) { list.innerHTML = '<div class="empty">Nenhum log ainda.</div>'; return; }
    list.innerHTML = d.logs.map(f => `<div class="log-item">${esc(f)}</div>`).join("");
  } catch (e) { /* ignore */ }
}

/* ---------- Wiring ---------- */
$("#refreshBtn").addEventListener("click", () => { loadDevices(); loadLogs(); loadBackends(); });
$("#guideBtn").addEventListener("click", () => openModeTutorial(null, null)); // avulso: todos os modos

function init() {
  loadTutorials().then(() => {
    loadMeta();
    loadDevices();
    loadLogs();
    loadBackends();
    renderActions(); // mostra todas as funções enquanto não há aparelho
  });
  setInterval(loadDevices, 5000); // auto-detecta conexões
}

// Espera a API nativa do pywebview ficar pronta antes de iniciar.
if (window.pywebview && window.pywebview.api) {
  init();
} else {
  window.addEventListener("pywebviewready", init);
}
