# -*- coding: utf-8 -*-
"""
OpenGSM Toolkit :: base de tutoriais de modo + deteccao de aparelho por USB.

Conteudo informativo (como entrar em cada modo), por marca, mais um mapa
de assinaturas USB (VID/PID) pra detectar automaticamente marca e modo atual.
Nada aqui mexe no aparelho; e so informacao + leitura da lista de USB do Windows.
"""

import re
import subprocess

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# --------------------------------------------------------------------------- #
# Fabricantes por VID
# --------------------------------------------------------------------------- #
USB_VENDORS = {
    "05c6": "Qualcomm",
    "0e8d": "MediaTek",
    "18d1": "Google",
    "04e8": "Samsung",
    "2717": "Xiaomi",
    "2a70": "OnePlus",
    "22d9": "Oppo/Realme",
    "12d1": "Huawei",
    "22b8": "Motorola",
    "1004": "LG",
    "0bb4": "HTC",
    "19d2": "ZTE",
    "1bbb": "Alcatel/TCL",
    "2916": "Yulong",
    "0fce": "Sony",
    "2ae5": "Fairphone",
}

# Assinaturas de MODO por (vid, pid). Valor = chave do modo.
MODE_SIGNATURES = {
    ("05c6", "9008"): "edl",        # Qualcomm EDL / QDLoader 9008
    ("05c6", "900e"): "diag",       # Qualcomm Diag 900E (quase-EDL)
    ("05c6", "9006"): "edl",        # QDLoader alternativo
    ("0e8d", "0003"): "brom",       # MediaTek BROM
    ("0e8d", "2000"): "preloader",  # MediaTek Preloader
    ("0e8d", "2001"): "preloader",  # MediaTek Preloader (variante)
    ("18d1", "4ee0"): "fastboot",   # Google/AOSP fastboot
    ("18d1", "d00d"): "fastboot",   # fastbootd
    ("18d1", "4ee7"): "adb",
    ("04e8", "685d"): "adb",        # Samsung ADB (download usa outro ID por modelo)
    ("04e8", "6601"): "download",   # Samsung Download (Odin) antigo
}

