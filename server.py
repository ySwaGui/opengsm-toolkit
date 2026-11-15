#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenGSM Toolkit  -  Open Android Service Toolkit
Ferramenta ORIGINAL de diagnostico/servico de aparelhos Android.
Backend em Python puro (stdlib), usando as ferramentas abertas adb e fastboot.

Isto NAO e um clone de nenhum software comercial: e codigo proprio.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

try:
    import backends  # backends abertos opcionais (mtkclient / edlclient)
except Exception:  # noqa
    backends = None

try:
    import tutorials  # base de tutoriais de modo + deteccao USB
except Exception:  # noqa
    tutorials = None

try:
    import drivers  # instalador de drivers
except Exception:  # noqa
    drivers = None

APP_NAME = "OpenGSM Toolkit"
APP_FULL = "Open Android Service Toolkit"
VERSION = "1.0.0"
HOST = "127.0.0.1"
PORT = 8720

# Pasta base: ao lado do .exe quando empacotado (PyInstaller), senao do script.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")
BACKUP_DIR = os.path.join(BASE_DIR, "Backup")
SHOT_DIR = os.path.join(BASE_DIR, "ScreenShot")
DUMP_DIR = os.path.join(BASE_DIR, "Dumps")

for d in (LOGS_DIR, BACKUP_DIR, SHOT_DIR, DUMP_DIR):
    os.makedirs(d, exist_ok=True)

# Binarios PROPRIOS da pasta (autossuficiente). Se nao existirem, cai pro PATH.
PT_DIR = os.path.join(BASE_DIR, "tools", "platform-tools")


def _tool(name):
    """Prefere o binario local em tools/platform-tools; senao usa o do PATH."""
    local = os.path.join(PT_DIR, name + ".exe")
    if os.path.isfile(local):
        return local
    found = shutil.which(name)
    return found or name


ADB = _tool("adb")
FASTBOOT = _tool("fastboot")


# --------------------------------------------------------------------------- #
# Helpers de processo (sem shell=True, com timeout)
# --------------------------------------------------------------------------- #
def which(tool):
    """Disponivel se houver binario local OU no PATH."""
    local = os.path.join(PT_DIR, tool + ".exe")
    if os.path.isfile(local):
        return local
    return shutil.which(tool)


def run(args, timeout=30):
    """Executa um comando e devolve (ok, stdout, stderr)."""
    try:
        p = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return False, "", f"'{args[0]}' nao encontrado no PATH."
    except subprocess.TimeoutExpired:
        return False, "", f"Tempo esgotado ({timeout}s)."
    except Exception as e:  # noqa
        return False, "", str(e)


def adb(*args, serial=None, timeout=30):
    base = [ADB]
    if serial:
        base += ["-s", serial]
    return run(base + list(args), timeout=timeout)


def fastboot(*args, serial=None, timeout=30):
    base = [FASTBOOT]
    if serial:
        base += ["-s", serial]
    return run(base + list(args), timeout=timeout)


# --------------------------------------------------------------------------- #
# Deteccao de aparelhos
# --------------------------------------------------------------------------- #
def list_devices():
    devices = []
    tools = {"adb": bool(which("adb")), "fastboot": bool(which("fastboot"))}

    if tools["adb"]:
        ok, out, _ = adb("devices", "-l")
        if ok:
            for line in out.splitlines()[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                serial = parts[0]
                state = parts[1] if len(parts) > 1 else "?"
                model = ""
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1].replace("_", " ")
                devices.append(
                    {"serial": serial, "mode": "adb", "state": state, "model": model}
                )

    if tools["fastboot"]:
        ok, out, err = fastboot("devices")
        blob = (out + "\n" + err).strip()
        for line in blob.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            serial = parts[0]
            devices.append(
                {"serial": serial, "mode": "fastboot", "state": "fastboot", "model": ""}
            )

    # Modos acessados so por USB (EDL / BROM / Preloader / Download / Diag).
    # adb/fastboot ja cobrem seus modos; aqui entram os de flash profundo.
    if tutorials is not None:
        try:
            usb = tutorials.detect_usb()
            flash_modes = {"edl", "brom", "preloader", "download", "diag"}
            for d in usb.get("devices", []):
                mode = d.get("mode")
                if mode in flash_modes:
                    devices.append({
                        "serial": f"{d['brand']} [{d['vid']}:{d['pid']}]",
                        "mode": mode,
                        "state": mode,
                        "model": f"{d['brand']} (USB)",
                    })
        except Exception:  # noqa
            pass

    return {"tools": tools, "devices": devices}


