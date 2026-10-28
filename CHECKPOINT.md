# Ponto de restauração — FreeBuds Client

**Data:** 2026-10-28  
**Estado:** Fase 1 e Fase 2 concluídas e validadas em hardware. Em **2026-10-28** a UI PySide6 foi redesenhada no estilo HarmonyOS/HUAWEI Audio Connect: rail lateral, páginas Visão geral, Áudio, Gestos, Conexão e Diagnóstico, cartões amplos, segment controls e pastilhas de bateria no hero. O painel de ANC mantém o Reconhecimento adaptável de 11 níveis. Suíte com **89 testes automatizados passando**, Ruff e compileall limpos. Faltam DPI alto, suspensão/retomada e teste de desconexão física de enlace.  
**Para retomar:** use o prompt sugerido no final deste arquivo.

> Este documento não contém o MAC real, seriais ou capturas completas com dados
> pessoais. Use placeholders ao repetir os testes.

---

## 1. Resumo executivo

O núcleo, a CLI e a documentação de engenharia reversa estão prontos. A validação
real foi feita com um **HUAWEI FreeBuds Pro 5** no canal RFCOMM `1`:

- listagem e conexão SPP: OK;
- handshake `0x0107`: OK;
- bateria `0x0108`: OK;
- ANC `0x2B2A`: OK nos modos normal, cancelamento e transparência;
- Reconhecimento adaptável: identificado no nível `4` da transparência, com 11
  níveis no parâmetro `2` (`0x00..0x0A`);
- notificações de mudança de ANC: chegam como `0x2B2A` espontâneo, **não** como
  `0x2B03` neste firmware.

A Fase 2 já foi codificada: `core/client.py`, UI PySide6, bandeja, worker de
polling/reconexão, configurações e testes offscreen. Notificações espontâneas
recebidas entre os ciclos acordam o worker, que lê um snapshot imediatamente, e
são registradas no log; TLVs desconhecidos são preservados em hexadecimal. Em
**2026-10-23** a UI foi validada com o FreeBuds Pro 5 conectado ao PC e ao celular
ao mesmo tempo: conexão no canal `1`, bateria, ANC normal, notificação de
cancelamento, atualização sob demanda, reconexão lógica, bandeja e
fechar-para-bandeja funcionaram. A escrita de ANC (`0x2B04`) foi validada no
mesmo dia para os três modos, níveis de cancelamento e os 11 níveis do
Reconhecimento adaptável, com restauração do estado. A UI foi redesenhada com
fundo preto, foto transparente dos fones e controles de ANC; o fluxo adaptativo
foi exercitado por automação com o fone real e uma captura de tela foi conferida.

### Validação da UI em 2026-10-23

- Conexão SPP no canal `1` com o fone conectado também ao celular.
- Bateria lida: `100/100/100`, estojo `79`, flags `00 00 00`, sem carga.
- ANC normal (`00 00`) exibido corretamente; o código de padding `0` não é mais
  mostrado como nível desconhecido.
- Notificação espontânea de cancelamento (`0x2B2A`, `03 01`) capturada e
  registrada na UI; o snapshot passou para cancelamento/dinâmico.
- Notificações desconhecidas (`01 06`, `0x2BAC` e outras) preservadas em hex.
- “Atualizar agora”, desconectar/reconectar e fechar para a bandeja funcionaram.
- Bandeja disponível, com tooltip de bateria/ANC, e reabertura da janela OK.
- Escrita de ANC validada por script no hardware: modos `00 00`, `01 FF`,
  `02 02` e `02 04`, além de níveis de cancelamento; o estado foi restaurado ao
  final.
- Reconhecimento adaptável validado no fone: seleção do modo, slider nos níveis
  1/6/11 (bruto `00/05/0A`) e retorno à transparência padrão/normal.
- Fluxo da UI adaptável validado por automação com o fone real: botão
  **Adaptável**, slider, leitura confirmada e restauração; captura conferida em
  1200×980.
