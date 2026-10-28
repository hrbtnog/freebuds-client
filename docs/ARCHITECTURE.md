# Arquitetura

## 1. Objetivo

O FreeBuds Client é um cliente desktop não oficial para fones HUAWEI no Windows.
A Fase 1 entrega um núcleo testável, uma CLI de diagnóstico e documentação de
protocolo. A Fase 2 adiciona uma UI PySide6 com bandeja, reutilizando o mesmo
núcleo sem reescrever a comunicação.

> **Validação:** em 2026-10-21 o fluxo `list` → `probe` foi executado com um
> FreeBuds Pro 5 no canal `1`. Handshake, bateria e os três modos de ANC
> responderam. Em 2026-10-23 a UI foi validada com o fone conectado ao PC e ao
> celular ao mesmo tempo: conexão, bateria, ANC, notificação espontânea,
> atualização, reconexão lógica, bandeja e fechar-para-bandeja funcionaram. A
> escrita de ANC (`0x2B04`) foi validada no hardware para os três modos, os
> níveis de cancelamento e os 11 níveis do Reconhecimento adaptável, com
> restauração do estado. O fluxo adaptativo da UI também foi exercitado por
> automação com o fone real. Ainda faltam DPI alto, suspensão/retomada, perda
> real de enlace e confirmar a notificação adaptativa vinda do celular. Veja os
> detalhes em [`PROTOCOL.md`](PROTOCOL.md#4-comandos-implementados).

Princípios:

- o núcleo não importa Qt, não abre janelas e não depende da CLI;
- o codec e os modelos são puros e testáveis sem Bluetooth;
- Windows fica isolado em `core/windows_bt.py` e `core/transport.py`;
- escritas só são enviadas com comando confirmado, confirmação do fone e
  possibilidade de reverter; nesta versão, apenas ANC;
- o parser preserva dados desconhecidos em vez de inventar semântica;
- o polling da UI usa eventos/timers, sem loop ocupado, e a sessão é encerrada
  ao sair.

## 2. Camadas

```text
┌───────────────────────────────┐   ┌─────────────────────────────┐
│ CLI (cli/app.py)              │   │ UI PySide6 + tray (ui/)     │
│ descoberta, probe, decode     │   │ janela, snapshots, bandeja  │
└───────────────┬───────────────┘   └──────────────┬──────────────┘
                │                                  │
                ▼                                  ▼
┌───────────────────────────────┐   ┌─────────────────────────────┐
│ core/client.py                │◄──│ ui/worker.py (QThread)      │
│ canais, handshake, snapshot   │   │ polling, refresh, reconexão │
└───────────────┬───────────────┘   └─────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐   ┌─────────────────────────────┐
│ HuaweiSession                 │   │ config/settings.py          │
│ thread leitora, correlação    │   │ JSON atômico em AppData     │
└───────────────┬───────────────┘   └─────────────────────────────┘
                ▼
┌───────────────────────────────┐
│ RfcommTransport + Windows BT  │
│ socket RFCOMM, ctypes         │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│ Protocolo e comandos          │
│ 0x5A/TLV/CRC; 0107/0108/2B2A  │
└───────────────────────────────┘
```

### `core/protocol.py`

Não conhece dispositivo, Windows ou Qt. Responsabilidades:

- calcular CRC16/XMODEM;
- montar e decodificar o envelope `0x5A`;
- validar tamanho, magic, byte reservado, TLVs e CRC;
- parser incremental que tolera fragmentação, concatenação, lixo e perda de
  sincronização;
- retornar um `HuaweiFrame` com bytes brutos, parâmetros e indicador de CRC.

### `core/commands.py`

Mapeia IDs e layouts conhecidos para os modelos. Os builders e decoders cobrem
leitura e escrita de ANC (`0x2B04`), perfis HUAWEI SOUND (`0x2B49`/`0x2B4A`),
áudio espacial e recursos de áudio (`0x2BB4`), detecção de uso (`0x2B10`/`0x2B11`),
qualidade de som (`0x2BA2`/`0x2BA3`), modo de baixa latência (`0x2B6C`) e
gestos (`0x2B16`/`17`, `0x2B92`/`93`, `0x011F`/`20`, `0x0125`/`26`). Recursos
como deslizar (`0x2B19`) e multiponto (`0x2B2F`) contam com decodificadores
estritamente de leitura.

### `core/client.py`

Camada de alto nível reutilizada pela UI:

- `resolve_channels()` centraliza a ordem “canal salvo → configuração → canais
  conhecidos” e remove duplicatas;
- `FreeBudsClient.connect()` tenta os canais, valida o SPP com `0x0107` e
  mantém a sessão aberta;
- `read_snapshot(include_advanced=True)` lê bateria, ANC e configurações
  avançadas (`read_advanced()`), coleta avisos, problemas do parser e
  notificações espontâneas, e devolve um `DeviceSnapshot`;
- setters síncronos com confirmação (`_confirm_advanced()` e `_confirm_anc_state()`):
  `set_sound_profile()`, `set_spatial_mode()`, `set_adaptive_volume()`,
  `set_conversation_awareness()`, `set_one_earbud_anc()`, `set_head_control()`,
  `set_wear_detection()`, `set_sound_quality()`, `set_low_latency()`,
  `set_press_hold()`, `set_pinch_hold()`, `set_double_tap()`, `set_triple_tap()`;
- notificações recebidas entre ciclos são mescladas no snapshot e no estado
  avançado; a sequência do quadro impede que uma notificação antiga sobrescreva
  a resposta de polling mais nova;
- `close()` é idempotente;
- `connect(should_stop=...)` permite cancelar entre tentativas de canal quando
  a UI está encerrando.

A CLI ainda mantém seu fluxo de diagnóstico detalhado, mas usa o mesmo
`resolve_channels()`.

### `core/models.py`

Dataclasses de `BluetoothDevice`, `DeviceInfo`, `BatteryState`, `AncState` e
`AdvancedSettings`.
- `AncState` inclui `adaptive_level` (posição bruta `0..10`, exibida como `1..11`)
  quando o Reconhecimento adaptável está ativo;
- `AdvancedSettings` armazena equalização, áudio espacial, recursos inteligentes,
  gestos configurados e parâmetros brutos em `raw`.
Todos os modelos expõem `to_dict()`, com bytes brutos convertidos para hex para
que a CLI/UI possam serializar sem perder informação.

### `core/transport.py`

Cria um socket `AF_BLUETOOTH`/`SOCK_STREAM`/`BTPROTO_RFCOMM` e conecta ao canal
informado. Erros Winsock comuns (10050, 10060, 10061 etc.) são traduzidos para
mensagens em português com orientação de diagnóstico. O módulo não tenta
descobrir o canal por SDP ainda.

### `core/session.py`

Uma thread daemon lê o socket continuamente e alimenta o `FrameParser`. Uma
requisição por vez é serializada por um lock; a resposta é correlacionada pelo
eco do comando. Notificações não solicitadas ficam num histórico curto e numa
fila própria, consumida por `take_notification_frames()`/`take_notifications()`;
`frames_since()`/`wait_for_frames()` continuam disponíveis para diagnóstico.

Propriedades importantes:

- a UI nunca deve bloquear a thread leitora;
- callbacks `on_frame` são executados na thread leitora;
- exceções de callback são guardadas, não derrubam a sessão;
- a UI entrega eventos à thread Qt via sinais;
- o histórico atual é limitado a 1024 quadros; a fila de notificações, a 256;
- respostas correlacionadas não entram na fila de notificações, evitando que a
  UI confunda um eco de comando com uma mudança espontânea.

### `core/windows_bt.py`

Integração via `ctypes` com `bthprops.cpl`:

- `BluetoothFindFirstRadio`/`FindNextRadio`: descobre rádios;
- `BluetoothFindFirstDevice`/`FindNextDevice`: enumera dispositivos clássicos;
- `BluetoothAuthenticateDeviceEx`: abre o fluxo de autenticação/SSP do Windows.

Não há dependência de `winrt`/`pywin32`. O pareamento nunca captura nem contorna
PIN/passkey; o Windows conduz a UI. A enumeração depende do rádio Bluetooth
clássico estar ativo.

### `config/settings.py`

Preferências em:

```text
%APPDATA%\FreeBudsClient\settings.json
```

O caminho pode ser alterado com `--settings ARQUIVO`. O arquivo é gravado de
forma atômica. Se estiver corrompido, a CLI avisa, usa padrões e **não
sobrescreve** o arquivo automaticamente. O canal que funcionou é memorizado por
endereço para acelerar o próximo `probe`.

### `cli/app.py`

Comandos:

| Comando | Responsabilidade |
|---|---|
| `list` | dispositivos clássicos lembrados/pareados/conectados |
| `scan` | inquiry e filtro por nome Huawei/HONOR/FreeBuds |
| `pair` | descoberta opcional + autenticação assistida pelo Windows |
| `probe` | handshake, bateria, ANC e escuta de notificações, somente leitura |
| `decode` | análise offline de hex/arquivos de captura |
| `ui` | abre a interface PySide6; importação tardia para não exigir Qt na CLI |

`probe` tenta os canais configurados, validando o SPP pelo handshake `0x0107`.
Se o handshake falhar, tenta o próximo canal. Depois do handshake, bateria e ANC
podem falhar sem invalidar a conexão; isso é reportado como aviso.

### `ui/`

Implementação da Fase 2, opcional e dependente de `PySide6-Essentials`:

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | `QApplication`, tema, ícone e entrada `freebuds-ui` |
| `main_window.py` | janela, rail de navegação, páginas, seleção de dispositivo, estado, log e configurações |
| `worker.py` | `DeviceWorker` (conexão/polling/reconexão, notificações e fila genérica de ações) e `ScanWorker` (inquiry) |
| `widgets.py` | hero com pastilhas de bateria, cartões, painel de ANC, `FeaturesPanel` (Áudio, Gestos, Conexão), detalhes, log, switches e combos com popup arredondado |
| `tray.py` | `QSystemTrayIcon`, tooltip e menu |
| `theme.py` | stylesheet HarmonyOS escuro, com cartões, tipografia e estados de navegação |
| `icons.py` | ícones desenhados via `QPainter` (app, bandeja, navegação) e fallback dos recursos |
| `svg_icons.py` | renderização e tintura dos SVGs fornecidos em `assets/icons` |
| `assets/` | foto transparente do produto e `icons/*.svg` |

Fluxo de threads:

```text
UI (thread principal)                 DeviceWorker (QThread)
─────────────────────                 ──────────────────────
clique em Conectar  ───────────────►  FreeBudsClient.connect()
                                      │
sinais Qt          ◄───────────────   connected / snapshot_ready / failed / action_failed
│                                     │
├─ atualiza cartões, ANC, detalhes,   │  espera notificação ou polling
│  tray e log                         │  (até 0,5 s por bloco)
├─ agenda o próximo ciclo             │
└─ “Atualizar agora” acorda o evento  │
                                      │
clique em modo/nível/slider ────────► coloca ação na fila
                                      ├─ envia 0x2B04
                                      ├─ relê ANC até confirmar o alvo
                                      └─ emite snapshot_ready / action_failed

ScanWorker (QThread) ── inquiry 8 s ──► devices_found / failed
```

Pontos importantes:

- o worker não escreve no `settings.json`; a UI salva o canal em `connected`,
  evitando dois escritores concorrentes;
- `DeviceWorker.stop()` usa eventos, sem `terminate()`;
- `shutdown()` espera a thread e fecha a sessão antes de sair;
- o polling padrão é 30 s, configurável em 15/30/60/120 s; qualquer notificação
  espontânea acorda o worker e dispara um snapshot imediato;
- o ícone da bandeja é atualizado a partir do último snapshot, sem polling
  próprio;
- fechar a janela pode apenas escondê-la; **Sair** encerra de verdade;
- a UI envia somente ANC (`0x2B04`), após ação explícita. Modo, nível e slider
  adaptativo ficam desabilitados durante a escrita e são reabilitados quando o
  snapshot confirma o novo estado; em timeout ou falta de confirmação, o estado
  anterior é mantido e o erro é registrado. O botão **Transparência** envia
  `[2, 2]` explicitamente, pois `[2, FF]` reabre o último submode e pode manter o
  adaptável;
- notificações espontâneas são registradas no log; TLVs desconhecidos são
  mostrados em hexadecimal, sem interpretação inventada.

Se o rádio Bluetooth estiver desligado, `enumerate_devices()` levanta
`BluetoothRadioUnavailableError`, a UI registra a mensagem no log e continua
aberta com o botão Conectar desabilitado.

## 3. Fluxo do `probe`

```text
1. resolver --address ou --name
2. ordenar canais: último canal salvo, configuração, 1, 16
3. para cada canal:
   a. abrir socket RFCOMM
   b. iniciar thread de leitura
   c. enviar GET_DEVICE_INFO (0x0107)
   d. se não houver resposta válida, fechar e tentar o próximo
   e. ler bateria (0x0108; aceita 0x0127)
   f. ler ANC (0x2B2A)
   g. opcionalmente escutar notificações (--listen)
   h. salvar o canal que funcionou
4. fechar sessão e imprimir snapshot/JSON
```

O tempo de resposta e o timeout de conexão são configuráveis (`--timeout`,
`--connect-timeout`). O `--raw` mostra TX/RX e problemas de parser.

## 4. Fluxo da UI

```text
1. iniciar QApplication, tema, ícone e MainWindow
2. carregar settings.json
3. listar dispositivos pareados (sem inquiry) e selecionar o último usado
4. se o último dispositivo estiver conectado, iniciar DeviceWorker
5. no worker:
   a. resolver canais com resolve_channels()
   b. abrir FreeBudsClient e validar o handshake
   c. emitir connected
   d. ler snapshot (bateria, ANC e notificações pendentes) e emitir snapshot_ready
   e. dormir poll_interval ou até “Atualizar agora”
   f. em falha, emitir failed e tentar de novo após 12 s
6. na UI:
   a. atualizar cartões, ANC, detalhes, log e bandeja
   b. salvar o canal que funcionou
7. ao sair: parar worker, aguardar, fechar sessão e salvar preferências
```

O botão **Procurar** usa um `ScanWorker` separado para que o inquiry de 8 s não
congele a janela. A UI não faz polling quando está desconectada.

## 5. Tratamento de erros

| Exceção | Origem | Comportamento |
|---|---|---|
| `ProtocolError` | frame/TLV inválido | descartado ou reportado no decode |
| `ChecksumError` | CRC divergente | descartado na sessão; visível no decode |
| `TransportError` | socket RFCOMM | tenta o próximo canal |
| `BluetoothRadioUnavailableError` | APIs Windows | mensagem com dica de ativação |
| `RequestTimeout` | sem resposta | canal inválido ou comando não suportado |
| `SessionClosedError` | conexão encerrada | aviso/troca de canal |
| `Settings` corrompido | JSON inválido | padrões, sem sobrescrever |

## 6. Testes

A suíte possui **89 testes automatizados** passando, cobrindo:

- CRC e vetor conhecido;
- round-trip de framing e TLV;
- fragmentação, concatenação, lixo, CRC inválido e tamanho inválido;
- layouts de device info, bateria e ANC;
- builders e decodificadores de HUAWEI SOUND, áudio espacial, recursos multiplexados `0x2BB4`, detecção de uso, qualidade de som, latência baixa e gestos (`0x2B16`/`17`, `0x2B92`/`93`, `0x011F`/`20`, `0x0125`/`26`);
- sessão com transporte falso (resposta, timeout, notificação, callback, fila e espera por notificações);
- cliente de alto nível com transporte/sessão simulados: precedência de polling sobre notificações antigas, `set_anc`, `read_advanced()`, setters com confirmação e releitura, tratamento de timeout e merging de notificações em `AdvancedSettings`;
- configurações (`poll_interval` e `close_to_tray`);
- CLI `decode`, extração de hex e orquestração de `probe` com transporte mockado;
- smoke test offscreen da UI: renderização completa com bateria, ANC e `FeaturesPanel` (páginas Áudio, Gestos e Conexão), navegação pelo rail, atalhos da visão geral, interação com chips/switches/combos e despacho de ações para o worker.

O que ainda depende de hardware:

- DPI alto, suspensão/retomada da UI e confirmação visual em outras escalas;
- notificação espontânea do nível adaptativo quando o celular muda o slider;
- reconexão após perda real de enlace e pareamento do zero;
- handshake e validação de campos em outros modelos/firmwares.

## 7. Empacotamento futuro

Sugestão:

1. `python -m venv .venv`
2. `pip install -e ".[ui,dev]"`
3. PyInstaller em modo one-dir (evita o custo de extração do one-file e é mais
   previsível com Qt)
4. Inno Setup para criar o instalador `.exe`
5. assinatura de código antes de distribuição pública

O core não deve depender de PySide6 para os testes. A UI será um extra opcional.

## 8. Limites de escopo

- não é afiliado à Huawei;
- não faz atualização de firmware;
- não tenta burlar segurança/pareamento;
- não promete compatibilidade com todos os modelos;
- não substitui o app oficial para funções que exigem conta/cloud;
- não faz captura de pacotes por conta própria: a captura é feita no Android.

Consulte [`PROTOCOL.md`](PROTOCOL.md) e [`CAPTURE_GUIDE.md`](CAPTURE_GUIDE.md).
