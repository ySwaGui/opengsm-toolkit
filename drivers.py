# -*- coding: utf-8 -*-
"""
OpenGSM Toolkit :: instalador de drivers (original).

- Drivers OPEN-SOURCE / OFICIAIS ficam embutidos na pasta e instalam automatico
  (com UAC): Google USB Driver, UsbDk (Qualcomm/MTK via libusb), Zadig (WinUSB).
- Drivers de FABRICANTE (sem link oficial direto estavel) NAO sao baixados de
  mirrors piratas — o instalador abre a PAGINA OFICIAL da marca pra baixar.

Nada aqui repackageia driver proprietario de terceiros.
"""

import os
import subprocess
import sys

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DRV_DIR = os.path.join(BASE_DIR, "tools", "drivers")

GOOGLE_INF = os.path.join(DRV_DIR, "google", "usb_driver", "android_winusb.inf")
USBDK_MSI = os.path.join(DRV_DIR, "UsbDk_x64.msi")
ZADIG_EXE = os.path.join(DRV_DIR, "zadig.exe")
USBDK_INSTALLED = r"C:\Program Files\UsbDk Runtime Library\UsbDkController.exe"


# --------------------------------------------------------------------------- #
# Registro dos drivers
# --------------------------------------------------------------------------- #
# kind: "auto"  -> instala automatico (elevado)
#       "tool"  -> abre ferramenta (Zadig)
#       "link"  -> abre pagina oficial da marca
DRIVERS = [
    {
        "id": "google", "kind": "auto", "group": "Base",
        "name": "Google USB Driver (ADB / Fastboot)",
        "desc": "Driver WinUSB genérico — cobre ADB e Fastboot na maioria dos aparelhos.",
    },
    {
        "id": "usbdk", "kind": "auto", "group": "Base",
        "name": "UsbDk — Qualcomm (EDL 9008) e MediaTek (BROM/Preloader)",
        "desc": "Runtime libusb usado pelo edl/mtkclient pra falar com o aparelho.",
    },
    {
        "id": "zadig", "kind": "tool", "group": "Base",
        "name": "Zadig (WinUSB manual por aparelho)",
        "desc": "Abre o Zadig pra instalar WinUSB num aparelho específico, quando necessário.",
    },
    # --- Fabricantes: pagina oficial (download direto deles) ---
    {"id": "samsung", "kind": "link", "group": "Fabricantes",
     "name": "Samsung USB Driver", "url": "https://developer.samsung.com/android-usb-driver"},
    {"id": "huawei", "kind": "link", "group": "Fabricantes",
     "name": "Huawei (HiSuite)", "url": "https://consumer.huawei.com/en/support/hisuite/"},
    {"id": "motorola", "kind": "link", "group": "Fabricantes",
     "name": "Motorola (Rescue and Smart Assistant)",
     "url": "https://www.motorola.com/us/rescue-and-smart-assistant/p"},
    {"id": "lg", "kind": "link", "group": "Fabricantes",
     "name": "LG Mobile Driver",
     "url": "https://www.lg.com/us/support/help-library/lg-mobile-drivers-CT10000027-20150104174250"},
    {"id": "xiaomi", "kind": "link", "group": "Fabricantes",
     "name": "Xiaomi (Mi USB / Mi Flash)", "url": "https://xiaomiflashtool.com/"},
    {"id": "oppo", "kind": "link", "group": "Fabricantes",
     "name": "Oppo / Realme / OnePlus", "url": "https://support.oppo.com/"},
    {"id": "vivo", "kind": "link", "group": "Fabricantes",
     "name": "Vivo", "url": "https://www.vivo.com/en/support"},
]


# --------------------------------------------------------------------------- #
# Deteccao de status
# --------------------------------------------------------------------------- #
def _google_installed():
    try:
        p = subprocess.run(["pnputil", "/enum-drivers"], capture_output=True,
                           text=True, timeout=25, creationflags=CREATE_NO_WINDOW)
        return "android_winusb.inf" in (p.stdout or "").lower()
    except Exception:  # noqa
        return False


def status():
    """Lista os drivers com o estado atual (instalado / disponível)."""
    items = []
    for d in DRIVERS:
        st = None
        present = True
        if d["id"] == "google":
            st = "instalado" if _google_installed() else "não instalado"
            present = os.path.isfile(GOOGLE_INF)
        elif d["id"] == "usbdk":
            st = "instalado" if os.path.isfile(USBDK_INSTALLED) else "não instalado"
            present = os.path.isfile(USBDK_MSI)
        elif d["id"] == "zadig":
            present = os.path.isfile(ZADIG_EXE)
        item = dict(d)
        item["state"] = st
        item["present"] = present
        items.append(item)
    return items


# --------------------------------------------------------------------------- #
# Instalacao (elevada, com UAC) / abertura de pagina
# --------------------------------------------------------------------------- #
def _run_elevated(file, args):
    """Dispara um processo elevado (UAC) sem bloquear."""
    arglist = ",".join("'" + a.replace("'", "''") + "'" for a in args)
    ps = f"Start-Process -FilePath '{file}' -ArgumentList {arglist} -Verb RunAs"
    subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                     creationflags=CREATE_NO_WINDOW)


def _open_url(url):
    try:
        os.startfile(url)  # abre no navegador padrao
        return True
    except Exception:  # noqa
        subprocess.Popen(["cmd", "/c", "start", "", url], creationflags=CREATE_NO_WINDOW)
        return True


def install(driver_id):
    d = next((x for x in DRIVERS if x["id"] == driver_id), None)
    if not d:
        return {"ok": False, "msg": "driver desconhecido"}

    if d["kind"] == "link":
        _open_url(d["url"])
        return {"ok": True, "msg": f"Abri a página oficial da {d['name']}. Baixe e instale por lá."}

    if driver_id == "zadig":
        if not os.path.isfile(ZADIG_EXE):
            return {"ok": False, "msg": "zadig.exe não encontrado na pasta."}
        _run_elevated(ZADIG_EXE, [])
        return {"ok": True, "msg": "Zadig aberto (confirme o UAC). Selecione o aparelho e instale WinUSB."}

    if driver_id == "google":
        if not os.path.isfile(GOOGLE_INF):
            return {"ok": False, "msg": "INF do Google USB não encontrado."}
        _run_elevated("pnputil.exe", ["/add-driver", GOOGLE_INF, "/install"])
        return {"ok": True, "msg": "Instalando Google USB Driver (confirme o UAC)."}

    if driver_id == "usbdk":
        if not os.path.isfile(USBDK_MSI):
            return {"ok": False, "msg": "UsbDk_x64.msi não encontrado na pasta."}
        _run_elevated("msiexec.exe", ["/i", USBDK_MSI, "/qb"])
        return {"ok": True, "msg": "Instalando UsbDk (confirme o UAC)."}

    return {"ok": False, "msg": "ação não suportada"}