- Ainda faltam DPI alto, suspensão/retomada e uma perda real de enlace (o teste
  de reconexão parou e reiniciou o worker, sem desligar o fone).

### Redesign da UI em 2026-10-28

As capturas do HUAWEI Audio Connect usadas como referência local (não
versionadas) serviram de base para uma revisão visual completa, adaptada para
janela desktop:

- rail lateral fixo com marca, navegação, seleção de dispositivo e conectar;
- páginas **Visão geral**, **Áudio**, **Gestos**, **Conexão** e **Diagnóstico**
  em um `QStackedWidget` com coluna central de largura máxima;
- hero de 282 px com foto transparente, brilho discreto e pastilhas verticais de
  bateria desenhadas em `QPainter`;
- cartões de 24 px, hero de 28 px, separadores de 1 px e três níveis tipográficos;
- segment control de ruído com os SVGs fornecidos, chips de nível e slider
  adaptativo em um painel que recalcula a altura do cartão;
- ícones de recursos migrados para os SVGs fornecidos nas referências locais
  (copiados para `src/freebuds/ui/assets/icons`), dentro das molduras
  circulares coloridas dos cartões e atalhos, com tintura azul/cinza nos
  estados de ruído e áudio espacial;
- pastilhas de bateria com anel, ícone de fone/estojo e porcentagem alinhados
  ao centro;
- popups de seleção com cantos arredondados, seleção em pílula e largura
  calculada pelo maior item;
- cabeçalhos de cartão alinhados ao topo em grades com alturas diferentes e
  folga vertical extra no cartão de ANC para evitar texto cortado;
- switches, chips e combos com pintura própria; a marca, a bandeja e a navegação
  continuam desenhadas em `QPainter`;
- estados conectado, desconectado e adaptável conferidos por renderização
  offscreen em 1320×880 e 1100×760;
- nova cobertura de navegação entre páginas e dos atalhos da visão geral,
  elevando a suíte a 89 testes.

---

## 2. Ambiente e instalação

- Windows 10/11, Python **3.14.7** na `.venv`.
- Pacote instalado em modo editable: `freebuds-client 0.1.0`.
- Console scripts: `freebuds` e `freebuds-ui`.
- PySide6 **6.12.0** instalado via `pip install -e ".[ui]"`.
- O `pyproject.toml` agora declara `PySide6-Essentials>=6.7`, suficiente para
  QtCore/QtGui/QtWidgets.
- Não é um repositório git; não há commits.
- O projeto fica em uma pasta local; os caminhos abaixo são relativos.

Ativar a venv:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ou usar o Python diretamente:

```powershell
.\.venv\Scripts\python.exe ...
```

---

## 3. Verificação rápida

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\freebuds.exe --version
```

Estado atual:

- **89 testes passando**.
- `ruff check src tests`: sem erros.
- `compileall`: sem erros.
- `freebuds --version`: `freebuds 0.1.0`.
- UI executada offscreen e com a plataforma Windows usando `WA_DontShowOnScreen`;
  layout conferido em 1320×880 e 1100×760, com rolagem automática em janelas menores.
- UI validada com o FreeBuds Pro 5 em 2026-10-23: conexão, bateria, ANC,
  notificação espontânea, atualização, reconexão lógica, bandeja e fluxo
  adaptável por automação.
- Recursos avançados em páginas (Áudio, Gestos e Conexão) implementados e cobertos
  por testes unitários e de integração com a UI.
- Escrita de ANC, Reconhecimento adaptável e comandos avançados validados no
  hardware; o worker acorda com notificações e atualiza o snapshot sem esperar o
  polling.
- Temporários de captura HCI, bugreports e processos/forwards ADB limpos com
  sucesso.
- Com Bluetooth desligado, a UI registra “Bluetooth indisponível” e continua
  aberta, sem travar.

Teste de importação do PySide6 (o primeiro teste feito nesta sessão falhou sem
mensagem, mas o segundo funcionou; se repetir, investigar antes de assumir falha
do código):

```powershell
.\.venv\Scripts\python.exe -c "from PySide6 import QtCore; print(QtCore.qVersion())"
```

---

## 4. O que foi validado no hardware

Dispositivo usado nos testes (dados não sensíveis):

| Item | Valor |
|---|---|
| Nome no Windows | HUAWEI FreeBuds Pro 5 |
| Modelo interno (`0x0F`) | `BTFT0023` |
| Submodelo (`0x0A`) | `BTFT0023-00016D` |
| Hardware (`0x03`) | `HL1SAKM2_Ver.A` |
| Firmware (`0x07`) | HarmonyOS 7.0.0.350 (F003H003C91) |
| Canal RFCOMM | `1` |
| MAC | usar `<MAC_DO_FONE>` nos exemplos; não publicar |
| Seriais | redigidos; não publicar |

### 4.1. Bateria

Comando: `0x0108`, pedindo os parâmetros `1`, `2` e `3` vazios.

Exemplo de resposta real (snapshot, valores mudam com o uso):

```text
RX 5A 00 1B 00 01 08 01 01 53 02 03 53 53 45 03 03 01 01 01
   04 02 0A 14 05 02 01 01 06 01 0A 9F 73