# Chipsets Qualcomm (ro.board.platform mais comuns) para classificar em adb.
_QC_PLATFORMS = {
    "msmnile", "kona", "lahaina", "taro", "kalama", "lito", "bengal", "holi",
    "trinket", "sdm660", "sdm845", "sm6150", "sm8150", "sm8250", "sm8350",
    "sm8450", "sm8550", "sm8650", "parrot", "crow", "pineapple", "cliffs",
}


def detect_compat():
    """Diz se o aparelho conectado e compativel com cada backend (edl/mtk)."""
    res = {"edl": None, "mtk": None, "chipset": None, "mode": None, "brand": None}

    # 1) Modos acessados por USB (sinal mais forte de chipset).
    if tutorials is not None:
        try:
            for d in tutorials.detect_usb().get("devices", []):
                m, b = d.get("mode"), d.get("brand")
                if m in ("edl", "diag") or b == "Qualcomm":
                    res["edl"] = True
                    res["mode"], res["brand"] = m or res["mode"], b
                if m in ("brom", "preloader") or b == "MediaTek":
                    res["mtk"] = True
                    res["mode"], res["brand"] = m or res["mode"], b
        except Exception:  # noqa
            pass

    # 2) Aparelho em adb: le o chipset pelas props.
    try:
        adbdev = next((x for x in list_devices()["devices"]
                       if x["mode"] == "adb" and x["state"] == "device"), None)
    except Exception:  # noqa
        adbdev = None
    if adbdev:
        ok, plat, _ = adb("shell", "getprop", "ro.board.platform",
                          serial=adbdev["serial"], timeout=10)
        ok2, hw, _ = adb("shell", "getprop", "ro.hardware",
                         serial=adbdev["serial"], timeout=10)
        plat = (plat or "").strip().lower()
        hw = (hw or "").strip().lower()
        res["chipset"] = plat or hw or None
        res["mode"] = res["mode"] or "adb"
        blob = f"{plat} {hw}"
        is_qc = (plat in _QC_PLATFORMS or "qcom" in blob or "qualcomm" in blob
                 or plat.startswith("msm") or plat.startswith("sm")
                 or plat.startswith("sdm"))
        is_mtk = (plat.startswith("mt") or "mediatek" in blob or "mtk" in hw)
        if is_qc:
            res["edl"] = True
        if is_mtk:
            res["mtk"] = True
    return res


# --------------------------------------------------------------------------- #
# Leitura de info
# --------------------------------------------------------------------------- #
PROPS = {
    "Fabricante": "ro.product.manufacturer",
    "Modelo": "ro.product.model",
    "Dispositivo": "ro.product.device",
    "Marca": "ro.product.brand",
    "Android": "ro.build.version.release",
    "SDK": "ro.build.version.sdk",
    "Build": "ro.build.display.id",
    "Patch seguranca": "ro.build.version.security_patch",
    "Chipset (board)": "ro.board.platform",
    "Hardware": "ro.hardware",
    "CPU ABI": "ro.product.cpu.abi",
    "Serial HW": "ro.serialno",
    "Bootloader": "ro.bootloader",
    "Bootloader destravado": "ro.boot.flash.locked",
    "Modo verificado": "ro.boot.verifiedbootstate",
}