# --------------------------------------------------------------------------- #
# Modos: passos genericos + por marca + comandos de software + verificacao
# --------------------------------------------------------------------------- #
MODES = {
    "edl": {
        "name": "EDL (9008) — Qualcomm",
        "desc": "Emergency Download. Porta 'Qualcomm HS-USB QDLoader 9008' no Gerenciador de Dispositivos.",
        "software": [
            "adb reboot edl  (precisa de Depuracao USB; bloqueado em muitas MIUI)",
            "fastboot oem edl   ou   fastboot reboot edl  (precisa de fastboot, as vezes bootloader destravado)",
        ],
        "generic": [
            "Desligue o aparelho completamente.",
            "Segure Volume (+) e Volume (-) ao mesmo tempo.",
            "Sem soltar, conecte o cabo USB no PC.",
            "A tela fica preta e surge 'Qualcomm HS-USB QDLoader 9008' no Windows.",
        ],
        "brands": {
            "Xiaomi": [
                "Em muitos modelos o 'adb reboot edl' nao funciona (MIUI).",
                "Desligue, segure Vol (+) e Vol (-), conecte o USB.",
                "Modelos travados: usar cabo EDL (deep flash) ou test point na placa.",
            ],
            "OnePlus/Oppo/Realme": [
                "Desligue; quando sentir a vibracao ao conectar, segure Vol (+) e Vol (-).",
                "Alguns aceitam 'fastboot reboot edl' com bootloader destravado.",
            ],
            "Motorola": [
                "Via fastboot: 'fastboot oem edl' ou 'fastboot reboot edl'.",
                "Por botoes: desligar, segurar Vol (+) + Vol (-), conectar USB.",
            ],
        },
        "testpoint": "Ultimo recurso: abrir o aparelho e curto-circuitar o test point de EDL ao GND enquanto conecta o USB. Arriscado — pode danificar a placa.",
        "verify": "Gerenciador de Dispositivos → Portas → 'Qualcomm HS-USB QDLoader 9008'.",
        "warning": "Em aparelho ligado e com bateria ok. Loader assinado pode ser exigido em modelos novos.",
    },
    "brom": {
        "name": "BROM — MediaTek",
        "desc": "Boot ROM (acesso mais profundo que Preloader). USB 0E8D:0003.",
        "software": ["Rode o comando da ferramenta ANTES e so entao conecte o aparelho desligado."],
        "generic": [
            "Desligue o aparelho totalmente (segure Power ~10s).",
            "Inicie a acao na ferramenta (ela fica 'aguardando aparelho').",
            "Segure Volume (+) e Volume (-) no aparelho desligado.",
            "Sem soltar, conecte o cabo USB.",
        ],
        "brands": {
            "Xiaomi": ["Desligado, segurar ambos os volumes e conectar. Secure-boot pode exigir test point."],
            "Oppo/Realme": ["Desligado, segurar ambos os volumes e conectar enquanto a ferramenta aguarda."],
        },
        "testpoint": "Modelos com secure-boot: curto do test point BROM ao GND enquanto conecta o USB (ferramenta ja aguardando).",
        "verify": "Aparece 'MediaTek USB Port' (BROM) / VID 0E8D PID 0003.",
        "warning": "A janela do Preloader dura ~2s; tenha a ferramenta aguardando antes de conectar.",
    },
    "preloader": {
        "name": "Preloader — MediaTek",
        "desc": "Primeiro estagio do MTK. USB 0E8D:2000. Janela curta (~2s) ao conectar.",
        "software": ["Deixe a ferramenta aguardando e conecte o aparelho desligado."],
        "generic": [
            "Desligue o aparelho completamente.",
            "Deixe a ferramenta (mtkclient) 'aguardando aparelho'.",
            "Apenas conecte o cabo USB — o Preloader aparece por ~2 segundos.",
            "Se nao pegar, segure Vol (-) enquanto conecta.",
        ],
        "brands": {},
        "testpoint": None,
        "verify": "'MediaTek PreLoader USB VCOM' / VID 0E8D PID 2000.",
        "warning": "Instale o driver 'MediaTek PreLoader USB VCOM' antes.",
    },
    "fastboot": {
        "name": "Fastboot / Bootloader",
        "desc": "Modo de gravacao por fastboot. (Samsung nao tem fastboot — usa Download.)",
        "software": ["adb reboot bootloader"],
        "generic": [
            "Desligue o aparelho.",
            "Segure Volume (-) + Power juntos.",
            "Solte ao aparecer a tela FASTBOOT / bootloader.",
            "Conecte o USB. Confirme com: fastboot devices",
        ],
        "brands": {
            "Xiaomi": ["Desligar; segurar Vol (-) + Power ate aparecer o coelhinho FASTBOOT."],
            "Motorola": ["Desligar; segurar Vol (-) + Power; navegar com volume, confirmar com Power."],
            "Google": ["Desligar; segurar Vol (-) + Power."],
            "Samsung": ["Samsung nao tem fastboot. Use o modo Download (Odin)."],
        },
        "testpoint": None,
        "verify": "Comando 'fastboot devices' lista o serial.",
        "warning": None,
    },
    "download": {
        "name": "Download / Odin — Samsung",
        "desc": "Modo de flash da Samsung (usado pelo Odin).",
        "software": ["adb reboot download"],
        "generic": [
            "Desligue o aparelho.",
            "Modelos novos (USB-C, sem Home/Bixby): segure Vol (+) e Vol (-) juntos e conecte o USB.",
            "Na tela de aviso, pressione Volume (+) para continuar.",
        ],
        "brands": {
            "Samsung": [
                "Novos (sem Home/Bixby): desligar, segurar Vol(+)+Vol(-), conectar USB, Vol(+) confirma.",
                "Com tecla Bixby (S8–S10): Vol(-) + Bixby + Power.",
                "Com botao Home (antigos): Vol(-) + Home + Power.",
            ],
        },
        "testpoint": None,
        "verify": "Tela azul 'Downloading...' no aparelho; Odin mostra porta COM.",
        "warning": "Atualizacoes recentes da Samsung mudaram o combo em alguns modelos; confira o do seu.",
    },
    "recovery": {
        "name": "Recovery",
        "desc": "Modo de recuperacao do Android.",
        "software": ["adb reboot recovery"],
        "generic": [
            "Desligue o aparelho.",
            "Segure Volume (+) + Power.",
            "Solte ao aparecer o logo / menu de recovery.",
        ],
        "brands": {
            "Samsung": ["Vol(+) + (Bixby/Home) + Power, conforme o modelo."],
            "Xiaomi": ["Vol(+) + Power ate o logo da Mi."],
        },
        "testpoint": None,
        "verify": "Menu de recovery na tela do aparelho.",
        "warning": None,
    },
}

# Mapa: qual modo cada backend precisa (pra ligar o tutorial certo)
BACKEND_MODE = {
    "mtk": ["preloader", "brom"],
    "edl": ["edl"],
}