```

- `param 1` = `53` → 83% global.
- `param 2` = `53 53 45` → 83% / 83% / 69% (L/R/estojo).
- `param 3` = `01 01 01` → flags; o cliente marca `charging = true`.
- `param 4` = `0A 14`, `param 5` = `01 01`, `param 6` = `0A` → desconhecidos,
  preservados como brutos.

Em outra leitura, com os fones fora do estojo e só o estojo carregando, as flags
vieram `00 00 01`. Isso é compatível com flags L/R/estojo, mas **não foi
confirmado**; o código não interpreta cada byte individualmente.

### 4.2. ANC

Comando: `0x2B2A`, pedindo os parâmetros `1` e `2`.

| Modo | Resposta real | Parâmetro `1` | Interpretação |
|---|---|---|---|
| Normal | `5A 00 0A 00 2B 2A 01 02 00 00 02 01 00 E8 E6` | `00 00` | nível 0, modo 0 |
| Cancelamento | `5A 00 0A 00 2B 2A 01 02 03 01 02 01 00 70 80` | `03 01` | nível 3 = dynamic, modo 1 |
| Transparência adaptável | `5A 00 0A 00 2B 2A 01 02 04 02 02 01 00 8C 88` | `04 02` | Reconhecimento adaptável; posição no parâmetro `2` |

O código `4` é o **Reconhecimento adaptável**. O parâmetro `2` traz a posição
bruta `0x00..0x0A`, apresentada pela UI como `1..11` (1 = mais ruído, 6 =
padrão, 11 = menos ruído). O valor só é exposto como `adaptive_level` quando o
modo é transparência e o nível é `4`; nos outros modos ele pode persistir sem
significado ativo. Para voltar à transparência padrão, a UI envia `[2, 2]`, pois
`[2, FF]` reabre o último submode e pode manter o adaptável.

### 4.3. Notificações

Durante uma escuta de 50 s, alternando o ANC pelos gestos, o fone enviou **oito
notificações `0x2B2A` espontâneas**, com o mesmo formato da resposta de leitura.
**Não foi enviado `0x2B03`** neste firmware.

Também apareceu uma notificação `0x2BAC` no início, com TLVs `1..11` e valores
majoritariamente `01`/`00`; ela permaneceu estática e não está relacionada às
mudanças de ANC. O significado é desconhecido.

### 4.4. Escrita de ANC — `0x2B04`

Formato validado no FreeBuds Pro 5 em 2026-10-23 (com base no OpenFreebuds):

| Operação | Parâmetros | Exemplo |
|---|---|---|
| Modo normal | `1 = [0, 0x00]` | `00 00` |
| Modo cancelamento | `1 = [1, 0xFF]` | `01 FF` |
| Transparência (último submode) | `1 = [2, 0xFF]` | `02 FF` |
| Transparência padrão | `1 = [2, 2]` | `02 02` |
| Nível do modo ativo | `1 = [modo_ativo, nível]` | `01 03` = cancelamento/dinâmico |
| Ativar Reconhecimento adaptável | `1 = [2, 4]` | `02 04` |
| Intensidade adaptativa | `1 = [2, 4]`, `3 = 01`, `4 = [0x00..0x0A]` | nível 6 = `05` |

O fone confirmou os três modos, os níveis de cancelamento e os 11 níveis do
Reconhecimento adaptável. O eco `0x2B04` foi observado com `TLV 2 = 00` (aceito),
normalmente seguido por um push `0x2B2A` com o novo estado. O firmware confirma
antes de publicar o estado novo; por isso o cliente relê o ANC até o alvo
aparecer, com limite de tempo. Se não confirmar, a UI mantém o estado anterior e
reporta o erro. Enviar a posição no TLV `2` é ignorado; a intensidade vai no TLV
`4`.

### 4.5. Campos de identificação

A resposta de `0x0107` trouxe 14 TLVs. Campos conhecidos: `0x03`, `0x07`, `0x09`,
`0x0A`, `0x0F`, `0x18`. O campo `0x20` contém o endereço Bluetooth local
invertido (6 bytes). Os campos `0x02`, `0x19`, `0x1B`, `0x1D`, `0x1E`, `0x21` e
`0x22` continuam sem significado confirmado e são preservados como hex.

---

## 5. Código e documentação já prontos

### Núcleo

- `src/freebuds/core/protocol.py` — quadro `0x5A`, TLV, CRC16/XMODEM, parser
  incremental.
- `src/freebuds/core/commands.py` — builders e decodificação. Ajuste recente:
  campos desconhecidos de `0x0107` são exibidos como hex, sem tentar GBK em bytes
  binários; `INFO_TEXT_FIELDS` limita a decodificação de texto aos campos
  conhecidos.
- `src/freebuds/core/client.py` — cliente de alto nível: canais, handshake,
  snapshot de bateria/ANC, escrita de ANC com confirmação do estado, intensidade
  adaptativa, avisos e cancelamento de conexão.
- `src/freebuds/core/transport.py` — socket RFCOMM/SPP.
- `src/freebuds/core/session.py` — thread leitora, correlação e notificações.
- `src/freebuds/core/windows_bt.py` — enumeração, inquiry e pareamento.
- `src/freebuds/core/models.py` — dataclasses.
- `src/freebuds/config/settings.py` — JSON atômico em
  `%APPDATA%\FreeBudsClient\settings.json`; agora inclui `poll_interval` e
  `close_to_tray`.
- `src/freebuds/cli/app.py` — CLI `list`, `scan`, `pair`, `probe`, `decode`, `ui`.

### UI (Fase 2)

- `src/freebuds/ui/app.py` — `QApplication`, tema e entrada `freebuds-ui`.
- `src/freebuds/ui/main_window.py` — janela, seleção de dispositivo, polling,
  log, controles de ANC, bandeja e encerramento.
- `src/freebuds/ui/worker.py` — `DeviceWorker` e `ScanWorker` em `QThread`;
  `DeviceWorker` enfileira escritas de ANC/adaptativo e acorda com notificações.
- `src/freebuds/ui/widgets.py` — hero com foto transparente, cartões de bateria,
  painel de ANC com modos/níveis, botão **Adaptável**, slider de 11 níveis,
  detalhes e log.
- `src/freebuds/ui/tray.py` — `QSystemTrayIcon` e menu.
- `src/freebuds/ui/theme.py` — stylesheet preto/premium.
- `src/freebuds/ui/icons.py` — ícones desenhados com `QPainter`.
- `src/freebuds/ui/assets/freebuds_pro_5.png` — foto do produto com fundo
  transparente (ativo ilustrativo; substituir antes de distribuir).
- `pyproject.toml` — extra `ui` com `PySide6-Essentials`, script `freebuds-ui` e
  inclusão dos assets no pacote.
- Testes offscreen em `tests/test_ui_smoke.py`; cliente em
  `tests/test_client.py`; sessão/notificações em `tests/test_session.py`.

### Ajustes recentes na CLI

- `probe --address` resolve o nome amigável do Windows (ex.: “HUAWEI FreeBuds Pro
  5”) em vez de mostrar apenas o codename interno.
- `_print_info` mostra campos desconhecidos como hex.
- Bateria e ANC mostram “Extras brutos” para parâmetros não interpretados.
- `--listen` mostra um resumo de TLVs para notificações desconhecidas e um resumo
  semântico para ANC.
- Novo teste de CLI cobre a impressão de notificação de ANC.
- Subcomando `freebuds ui`, com importação tardia de PySide6; falha com mensagem
  amigável se o extra `ui` não estiver instalado.
- `_channel_order` agora usa `core.client.resolve_channels`.

### Documentação

- `README.md` — visão geral, instalação, CLI, UI, validação em hardware e
  limitações.
- `docs/PROTOCOL.md` — protocolo, capturas reais, campos, bateria, ANC,
  notificações e lacunas.
- `docs/ARCHITECTURE.md` — camadas, threading, fluxo da UI e roadmap.
- `docs/CAPTURE_GUIDE.md` — captura Android/HCI e correlação.

---

## 6. Fase 2 — implementada em código (plano original abaixo)

> **Status em 2026-10-23:** o plano desta seção foi executado e depois evoluído.
> A UI existe em `src/freebuds/ui/`, o cliente de alto nível em `core/client.py`,
> as preferências foram estendidas e a suíte tem 72 testes. A escrita de ANC e o
> Reconhecimento adaptável foram validados no hardware, a UI foi redesenhada e o
> worker acorda com notificações. Faltam DPI alto, suspensão/retomada, perda real
> de enlace e confirmar a notificação adaptativa vinda do celular. Use as seções
> 7 a 10 para retomar. O texto abaixo é histórico do plano original; onde ele
> disser “somente leitura”, vale a exceção de ANC já validada.

### Objetivo da Fase 2

Entregar uma UI desktop em PySide6, em português, com bandeja do sistema,
consumindo o núcleo sem duplicar protocolo. A UI lê bateria, ANC, informações do
dispositivo e notificações, e envia **apenas** a escrita de ANC já validada.
Outras escritas continuam desabilitadas até validação por captura.

### Arquitetura implementada

```text
src/freebuds/
  core/
    client.py        # cliente de alto nível reutilizável pela UI
  ui/
    app.py           # QApplication, tema, launch
    main_window.py   # janela principal
    worker.py        # QThread de conexão/polling e scan
    widgets.py       # cartões de bateria, painel ANC, log, detalhes
    tray.py          # QSystemTrayIcon e menu
    theme.py         # stylesheet dark
    icons.py         # ícones desenhados com QPainter
