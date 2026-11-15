# -*- coding: utf-8 -*-
"""
OpenGSM Toolkit :: backends avancados (EDL / MTK)

Este modulo NAO reimplementa nenhum protocolo proprietario. Ele apenas
*orquestra* ferramentas de codigo aberto ja instaladas no sistema:
  - mtkclient  (MediaTek BROM/Preloader/DA)  -> github.com/bkerler/mtkclient
  - edlclient  (Qualcomm Sahara/Firehose 9008)-> github.com/bkerler/edl

Toda a logica de baixo nivel vive nessas ferramentas (licenca aberta).
O OpenGSM Toolkit so chama a CLI delas e mostra o resultado na interface.
"""

import importlib.util
import os
import shutil
import subprocess
import sys

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Pasta base: ao lado do .exe quando empacotado, senao do script.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EDL_REPO = os.path.join(BASE_DIR, "tools", "edl")

# Python das ferramentas: SEMPRE o venv da pasta (pyenv). Dentro do .exe,
# sys.executable e o proprio .exe (nao serve pra '-m mtkclient'); por isso
# apontamos explicitamente pro Python isolado que tem os modulos.
_PYENV = os.path.join(BASE_DIR, "pyenv", "Scripts", "python.exe")
PY = _PYENV if os.path.isfile(_PYENV) else (sys.executable or "python")

# Torna o pacote edl importavel neste processo (quando nao empacotado).
if os.path.isdir(EDL_REPO) and EDL_REPO not in sys.path:
    sys.path.insert(0, EDL_REPO)


def _py_env():
    env = dict(os.environ)
    if os.path.isdir(EDL_REPO):
        env["PYTHONPATH"] = EDL_REPO + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _py_has_module(name):
    """Pergunta ao Python da pasta (PY) se o modulo existe — autoritativo,
    mesmo quando o app roda empacotado como .exe."""
    try:
        p = subprocess.run(
            [PY, "-c",
             f"import importlib.util as u,sys; sys.exit(0 if u.find_spec('{name}') else 1)"],
            capture_output=True, text=True, timeout=20, env=_py_env(),
            creationflags=CREATE_NO_WINDOW,
        )
        return p.returncode == 0
    except Exception:  # noqa
        return False


def _edl_repo_cli():
    for cand in ("edl.py", "edl"):
        p = os.path.join(EDL_REPO, cand)
        if os.path.isfile(p):
            return [PY, p]
    return None


def _has_module(name):
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:  # noqa
        return False


def _find_cli(names):
    """Procura um executavel de CLI no PATH (ex.: 'mtk', 'edl')."""
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def detect():
    """Retorna o estado dos backends abertos (instalado? como chamar?)."""
    backends = {}

    # ---- MTK (mtkclient) ----
    mtk_mod = _py_has_module("mtkclient")
    mtk_cli = _find_cli(["mtk", "mtk.py"])
    backends["mtk"] = {
        "name": "MediaTek (mtkclient)",
        "proto": "BROM / Preloader / DA",
        "installed": bool(mtk_mod or mtk_cli),
        "invoke": ([mtk_cli] if mtk_cli
                   else ([PY, "-m", "mtkclient.mtk"] if mtk_mod else None)),
        "project": "github.com/bkerler/mtkclient",
        "reason": None if (mtk_mod or mtk_cli) else "modulo mtkclient nao encontrado neste Python",
    }

    # ---- Qualcomm (edlclient) ----
    edl_mod = _py_has_module("edlclient")
    edl_cli = _find_cli(["edl", "edl.py"])
    edl_repo = _edl_repo_cli()
    # Preferir o script edl.py do repo local: funciona em subprocesso limpo,
    # sem depender de edlclient estar no sys.path (o -m so funciona no processo
    # que ja inseriu o repo no path).
    edl_invoke = (
        [edl_cli] if edl_cli
        else (edl_repo if edl_repo
              else ([PY, "-m", "edlclient.edl"] if edl_mod else None))
    )
    edl_ok = bool(edl_mod or edl_cli or edl_repo)
    backends["edl"] = {
        "name": "Qualcomm (edlclient)",
        "proto": "Sahara / Firehose (9008)",
        "installed": edl_ok,
        "invoke": edl_invoke,
        "project": "github.com/bkerler/edl",
        "reason": None if edl_ok else "repo tools/edl ausente e modulo nao instalado",
    }
    return backends