def read_info(serial, mode):
    info = {}
    if mode == "fastboot":
        for key, var in [
            ("Produto", "product"),
            ("Bootloader destravado", "unlocked"),
            ("Versao bootloader", "version-bootloader"),
            ("Versao baseband", "version-baseband"),
            ("Secure", "secure"),
            ("Serial", "serialno"),
        ]:
            ok, out, err = fastboot("getvar", var, serial=serial, timeout=15)
            blob = (err + out)  # fastboot escreve getvar no stderr
            m = re.search(rf"{re.escape(var)}:\s*(.*)", blob)
            info[key] = m.group(1).strip() if m else "-"
        return info

    # modo adb
    for label, prop in PROPS.items():
        ok, out, _ = adb("shell", "getprop", prop, serial=serial, timeout=15)
        info[label] = out if (ok and out) else "-"

    # bateria
    ok, out, _ = adb("shell", "dumpsys", "battery", serial=serial, timeout=15)
    if ok:
        lvl = re.search(r"level:\s*(\d+)", out)
        health = re.search(r"health:\s*(\d+)", out)
        temp = re.search(r"temperature:\s*(\d+)", out)
        if lvl:
            info["Bateria (%)"] = lvl.group(1)
        if temp:
            info["Temp. bateria (C)"] = f"{int(temp.group(1)) / 10:.1f}"
    return info


# --------------------------------------------------------------------------- #
# Diagnostico -> log HTML
# --------------------------------------------------------------------------- #
LOG_CSS = """
body{font-family:Segoe UI,Arial,sans-serif;background:#0f1419;color:#e6edf3;margin:0;padding:24px}
h1{color:#2dd4bf;margin:0 0 4px}
.sub{color:#8b98a5;margin:0 0 20px;font-size:13px}
table{border-collapse:collapse;width:100%;max-width:820px}
td,th{border:1px solid #243041;padding:7px 11px;text-align:left;font-size:13px}
th{background:#172230;color:#2dd4bf;width:230px}
.ok{color:#2dd4bf;font-weight:600}.warn{color:#fbbf24;font-weight:600}.err{color:#f87171;font-weight:600}
.foot{margin-top:18px;color:#5a6b7b;font-size:11px}
"""


def write_log(title, serial, rows):
    stamp = datetime.now().strftime("%Y.%m.%d %H.%M.%S")
    safe = re.sub(r"[^A-Za-z0-9 _-]", "", title)
    path = os.path.join(LOGS_DIR, f"LOG_{safe} [{stamp}].html")
    body = "".join(
        f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{APP_NAME} - {title}</title><style>{LOG_CSS}</style></head><body>
<h1>{APP_NAME}</h1>
<p class="sub">{title} &middot; {serial or '-'} &middot; {stamp}</p>
<table>{body}</table>
<p class="foot">Gerado por {APP_NAME} v{VERSION} - {APP_FULL}</p>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.basename(path)


def diagnose(serial, mode):
    rows = []
    rows.append(("Modo de conexao", mode))
    rows.append(("Serial", serial))

    if mode == "adb":
        ok, out, _ = adb("get-state", serial=serial, timeout=10)
        rows.append(("Estado adb", out or "desconhecido"))
        ok, out, _ = adb("shell", "echo", "OGSM", serial=serial, timeout=10)
        rows.append(("Shell responde", "Sim" if (ok and "OGSM" in out) else "Nao"))
        info = read_info(serial, mode)
        for k, v in info.items():
            rows.append((k, v))
    else:
        info = read_info(serial, mode)
        for k, v in info.items():
            rows.append((k, v))

    log_file = write_log("Diagnostico", serial, rows)
    return {"rows": rows, "log": log_file}


# --------------------------------------------------------------------------- #
# Backup (apenas o que e acessivel sem root)
# --------------------------------------------------------------------------- #
def backup(serial):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"{serial}_{stamp}")
    os.makedirs(dest, exist_ok=True)
    results = []
    for remote, name in [
        ("/sdcard/DCIM", "DCIM"),
        ("/sdcard/Download", "Download"),
        ("/sdcard/Pictures", "Pictures"),
    ]:
        ok, out, err = adb("pull", remote, os.path.join(dest, name),
                           serial=serial, timeout=600)
        results.append({"item": name, "ok": ok, "msg": (err or out)[:200]})
    return {"dest": dest, "results": results}