```

### `core/client.py`

Implementado como camada de alto nível para a UI:

- `resolve_channels(address, requested, saved_channel, settings_channels)` —
  reutilizar a lógica de ordem de canais da CLI.
- `FreeBudsClient`:
  - `connect() -> ConnectionInfo` — tenta canais, faz handshake e mantém a
    sessão aberta.
  - `read_snapshot() -> DeviceSnapshot` — lê bateria e ANC, opcionalmente escuta
    notificações, preserva warnings e `parser_issues`.
  - `close()` idempotente.
  - `DeviceSnapshot` com `info`, `battery`, `anc`, `notifications`, `warnings`,
    `parser_issues` e `timestamp`.
- A CLI pode continuar como está; refatorar `_probe_one_channel` para usar o
  cliente fica para depois, se valer a pena.

### Worker

- `DeviceWorker(QThread)`:
  - conecta com `FreeBudsClient`, emite `connected`, `snapshot_ready`, `failed` e
    `action_failed`;
  - polling padrão de 30 s, ajustável (15/30/60/120 s), como verificação de
    segurança;
  - acorda com notificações `0x2B2A` e com o botão “Atualizar agora”;
  - processa a fila de escritas de ANC na própria thread;
  - fecha a sessão em `finally`;
  - tenta reconectar após falha (ex.: 10–15 s).
- `ScanWorker(QThread)`:
  - executa `enumerate_devices(include_unknown=True, issue_inquiry=True,
    inquiry_seconds=8)`;
  - emite a lista de dispositivos;
  - a UI mantém referência até `finished`.

Não salvar settings dentro do worker. A UI salva o canal em `connected` para
evitar corrida entre escritores do JSON.

### Janela principal

Layout sugerido:

- cabeçalho com “FreeBuds”, subtítulo e pill de conexão;
- barra de dispositivo: combo de pareados, “Procurar”, “Atualizar lista”,
  “Conectar/Desconectar”;
- cartões de bateria: global, esquerda, direita, estojo, com barras e flags
  brutas;
- painel de ANC: modo atual, nível, botões/chips e botão **Adaptável** com
  slider de 11 níveis, habilitados quando há sessão, com níveis de
  cancelamento/transparência conhecidos;
- detalhes: modelo, submodelo, firmware, hardware, canal, última atualização;
- log de atividade com erros/avisos e mudanças de ANC;
- rodapé: intervalo de polling, “Fechar para a bandeja”, “Atualizar agora”.

Tema: preto/premium, acentos em champanhe e verde suave, português, fontes Segoe
UI/Consolas. Não exibir seriais no painel principal por padrão.

### Bandeja

- `QSystemTrayIcon` com ícone desenhado (bateria + indicador de ANC).
- Tooltip com nome, bateria L/R/estojo e modo ANC.
- Menu: Abrir, status, Atualizar agora, Sair.
- Duplo clique abre a janela.
- Fechar a janela pode esconder para a bandeja; “Sair” encerra de verdade.
- Parar o worker em `aboutToQuit`/`shutdown`.

### Configurações

Adicionar a `Settings`:

- `poll_interval: float = 30.0` (sanitizar entre 5 e 3600);
- `close_to_tray: bool = True`.

Salvar em `%APPDATA%\FreeBudsClient\settings.json` junto com os campos atuais.
Adicionar testes de sanitização.

### Entrada da UI

- `freebuds ui [--address <MAC>] [--settings <arquivo>]` na CLI.
- Console script `freebuds-ui` em `pyproject.toml`.
- `ui/app.py` deve falhar com mensagem amigável se PySide6 não estiver instalado.
- `python -m freebuds ui` também deve funcionar.

### Testes implementados

- `tests/test_client.py`: ordem/deduplicação de canais, conexão e snapshot com
  transporte/sessão simulados, incluindo notificações espontâneas mais novas que
  a resposta de polling; `set_anc`, confirmação do estado e
  `set_anc_adaptive_level`.
- `tests/test_settings.py`: `poll_interval`, `close_to_tray` e sanitização.
- `tests/test_ui_smoke.py`: com `QT_QPA_PLATFORM=offscreen`, criar
  `QApplication` + `MainWindow(settings_path=tmp_path/...)`, renderizar um
  snapshot sintético e verificar bateria/ANC; o log de notificações é testado sem
  reescrever o snapshot lido e o padding normal não vira nível desconhecido.
  Também cobre os sinais de modo/nível do `AncPanel`, o modo adaptável, o slider
  de 11 níveis e as ações da janela. Pula se PySide6 ausente.
- `tests/test_commands.py`: builders de escrita de ANC, intensidade adaptativa no
  TLV `4`, decodificação e validação de entradas.
- `tests/test_session.py`: espera por notificações, predicado de parada e fila.
- Suíte total: **72 testes passando**.

### Escopo que NÃO entra agora

- EQ, áudio espacial, HUAWEI SOUND/áudio adaptável de volume, gestos,
  multiponto, wear detection, fit test, find buds e demais escritas ainda sem
  captura.
- Atualização de firmware.
- Pareamento automático sem o assistente do Windows.
- Captura Android/HCI integrada à UI.

---

## 7. Comandos úteis para amanhã

### Sem fone / sem hardware

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m compileall -q src tests
```