def _invoke_list(info):
    inv = info.get("invoke")
    if inv is None:
        return None
    return [inv] if isinstance(inv, str) else list(inv)


def run_command(backend_key, args, timeout=180):
    """
    Executa uma subacao da ferramenta aberta.
    backend_key: 'mtk' | 'edl'
    args: lista de argumentos (ex.: ['printgpt'] ou ['r','boot','boot.img'])
    """
    info = detect().get(backend_key)
    if not info or not info["installed"]:
        return {"ok": False, "out": "", "err": f"Backend '{backend_key}' nao instalado."}

    base = _invoke_list(info)
    if not base:
        return {"ok": False, "out": "", "err": "Nao foi possivel localizar a CLI."}

    env = dict(os.environ)
    if os.path.isdir(EDL_REPO):
        env["PYTHONPATH"] = EDL_REPO + os.pathsep + env.get("PYTHONPATH", "")
    try:
        p = subprocess.run(
            base + list(args),
            capture_output=True, text=True, timeout=timeout,
            creationflags=CREATE_NO_WINDOW, env=env,
        )
        return {
            "ok": p.returncode == 0,
            "out": (p.stdout or "")[-8000:],
            "err": (p.stderr or "")[-4000:],
            "cmd": " ".join(base + list(args)),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "out": "", "err": f"Tempo esgotado ({timeout}s)."}
    except Exception as e:  # noqa
        return {"ok": False, "out": "", "err": str(e)}


def run_tool(backend_key, args, loader="", timeout=1800):
    """Como run_command, mas aceita um loader fornecido pelo usuario (--loader).
    O loader e legitimo quando o tecnico tem direito de usa-lo no aparelho dele."""
    full = list(args)
    if loader:
        full += ["--loader", loader]
    return run_command(backend_key, full, timeout=timeout)


# Operacoes abertas por verbo. Tudo isto vem do mtkclient/edl (open-source);
# write/erase/unlock sao destrutivas -> a interface confirma antes.
def op(backend_key, verb, partition="", image="", loader="", outfile=""):
    b = backend_key
    if verb == "read":        # dump de particao (leitura)
        args = ["r", partition, outfile]
    elif verb == "write":     # grava imagem na particao
        args = ["w", partition, image]
    elif verb == "erase":     # apaga particao
        args = ["e", partition]
    elif verb == "reset":     # reinicia o aparelho
        args = ["reset"]
    elif verb == "unlock":    # destrava bootloader
        args = (["da", "seccfg", "unlock"] if b == "mtk" else ["oemunlock", "enable"])
    elif verb == "lock":      # retrava bootloader
        args = (["da", "seccfg", "lock"] if b == "mtk" else ["oemunlock", "disable"])
    elif verb == "frp":       # apaga a particao FRP (reset FRP em aparelho proprio)
        args = ["e", "frp"]
    else:
        return {"ok": False, "out": "", "err": f"verbo desconhecido: {verb}"}
    return run_tool(b, args, loader=loader)


# Acoes seguras pre-definidas (somente leitura / nao destrutivas por padrao)
SAFE_ACTIONS = {
    "mtk": {
        "gpt": ["printgpt"],          # le a tabela de particoes
        "info": ["gettargetconfig"],  # info do target BROM
    },
    "edl": {
        "gpt": ["printgpt"],          # le a tabela de particoes
        "info": ["memtbl"],           # tabela de memoria
    },
}


def dump_partition(backend_key, partition, outfile, timeout=1800):
    """Le (dump) uma particao pro arquivo — operacao de LEITURA, nao destrutiva.
    edl:  edl r <particao> <arquivo>
    mtk:  mtk r <particao> <arquivo>
    """
    if not partition or not outfile:
        return {"ok": False, "out": "", "err": "particao/arquivo ausente"}
    # 'r' = read em ambas as ferramentas (bkerler)
    return run_command(backend_key, ["r", partition, outfile], timeout=timeout)
