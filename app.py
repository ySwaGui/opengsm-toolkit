# -*- coding: utf-8 -*-
"""
OpenGSM Toolkit :: app nativo (SEM servidor).

Janela nativa (pywebview). A interface fala direto com o Python pela API do
pywebview (window.pywebview.api) — não há servidor HTTP nem porta aberta.
Empacotado com PyInstaller vira o OpenGSM Toolkit.exe.
"""

import os
import sys

import webview

import server as core  # lógica (adb/fastboot/info/diag/backup/compat)
import backends
import tutorials
import drivers

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_INDEX = os.path.join(BASE_DIR, "ui", "index.html")


class Api:
    """Métodos chamados pela interface via window.pywebview.api.*"""

    # ---- info geral ----
    def meta(self):
        return {"app": core.APP_NAME, "full": core.APP_FULL, "version": core.VERSION}

    def devices(self):
        return core.list_devices()

    def info(self, serial="", mode="adb"):
        return {"info": core.read_info(serial, mode)}

    def logs(self):
        try:
            files = sorted(os.listdir(core.LOGS_DIR), reverse=True)
        except Exception:  # noqa
            files = []
        return {"logs": files[:50]}

    def compat(self):
        return core.detect_compat()

    # ---- ações no aparelho ----
    def diag(self, serial="", mode="adb"):
        return core.diagnose(serial, mode)

    def backup(self, serial=""):
        return core.backup(serial)

    def reboot(self, serial="", mode="adb", target="system"):
        if mode == "fastboot":
            if target == "edl":
                ok, out, err = core.fastboot("oem", "edl", serial=serial, timeout=25)
            else:
                tgt = {"bootloader": ["bootloader"], "recovery": ["recovery"]}.get(target, [])
                ok, out, err = core.fastboot("reboot", *tgt, serial=serial, timeout=25)
        else:
            arg = {"system": [], "bootloader": ["bootloader"], "fastboot": ["bootloader"],
                   "recovery": ["recovery"], "download": ["download"],
                   "edl": ["edl"], "sideload": ["sideload"]}.get(target, [])
            ok, out, err = core.adb("reboot", *arg, serial=serial, timeout=25)
        return {"ok": ok, "msg": err or out or "ok"}

    # ---- Lote 1 (adb) ----
    def screenshot(self, serial=""):
        return core.screenshot(serial)

    def logcat(self, serial=""):
        return core.capture_logcat(serial)

    def props(self, serial=""):
        return core.props_dump(serial)

    def pull(self, serial="", remote="/sdcard/"):
        return core.pull_path(serial, remote)

    def packages(self, serial=""):
        return core.list_packages(serial)

    def install_apk(self, serial="", apk=""):
        if not apk:
            apk = self._pick(("APK (*.apk)",))
            if not apk:
                return {"ok": False, "msg": "cancelado"}
        return core.install_apk(serial, apk)

    def uninstall(self, serial="", pkg=""):
        return core.uninstall_pkg(serial, pkg)

    def sideload(self, serial="", zip=""):
        if not zip:
            zip = self._pick(("OTA/ZIP (*.zip)",))
            if not zip:
                return {"ok": False, "msg": "cancelado"}
        return core.sideload(serial, zip)

    # ---- Lote 2 (fastboot) ----
    def fb_flash(self, serial="", partition="", image=""):
        if not partition:
            return {"ok": False, "msg": "informe a partição (ex.: boot)"}
        if not image:
            image = self._pick(("Imagem (*.img *.bin *.mbn);;Todos (*.*)",))
            if not image:
                return {"ok": False, "msg": "cancelado"}
        return core.fb_flash(serial, partition, image)

    def fb_erase(self, serial="", partition=""):
        return core.fb_erase(serial, partition)

    def fb_unlock(self, serial="", unlock=True):
        return core.fb_set_unlock(serial, unlock)

    # ---- EDL/MTK dump (leitura) ----
    def dump(self, backend="", partition="", serial=""):
        if not partition:
            return {"ok": False, "err": "informe a partição"}
        import os
        out = os.path.join(core.DUMP_DIR, f"{backend}_{partition}_{core._stamp()}.img")
        res = backends.dump_partition(backend, partition, out)
        res["dest"] = out
        return res

    # ---- operações abertas genéricas (edl/mtk): read/write/erase/unlock/lock/reset/frp ----
    def backend_op(self, backend="", verb="", partition="", loader="", serial=""):
        import os
        if verb in ("write", "read", "erase") and not partition:
            return {"ok": False, "err": "informe a partição"}
        if verb == "read":
            out = os.path.join(core.DUMP_DIR, f"{backend}_{partition}_{core._stamp()}.img")
            r = backends.op(backend, "read", partition=partition, outfile=out, loader=loader)
            r["dest"] = out
            return r
        image = ""
        if verb == "write":
            image = self._pick(("Imagem (*.img *.bin *.mbn);;Todos (*.*)",))
            if not image:
                return {"ok": False, "err": "cancelado (sem imagem)"}
        return backends.op(backend, verb, partition=partition, image=image, loader=loader)

    def pick_loader(self):
        return self._pick(("Loader DA/Firehose (*.bin *.mbn *.elf);;Todos (*.*)",))

    # ---- seletor de arquivo nativo ----
    def _pick(self, file_types=()):
        try:
            import webview
            w = webview.windows[0]
            r = w.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False,
                                     file_types=file_types or ("Todos (*.*)",))
            if r:
                return r[0] if isinstance(r, (list, tuple)) else r
        except Exception:  # noqa
            pass
        return ""

    # ---- backends abertos (edl/mtk) ----
    def backends(self):
        return {"available": True, "backends": backends.detect()}

    def backend_run(self, backend="", action="", serial=""):
        acts = backends.SAFE_ACTIONS.get(backend, {})
        if action not in acts:
            return {"ok": False, "err": f"acao '{action}' nao permitida"}
        res = backends.run_command(backend, acts[action])
        try:
            core.write_log(f"{backend}-{action}", serial,
                           [("comando", res.get("cmd", "")),
                            ("ok", res.get("ok")),
                            ("saida", (res.get("out", "") or res.get("err", ""))[:4000])])
        except Exception:  # noqa
            pass
        return res

    # ---- tutoriais / usb ----
    def tutorials(self):
        return {
            "available": True,
            "modes": tutorials.MODES,
            "brands": tutorials.BRANDS,
            "backend_mode": tutorials.BACKEND_MODE,
            "mode_actions": tutorials.MODE_ACTIONS,
        }

    def usb(self):
        return tutorials.detect_usb()

    # ---- drivers ----
    def drivers(self):
        return {"available": True, "drivers": drivers.status()}

    def drivers_install(self, id=""):
        return drivers.install(id)


def main():
    api = Api()
    webview.create_window(
        f"OpenGSM Toolkit — {core.APP_FULL}",
        url=UI_INDEX,
        js_api=api,
        width=1040, height=740, min_size=(880, 600),
        background_color="#0f1419",
    )
    webview.start()


if __name__ == "__main__":
    main()