### Com o fone ligado, fora do estojo e pareado

```powershell
.\.venv\Scripts\freebuds.exe list
.\.venv\Scripts\freebuds.exe scan --seconds 8
.\.venv\Scripts\freebuds.exe probe --address <MAC_DO_FONE> --raw
.\.venv\Scripts\freebuds.exe probe --address <MAC_DO_FONE> --listen 20 --raw
```

Durante `--listen`, alterne o ANC nos gestos para capturar as notificações
`0x2B2A`.

### Comandos da UI

```powershell
.\.venv\Scripts\freebuds.exe ui
.\.venv\Scripts\freebuds.exe ui --address <MAC_DO_FONE>
.\.venv\Scripts\freebuds-ui.exe
```

A UI abre mesmo com o Bluetooth desligado; ela mostra o erro no log e deixa o
botão Conectar desabilitado.

---

## 8. Decisões e restrições que devem ser mantidas

- Python + PySide6; o `core` **não** importa Qt.
- Comunicação por Bluetooth Classic SPP/RFCOMM, UUID
  `00001101-0000-1000-8000-00805F9B34FB`.
- Formato Huawei: `0x5A` + tamanho + comando + TLV + CRC16/XMODEM.
- Canais conhecidos: `1` (Pro/Pro 2/Pro 3/Pro 5/6i) e `16` (4i/5i).
- Pareamento pelo assistente/SSP do Windows, sem contornar PIN/passkey.
- `probe` é somente leitura; a UI envia apenas as escritas de ANC já validadas,
  incluindo o Reconhecimento adaptável.
