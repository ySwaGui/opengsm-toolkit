<!-- Tagline (English, for reach): Open-source Android service toolkit — ADB/Fastboot + MediaTek (mtkclient) & Qualcomm (edl), native app, no server. -->

# OpenGSM Toolkit — Open Android Service Toolkit

**Ferramenta aberta de serviço/diagnóstico de aparelhos Android.** Interface nativa
(sem navegador, sem servidor) que orquestra ferramentas **open-source** padrão da
indústria — `adb`, `fastboot`, [`mtkclient`](https://github.com/bkerler/mtkclient)
(MediaTek) e [`edl`](https://github.com/bkerler/edl) (Qualcomm) — num app só.

> ⚠️ **Uso responsável:** use apenas em aparelhos **seus** ou que você tem
> autorização para dar manutenção. Operações como destravar bootloader, apagar FRP
> ou gravar partições são de assistência técnica, não de burlar segurança alheia.

---

## O que faz

**Diagnóstico / leitura**
- 🔍 Ler info (modelo, chipset, Android, serial, bateria, bootloader)
- 🩺 Diagnóstico com log HTML · 🧾 `build.prop` · 📦 apps instalados
- 📷 Screenshot · 📜 Logcat · 📥 Puxar arquivos · 💾 Backup

**ADB / Fastboot**
- ↻ Reiniciar para system / bootloader / fastboot / recovery / download / **EDL** / sideload
- ➕/➖ Instalar/Desinstalar APK · ⬆️ Sideload de OTA
- ⚡ Flash de imagem · 🧹 Apagar FRP · 🔓/🔒 Unlock/Relock bootloader (fastboot)

**MediaTek (BROM/Preloader, via `mtkclient`)**
- 📑 Partições · ℹ️ Info · ⬇️ Dump · ✏️ Gravar · 🧽 Apagar
- 🔓 **Unlock de bootloader via `seccfg`** (método aberto, sem chave de fabricante)
- 🧹 Apagar FRP · ↻ Reiniciar · 📎 **loader DA fornecido por você**

**Qualcomm (EDL 9008, via `edl`)**
- 📑 Partições · ℹ️ Info · ⬇️ Dump · ✏️ Gravar · 🧽 Apagar · 🧹 FRP · ↻ Reiniciar
- 📎 **loader Firehose fornecido por você**

**Extras que as ferramentas de bancada geralmente não têm**
- 📘 **Guia de modos** embutido: passo a passo por marca (Samsung/Xiaomi/Moto/…) +
  **detecção pelo USB** (VID/PID) pra saber em que modo o aparelho está
- 🧩 **Instalador de drivers** (Google USB, UsbDk, Zadig automáticos; marcas via página oficial)
- 🟢 **Detecção automática** do aparelho conectado e das opções válidas pra cada modo

---

## "Faz quase tudo que os box-tools pagos fazem?"

**Nas operações do dia a dia e em aparelhos destraváveis por métodos abertos — sim,
cobre a grande maioria (~90%).** A base técnica é idêntica: mesmos protocolos
(BROM/DA no MediaTek, Sahara/Firehose no Qualcomm), mesmo transporte USB.

**Os ~10% que faltam — e por quê:** as ferramentas comerciais têm um **servidor pago**
que entrega *loaders assinados* e *bypass de autenticação* para chips **novos/seguros**.
Isso depende de **chaves privadas de fabricante**, **loaders proprietários** ou
**exploits fechados** — coisas que **não podem** entrar num projeto aberto (nem são
obtíveis legalmente). Por isso o OpenGSM Toolkit **não** reproduz essa parte: nela, nem um clone
resolveria sem pirataria. Para esses casos, use o **loader que você tem direito de usar**
(botão *Definir loader*).

Resumo honesto: **o teto de um app open source é até onde os exploits/loaders abertos
chegam — e o OpenGSM Toolkit vai até esse teto.**

---

## Instalação (Windows)

Requer **Python 3** e **Git** no PATH.

```powershell
git clone https://github.com/<seu-usuario>/<seu-repo>.git
cd <seu-repo>
powershell -ExecutionPolicy Bypass -File setup.ps1
```

O `setup.ps1` monta tudo **dentro da pasta** (ambiente isolado), sem sujar o sistema:
cria o venv `pyenv/`, instala `mtkclient`, clona o `edl`, e baixa `adb`/`fastboot`
(platform-tools) + drivers (UsbDk, Google USB, Zadig).

### Rodar
- **App nativo:** `pyenv\Scripts\python app.py` (ou gere o `.exe` com `build.ps1`)
- Conecte o aparelho por USB (Depuração USB ligada, ou modo fastboot/EDL/BROM)

---

## Construído sobre (créditos)

Este projeto **orquestra** e **credita** estes projetos open-source — todo o mérito do
baixo nível é deles:

- [mtkclient](https://github.com/bkerler/mtkclient) — MediaTek BROM/DA (GPLv3)
- [edl / edlclient](https://github.com/bkerler/edl) — Qualcomm Sahara/Firehose (GPLv3)
- [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) — adb/fastboot (Google)
- [UsbDk](https://github.com/daynix/UsbDk) · [Zadig](https://github.com/pbatard/libwdi) — drivers USB
- [pywebview](https://github.com/r0x0r/pywebview) — janela nativa

---

## Licença

**GPLv3** — por depender de `mtkclient`/`edl` (GPLv3), este projeto também é GPLv3.
Veja [`LICENSE`](LICENSE).

## Aviso legal

Software fornecido "como está", sem garantia. Operações de flash/unlock podem
**inutilizar o aparelho** ou **apagar dados**. O autor e os contribuidores não se
responsabilizam por mau uso. Use somente em aparelhos próprios ou autorizados, e de
acordo com as leis do seu país.