# --------------------------------------------------------------------------- #
# Operações extras (adb / fastboot)  — todas legítimas, ferramentas abertas
# --------------------------------------------------------------------------- #
def run_bytes(args, timeout=120):
    """Como run(), mas devolve stdout em BYTES (p/ screenshot/dump)."""
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return p.returncode == 0, p.stdout, (p.stderr or b"").decode("latin1", "ignore")
    except Exception as e:  # noqa
        return False, b"", str(e)


def _stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ---- Lote 1: adb ----
def screenshot(serial):
    ok, png, err = run_bytes([ADB, "-s", serial, "exec-out", "screencap", "-p"], timeout=30)
    if not ok or not png:
        return {"ok": False, "msg": err or "falha ao capturar"}
    path = os.path.join(SHOT_DIR, f"shot_{serial}_{_stamp()}.png")
    with open(path, "wb") as f:
        f.write(png)
    return {"ok": True, "path": path, "msg": os.path.basename(path)}


def capture_logcat(serial):
    ok, out, err = adb("logcat", "-d", "-v", "time", serial=serial, timeout=60)
    path = os.path.join(LOGS_DIR, f"logcat_{serial}_{_stamp()}.txt")
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write(out or err)
    return {"ok": ok, "path": path, "lines": (out or "").count("\n"),
            "msg": os.path.basename(path)}


def props_dump(serial):
    ok, out, err = adb("shell", "getprop", serial=serial, timeout=20)
    path = os.path.join(LOGS_DIR, f"props_{serial}_{_stamp()}.txt")
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write(out or err)
    return {"ok": ok, "path": path, "msg": os.path.basename(path)}


def pull_path(serial, remote):
    dest = os.path.join(BACKUP_DIR, f"{serial}_{_stamp()}", os.path.basename(remote.rstrip("/")) or "pull")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    ok, out, err = adb("pull", remote, dest, serial=serial, timeout=1200)
    return {"ok": ok, "dest": dest, "msg": (err or out)[:300]}


def install_apk(serial, apk):
    ok, out, err = adb("install", "-r", apk, serial=serial, timeout=600)
    return {"ok": ok and "Success" in (out + err), "msg": (out or err)[:300]}


def uninstall_pkg(serial, pkg):
    ok, out, err = adb("uninstall", pkg, serial=serial, timeout=60)
    return {"ok": ok and "Success" in (out + err), "msg": (out or err)[:200]}


def list_packages(serial):
    ok, out, _ = adb("shell", "pm", "list", "packages", serial=serial, timeout=30)
    pkgs = sorted(l.replace("package:", "").strip() for l in (out or "").splitlines() if l.strip())
    return {"ok": ok, "packages": pkgs[:1000], "count": len(pkgs)}


def sideload(serial, zip_path):
    ok, out, err = adb("sideload", zip_path, serial=serial, timeout=3600)
    return {"ok": ok, "msg": (err or out)[:400]}


# ---- Lote 2: fastboot (bootloader destravado) ----
def fb_flash(serial, partition, image):
    ok, out, err = fastboot("flash", partition, image, serial=serial, timeout=1800)
    return {"ok": ok, "msg": (err or out)[:500]}


def fb_erase(serial, partition):
    ok, out, err = fastboot("erase", partition, serial=serial, timeout=120)
    return {"ok": ok, "msg": (err or out)[:300]}


def fb_set_unlock(serial, unlock=True):
    verb = "unlock" if unlock else "lock"
    # tenta os dois esquemas (novo 'flashing' e antigo 'oem')
    ok, out, err = fastboot("flashing", verb, serial=serial, timeout=60)
    if not ok:
        ok, out, err = fastboot("oem", verb, serial=serial, timeout=60)
    return {"ok": ok, "msg": (err or out)[:300] or "confirme no aparelho"}


# (A interface nativa usa estas funções direto via app.py — sem servidor HTTP.)