# O que da pra fazer em CADA modo (o app mostra so o que vale pro aparelho).
#   kind "core"    -> acao interna (info/diag/backup/reboot/flash)
#   kind "backend" -> chama mtk/edl (backend + action)
_MTK_READS = [
    {"id": "mtk_gpt", "label": "📑 Ler partições", "kind": "backend", "backend": "mtk", "action": "gpt"},
    {"id": "mtk_info", "label": "ℹ️ Info target", "kind": "backend", "backend": "mtk", "action": "info"},
    {"id": "mtk_dump", "label": "⬇️ Dump partição", "kind": "dump", "backend": "mtk"},
    {"id": "mtk_unlock", "label": "🔓 Unlock bootloader", "kind": "op2", "backend": "mtk", "verb": "unlock", "danger": True},
    {"id": "mtk_lock", "label": "🔒 Lock bootloader", "kind": "op2", "backend": "mtk", "verb": "lock", "danger": True},
    {"id": "mtk_write", "label": "✏️ Gravar partição", "kind": "op2", "backend": "mtk", "verb": "write", "danger": True},
    {"id": "mtk_erase", "label": "🧽 Apagar partição", "kind": "op2", "backend": "mtk", "verb": "erase", "danger": True},
    {"id": "mtk_frp", "label": "🧹 Apagar FRP", "kind": "op2", "backend": "mtk", "verb": "frp", "danger": True},
    {"id": "mtk_reset", "label": "↻ Reiniciar", "kind": "op2", "backend": "mtk", "verb": "reset"},
    {"id": "mtk_loader", "label": "📎 Definir loader", "kind": "loader", "backend": "mtk"},
]
_EDL_ADV = [
    {"id": "edl_gpt", "label": "📑 Ler partições", "kind": "backend", "backend": "edl", "action": "gpt"},
    {"id": "edl_info", "label": "ℹ️ Info target", "kind": "backend", "backend": "edl", "action": "info"},
    {"id": "edl_dump", "label": "⬇️ Dump partição", "kind": "dump", "backend": "edl"},
    {"id": "edl_write", "label": "✏️ Gravar partição", "kind": "op2", "backend": "edl", "verb": "write", "danger": True},
    {"id": "edl_erase", "label": "🧽 Apagar partição", "kind": "op2", "backend": "edl", "verb": "erase", "danger": True},
    {"id": "edl_frp", "label": "🧹 Apagar FRP", "kind": "op2", "backend": "edl", "verb": "frp", "danger": True},
    {"id": "edl_reset", "label": "↻ Reiniciar", "kind": "op2", "backend": "edl", "verb": "reset"},
    {"id": "edl_loader", "label": "📎 Definir loader", "kind": "loader", "backend": "edl"},
]
MODE_ACTIONS = {
    "adb": [
        {"id": "info", "label": "🔍 Ler info", "kind": "core"},
        {"id": "diag", "label": "🩺 Diagnóstico", "kind": "core"},
        {"id": "screenshot", "label": "📷 Screenshot", "kind": "core"},
        {"id": "logcat", "label": "📜 Logcat", "kind": "core"},
        {"id": "props", "label": "🧾 build.prop", "kind": "core"},
        {"id": "packages", "label": "📦 Apps instalados", "kind": "core"},
        {"id": "apk_install", "label": "➕ Instalar APK", "kind": "core"},
        {"id": "apk_uninstall", "label": "➖ Desinstalar app", "kind": "core"},
        {"id": "pull", "label": "📥 Puxar arquivos", "kind": "core"},
        {"id": "backup", "label": "💾 Backup", "kind": "core"},
        {"id": "sideload", "label": "⬆️ Sideload OTA", "kind": "core", "danger": True},
        {"id": "reboot", "label": "↻ Reiniciar", "kind": "core"},
    ],
    "fastboot": [
        {"id": "info", "label": "🔍 Ler info", "kind": "core"},
        {"id": "fb_flash", "label": "⚡ Flash imagem", "kind": "core", "danger": True},
        {"id": "fb_erase_frp", "label": "🧹 Apagar FRP", "kind": "core", "danger": True},
        {"id": "fb_unlock", "label": "🔓 Destravar bootloader", "kind": "core", "danger": True},
        {"id": "fb_lock", "label": "🔒 Retravar bootloader", "kind": "core", "danger": True},
        {"id": "reboot", "label": "↻ Reiniciar", "kind": "core"},
    ],
    "edl": list(_EDL_ADV),
    "brom": list(_MTK_READS),
    "preloader": list(_MTK_READS),
    "diag": [
        {"id": "edl_info", "label": "ℹ️ Info target", "kind": "backend", "backend": "edl", "action": "info"},
    ],
    "download": [],   # modo de flash Samsung — use ferramenta Odin externa
}

BRANDS = ["Xiaomi", "Samsung", "Motorola", "OnePlus/Oppo/Realme", "Oppo/Realme",
          "Google", "Huawei", "LG", "Sony", "Outro"]


# --------------------------------------------------------------------------- #
# Deteccao por USB (le a lista de dispositivos do Windows)
# --------------------------------------------------------------------------- #
def detect_usb():
    """Le os dispositivos USB presentes e tenta identificar marca e modo."""
    found = []
    try:
        ps = (
            "Get-CimInstance Win32_PnPEntity | "
            "Where-Object { $_.DeviceID -like 'USB*VID_*' } | "
            "Select-Object -ExpandProperty DeviceID"
        )
        p = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=20,
            creationflags=CREATE_NO_WINDOW,
        )
        ids = p.stdout
    except Exception as e:  # noqa
        return {"ok": False, "err": str(e), "devices": []}

    seen = set()
    for line in ids.splitlines():
        m = re.search(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", line)
        if not m:
            continue
        vid = m.group(1).lower()
        pid = m.group(2).lower()
        key = (vid, pid)
        if key in seen:
            continue
        seen.add(key)
        if vid not in USB_VENDORS:
            continue  # ignora USB que nao e de celular conhecido
        found.append({
            "vid": vid,
            "pid": pid,
            "brand": USB_VENDORS.get(vid, "?"),
            "mode": MODE_SIGNATURES.get(key),  # None se nao for um modo conhecido
        })
    return {"ok": True, "devices": found}