- A UI escreve somente depois de uma ação explícita e mantém o estado anterior em
  caso de timeout, com releitura e reversão pelo snapshot seguinte.
- Dados desconhecidos são preservados como brutos/hex; não inventar semântica.
- Não implementar atualização de firmware por engenharia reversa.
- Não publicar MAC completo, seriais ou capturas com dados pessoais.
- Baixo consumo: polling com timer/evento, sem loop ocupado.

---

## 9. Pendências conhecidas

1. Validar DPI alto e suspensão/retomada do Windows com a UI conectada.
2. Validar reconexão após o fone ser desligado/religado ou sair do alcance.
3. Confirmar a notificação espontânea do nível adaptativo quando o slider é
   movido pelo celular, sem usar “Atualizar agora”.
4. Confirmar os nomes dos níveis de cancelamento (Padrão/Conforto/Ultra/Dinâmico)
   em outros firmwares.
5. Validar pareamento do zero em outro PC/dispositivo.
6. Observar notificações de bateria `0x0127` e entender `0x2BAC`; houve um burst
   de notificações desconhecidas quando o app do celular sincronizou, preservado
   apenas como hex.
7. Investigar escrita segura de multiponto sem risco de desconectar o outro
   dispositivo ou mantê-la como leitura conforme decisão atual.
8. Refatorar o fluxo de `probe` da CLI para usar `FreeBudsClient` completamente,
   se isso simplificar o diagnóstico sem perder os detalhes de `--raw`.
9. Repetir a validação de ANC e recursos avançados em outros modelos e
   firmwares e preencher a tabela de `docs/PROTOCOL.md`.

---

## 10. Prompt sugerido para retomar

Copie e cole:

> Retome o FreeBuds Client a partir do `CHECKPOINT.md`. A Fase 2 está completa
> com a UI HarmonyOS redesenhada (rail, páginas de Áudio, Gestos, Conexão e
> Diagnóstico), foto transparente, escrita de ANC/adaptativo e 89 testes
> passando. Temporários de captura HCI e processos ADB foram limpos. Confira o
> estado com `pytest`, `ruff` e `compileall`. Em seguida valide DPI alto,
> suspensão/retomada e reconexão após perda real de enlace. Mantenha a UI em
> português e o núcleo sem Qt. Não publique MACs, seriais ou dados do celular.
> Ao final, diga o que falta para a próxima fase.

---

**Fim do ponto de restauração.**

