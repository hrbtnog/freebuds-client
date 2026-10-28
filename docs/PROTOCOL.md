# Protocolo Huawei SPP — notas de engenharia reversa

> **Status:** o codec, o CRC e o parser incremental estão implementados e
> cobertos por testes. A validação inicial em hardware foi concluída em
> **2026-10-21** com um FreeBuds Pro 5 (modelo interno `BTFT0023`, HarmonyOS
> 7.0.0.350): listagem, handshake (`0x0107`), bateria (`0x0108`) e leitura de
> ANC (`0x2B2A`) responderam no canal `1`. Os três modos de ANC foram observados;
> o nível de transparência `4` foi identificado como **Reconhecimento adaptável**.
> Notificações espontâneas de ANC (`0x2B2A`) foram observadas. Em **2026-10-23**
> a escrita de ANC (`0x2B04`) e as preferências avançadas capturadas via HCI
> (HUAWEI SOUND, áudio espacial, áudio adaptável, controle de cabeça, detecção de
> uso, qualidade de transmissão, latência baixa, ANC com um fone e gestos de
> toque/pressão) foram validadas no mesmo hardware com confirmação e restauração
> do estado. Multiponto e deslizar permanecem somente leitura por segurança.
> Notificações de bateria (`0x0127`) e o significado de `0x2BAC` continuam pendentes.
>
> Nada neste documento autoriza atualização de firmware. O `probe` continua
> estritamente somente leitura; a UI envia apenas comandos de controle confirmados.

## 1. Transporte

Os FreeBuds usam **Bluetooth clássico**, perfil **SPP** (Serial Port Profile),
sobre **RFCOMM**. Não é o canal BLE/GATT principal desses fones.

| Item | Valor |
|---|---|
| UUID SPP | `00001101-0000-1000-8000-00805F9B34FB` |
| PSM L2CAP do RFCOMM | `0x0003` |
| Magic do protocolo | `0x5A` |
| Byte reservado | `0x00` no offset 3 |
| CRC | CRC16/XMODEM, big-endian |

Canais RFCOMM conhecidos por modelo (fonte: OpenFreebuds):

| Canal | Modelos |
|---|---|
| `1` | FreeBuds Pro, Pro 2, Pro 3, Pro 5, 6i |
| `16` | FreeBuds 4i, 5i |

O Windows não oferece uma API de socket que receba o UUID do serviço e resolva o
canal automaticamente. Por isso a CLI tenta os canais conhecidos (ou os
informados em `--channel`). O canal pode variar com firmware/região; a lista
acima é uma hipótese de trabalho, não uma garantia.

A conexão SPP é exclusiva na prática: o app oficial no celular e o cliente no
Windows não devem manter sessões simultâneas.

## 2. Enquadramento

Formato observado nas referências públicas:

```text
offset  0       1..2          3        4..5         6..N          último-1..último
        +-------+-------------+--------+------------+-------------+----------------+
        | 0x5A  | length (BE) | 0x00   | comando BE | TLVs        | CRC16 (BE)     |
        +-------+-------------+--------+------------+-------------+----------------+
```

Definições:

- `body = comando (2 bytes) + TLVs`.
- `length = len(body) + 1`.
- `total = 4 (header) + len(body) + 2 (CRC) = length + 5`.
- O maior quadro aceito pelo parser defensivo é 8192 bytes. O campo suporta
  até 65535, mas respostas conhecidas ficam abaixo de 1 KiB.

Cada TLV é:

```text
TT LL VV...
 |  |  +-- valor (0 a 255 bytes)
 |  +----- tamanho do valor (1 byte)
 +-------- tipo do parâmetro (1 byte)
```

TLVs com valor vazio são usados para **pedir** campos. Exemplo de pedido de
identificação (`0x0107`) pedindo os índices `0x00..0x1F`:

```text
5A 00 43 00 01 07 00 00 01 00 02 00 ... 1F 00 8B E9
```

O parser não depende de delimitador: usa `length` para saber onde um quadro
termina. Ele mantém bytes incompletos entre `feed()`s, descarta lixo até o
próximo `0x5A` e valida o CRC.

## 3. CRC16/XMODEM

Parâmetros:

- polinômio: `0x1021`
- valor inicial: `0x0000`
- reflexão de entrada/saída: não
- XOR final: `0x0000`
- armazenamento: big-endian

Vetor de teste usado no projeto:

```text
bytes sem CRC: 5A 00 06 00 2B 03 08 01 00
CRC calculado: A7 9D
quadro:        5A 00 06 00 2B 03 08 01 00 A7 9D
```

Esse é um vetor de validação do CRC; não trate o conteúdo semântico como uma
captura real.

## 4. Comandos implementados

O cliente envia os comandos de leitura abaixo e, na UI, a escrita de ANC
(`0x2B04`) já validada. Os demais comandos são reconhecidos para exibição ou
documentação.

| Comando | Nome | Direção | Parâmetros | Estado |
|---|---|---|---|---|
| `0x0107` | GET_DEVICE_INFO | PC → fone | TLVs vazios `0..31` | implementado |
| `0x0108` | GET_BATTERY | PC → fone | `1`, `2`, `3` vazios | implementado |
| `0x2B2A` | GET_ANC / ANC_STATE | PC → fone (leitura); fone → PC (notificação) | `1`, `2` vazios no pedido | implementado |
| `0x2B04` | SET_ANC | PC → fone | modo/nível | **implementado/validado na UI** |
| `0x0127` | BATTERY_NOTIFY | fone → PC | layout de bateria | reconhecido/decodificado |
| `0x2B03` | ANC_CHANGED | fone → PC | varia | não observado no Pro 5 |

### 4.1. Identificação — `0x0107`

O pedido usado segue o OpenFreebuds: 32 TLVs vazios, tipos `0x00` a `0x1F`. A
resposta ecoa o comando `0x0107` e traz os campos como TLVs.

Campos publicamente documentados:

| Tipo | Campo | Formato observado |
|---|---|---|
| `0x03` | hardware_version | texto |
| `0x07` | software_version | texto |
| `0x09` | serial_number | texto |
| `0x0A` | device_submodel | texto |
| `0x0F` | device_model | texto |
| `0x18` | serial L/R | `L-<serial>,R-<serial>` em alguns modelos |

Resposta real de um FreeBuds Pro 5 (`BTFT0023`, HarmonyOS 7.0.0.350), com 192
bytes e 14 TLVs:

| Tipo | Tam. | Observação |
|---|---|---|
| `0x02` | 2 | `01 6D`; significado desconhecido |
| `0x03` | 14 | `HL1SAKM2_Ver.A` |
| `0x07` | 32 | `HarmonyOS 7.0.0.350(F003H003C91)` |
| `0x09` | 16 | serial do dispositivo (redigido) |
| `0x0A` | 15 | `BTFT0023-00016D` |
| `0x0F` | 8 | `BTFT0023` (nome interno; o Windows exibe "HUAWEI FreeBuds Pro 5") |
| `0x18` | 37 | seriais L/R no formato `L-...,R-...` (redigidos) |
| `0x19` | 1 | `0E`; significado desconhecido |
| `0x1B` | 6 | binário; desconhecido |
| `0x1D` | 6 | binário; desconhecido |
| `0x1E` | 6 | binário; desconhecido |
| `0x20` | 6 | endereço Bluetooth local invertido (ver abaixo) |
| `0x21` | 1 | `01`; significado desconhecido |
| `0x22` | 6 | binário; desconhecido |

O campo `0x20` contém os seis bytes do endereço Bluetooth local em ordem
invertida. Por exemplo, o endereço Windows `AA:BB:CC:DD:EE:FF` aparece como
`FF EE DD CC BB AA`. O campo `0x22` também tem seis bytes, mas seu significado
não foi confirmado; não o tratamos como endereço sem uma captura que prove isso.

Campos desconhecidos são preservados em `fields`/`raw_fields`, com os bytes
binários exibidos em hexadecimal. Não inferimos o significado de dados não
documentados. A codificação de texto observada é UTF-8 e, em alguns aparelhos,
GBK/ASCII.

### 4.2. Bateria — `0x0108` e `0x0127`

Leitura: o cliente envia `0x0108` pedindo os parâmetros `1`, `2` e `3` vazios.
Alguns firmwares podem responder com `0x0127` de forma assíncrona; a sessão
aceita ambos ao pedir bateria.

| Parâmetro | Tamanho | Interpretação pública |
|---|---|---|
| `1` | 1 byte | nível global (`0..100`) |
| `2` | 3 bytes | esquerda, direita, estojo (`0..100` cada) |
| `3` | N bytes | flags de carga; `0x01` presente indica carregando em alguns modelos |
| `4` | 2 bytes | desconhecido; observado `0A 14` |
| `5` | 2 bytes | desconhecido; observado `01 01` |
| `6` | 1 byte | desconhecido; observado `0A` |

Quando um parâmetro tem tamanho diferente do esperado, o cliente mantém o valor
bruto e deixa os campos semânticos como `None`. Os parâmetros `4`, `5` e `6`
foram observados no FreeBuds Pro 5, mas não são interpretados.

Captura real de 2026-10-21 no FreeBuds Pro 5:

```text
TX 5A 00 09 00 01 08 01 00 02 00 03 00 FB B9
RX 5A 00 1B 00 01 08 01 01 53 02 03 53 53 45 03 03 01 01 01
   04 02 0A 14 05 02 01 01 06 01 0A 9F 73
```

Nessa captura:

- parâmetro `1` = `53` → 83% global;
- parâmetro `2` = `53 53 45` → 83% / 83% / 69% (L/R/estojo);
- parâmetro `3` = `01 01 01` → os três bytes valem `01`; o cliente marcou
  `charging = true`, mas o significado por componente ainda não foi confirmado;
- parâmetros `4`, `5` e `6` são preservados como brutos.

Em uma segunda leitura, com os fones fora do estojo e apenas o estojo carregando,
o parâmetro `3` veio `00 00 01`. Isso é compatível com a hipótese de três flags
na ordem esquerda/direita/estojo, mas ainda não é uma confirmação definitiva.
O cliente continua exibindo as flags brutas e usa `charging = true` quando
qualquer byte é `01`.

Alguns firmwares podem responder com uma notificação `0x0127` em vez de
`0x0108`. Exemplo apenas ilustrativo desse formato alternativo:

```text
comando 0x0127
param 1 = 64                     -> global 100%
param 2 = 5A 50 46              -> 90% / 80% / 70%
param 3 = 00 01                 -> flag 0x01 presente
```

### 4.3. ANC — `0x2B2A`

Leitura: `0x2B2A` com parâmetros `1` e `2` vazios. A resposta observada nas
referências traz no parâmetro `1` dois bytes:

```text
byte 0 = código do nível
byte 1 = código do modo
```

Modos:

| Código | Nome |
|---|---|
| `0` | normal |
| `1` | cancellation (cancelamento) |
| `2` | awareness (transparência) |

Níveis de cancelamento:

| Código | Nome |
|---|---|
| `0` | normal |
| `1` | comfort |
| `2` | ultra |
| `3` | dynamic (quando suportado) |

Níveis de transparência:

| Código | Nome |
|---|---|
| `1` | voice_boost |
| `2` | normal |
| `4` | adaptive (**Reconhecimento adaptável**) |

No FreeBuds Pro 5, o código `4` é o **Reconhecimento adaptável**. A posição do
controle fica no parâmetro `2`, com 11 posições de `0x00` a `0x0A`. A interface
apresenta esses valores como `1` a `11`:

| Parâmetro `2` | UI | Significado |
|---|---|---|
| `0x00` | `1` | mais ruído |
| `0x01` | `2` | — |
| `0x02` | `3` | — |
| `0x03` | `4` | — |
| `0x04` | `5` | — |
| `0x05` | `6` | padrão exibido pela UI |
| `0x06` | `7` | — |
| `0x07` | `8` | — |
| `0x08` | `9` | — |
| `0x09` | `10` | — |
| `0x0A` | `11` | menos ruído |

O parâmetro `2` pode persistir entre modos; o cliente só o expõe como
`adaptive_level` quando o parâmetro `1` é `[4, 2]` (adaptável ativo). Valores
fora de `0x00..0x0A` são preservados apenas no bruto.

Para selecionar **transparência padrão**, a UI envia o nível explícito `[2, 2]`
em `0x2B04`. O modo genérico `[2, 0xFF]` reabre o **último submode** de
transparência; em 2026-10-23, partindo do adaptável, ele manteve o nível `4`.
Esse detalhe foi confirmado no hardware.

Resposta real no modo normal (FreeBuds Pro 5, 2026-10-21):

```text
TX 5A 00 07 00 2B 2A 01 00 02 00 1D 33
RX 5A 00 0A 00 2B 2A 01 02 00 00 02 01 00 E8 E6
```

O parâmetro `1` é `00 00` (nível `0`, modo `0` = normal) e o parâmetro `2` é
`00`.

Com o ANC em cancelamento, a resposta foi:

```text
TX 5A 00 07 00 2B 2A 01 00 02 00 1D 33
RX 5A 00 0A 00 2B 2A 01 02 03 01 02 01 00 70 80
```

Aqui o parâmetro `1` é `03 01` (nível `3` = dynamic, modo `1` = cancellation).
Isso confirma o layout `[nível, modo]` e o código `3` para "dynamic" nesse
firmware.

Com o ANC em transparência (awareness), a resposta foi:

```text
TX 5A 00 07 00 2B 2A 01 00 02 00 1D 33
RX 5A 00 0A 00 2B 2A 01 02 04 02 02 01 00 8C 88
```

O parâmetro `1` é `04 02` (nível `4`, modo `2` = awareness), ou seja,
Reconhecimento adaptável. No quadro acima, o parâmetro `2` é `00` e corresponde
ao nível `1` de `11` na interface. Em 2026-10-23, ao mover o controle no
FreeBuds Pro 5, o parâmetro `2` percorreu `00, 01, …, 0A`; a escrita desse nível
foi confirmada e restaurada. Os níveis `2` (ultra) e `3` (dinâmico) de
cancelamento também foram observados na escrita de `0x2B04`.

#### Notificação de mudança de ANC

Em uma escuta de 50 segundos, alternando o ANC pelos gestos, o FreeBuds Pro 5
enviou oito notificações `0x2B2A` espontâneas, uma para cada mudança de estado.
**Não** foi enviado `0x2B03` nesse firmware. O corpo é idêntico ao de uma
resposta de leitura:

| Notificação | Parâmetro `1` | Estado |
|---|---|---|
| `5A 00 0A 00 2B 2A 01 02 03 01 02 01 00 70 80` | `03 01` | cancelamento, dynamic |
| `5A 00 0A 00 2B 2A 01 02 00 00 02 01 00 E8 E6` | `00 00` | normal |
| `5A 00 0A 00 2B 2A 01 02 04 02 02 01 00 8C 88` | `04 02` | Reconhecimento adaptável; parâmetro `2` = posição |

Isso mostra que `0x2B2A` deve ser tratado tanto como resposta de leitura quanto
como notificação de estado. O cliente preserva e decodifica esses quadros na
escuta (`--listen`) e no log da UI; o worker da UI é acordado por qualquer
notificação espontânea e lê um snapshot imediatamente, sem esperar o polling.
`0x2B03` continua documentado para outros firmwares, mas não foi observado neste.

### 4.4. Escrita de ANC — `0x2B04`

O comando foi validado no FreeBuds Pro 5 em **2026-10-23**. O parâmetro `1` usa
dois bytes:

| Operação | Parâmetros | Exemplo |
|---|---|---|
| Modo normal | `1 = [0, 0x00]` | `00 00` |
| Modo cancelamento | `1 = [1, 0xFF]` | `01 FF` |
| Transparência (último submode) | `1 = [2, 0xFF]` | `02 FF` |
| Transparência padrão | `1 = [2, 2]` | `02 02` |
| Nível do modo ativo | `1 = [modo_ativo, nível]` | `01 03` = cancelamento/dinâmico |
| Ativar Reconhecimento adaptável | `1 = [2, 4]` | `02 04` |
| Intensidade adaptativa | `1 = [2, 4]`, `3 = 01`, `4 = [0x00..0x0A]` | nível `6` = `05` |

Os três modos, os níveis de cancelamento (`0` padrão, `1` conforto, `2` ultra,
`3` dinâmico) e os 11 níveis do Reconhecimento adaptável foram aplicados e
restaurados no hardware. A escrita da intensidade usa o TLV `4`; tentar enviar a
posição no TLV `2` é ignorado pelo firmware. O eco `0x2B04` foi observado com
`TLV 2 = 00` (aceito), geralmente seguido de um push `0x2B2A` com o novo estado.

O firmware confirma a escrita antes de publicar o novo estado. Por isso o cliente
espera a confirmação e relê o ANC até o estado solicitado aparecer, com limite de
tempo; se não confirmar, mantém o estado anterior e reporta o erro. Para sair do
adaptável e voltar à transparência padrão, use `[2, 2]` — `[2, 0xFF]` reabre o
último submode e pode manter o adaptável. O nível `4` agora está mapeado e é
enviado somente pela ação explícita do usuário.

### 4.5. Notificação desconhecida `0x2BAC`

Durante uma escuta de 5 segundos após o snapshot, o fone enviou uma notificação
`0x2BAC` com TLVs `1..11`, a maioria com valor `01` ou `00`. O quadro tinha CRC
válido, mas o significado não foi identificado. O cliente preserva o quadro
bruto e o mostra como desconhecido; não o interpreta como configuração.

```text
RX 5A 00 24 00 2B AC 01 01 01 02 01 01 03 01 00 04 01 00 05 01 00
   06 01 00 07 01 00 08 01 00 09 01 00 0A 01 00 0B 01 00 62 44
```

### 4.6. Comandos e escritas avançadas confirmados no FreeBuds Pro 5

A captura do aplicativo oficial no Android e a análise dos frames HCI (1.022 quadros
Huawei válidos) permitiram isolar os comandos para as seguintes funções adicionais,
reverificadas por escrita no Windows e restauração de estado:

#### 4.6.1. HUAWEI SOUND (Perfis de equalização)

- Leitura: `0x2B4A` pedindo `{2: b""}`. Retorna `TLV 2` = ID ativo, `TLV 6` = curva
  bruta do equalizador (10 bandas), `TLV 7` = nome UTF-8 do perfil personalizado.
- Escrita: `0x2B49`.
  - Perfis padrão: usam apenas `TLV 1 = [ID]`.
    - `0x02` = Graves
    - `0x05` = Equilibrado
    - `0x09` = Voz
    - `0x0D` = Filme
    - `0x0E` = Jogos
    - `0x0F` = Podcast
    - `0x10` = Impacto
    - `0x11` = EQ adaptável
  - Perfil Clássico (`ID 201` / `0xC9`): usa payload completo
    `{1: C9, 2: 0A, 5: 01, 3: fb141e0a0000e7f60a00, 4: "201"}`.
  - Perfil Personalizado (`ID 100` / `0x64`): reutiliza a curva e o nome lidos
    previamente do fone: `{1: 64, 2: 0A, 5: 01, 3: curva, 4: nome}`.

#### 4.6.2. Recursos de áudio (`0x2BB4`)

O comando multiplexador `0x2BB4` usa `TLV 1` com o subcomando:

- **Áudio espacial (`0x18`)**:
  - Leitura: `{1: 18, 2: b"", 3: b""}`. `TLV 2` = modo (0 = desligado, 1 = acompanhamento da cabeça, 2 = fixo); `TLV 3` = efeito espacial (0 = padrão, 1 = teatro, 2 = cinema, 3 = sala de espetáculos).
  - Escrita de modo: `{1: 18, 2: [modo]}`.
- **Volume adaptável (`0x02`)**:
  - Leitura: `{1: 02, 2: b""}`.
  - Escrita: `{1: 02, 2: [00 ou 01]}`.
- **Reconhecimento de conversa (`0x1B`)**:
  - Leitura: `{1: 1B, 2: b""}`.
  - Escrita: `{1: 1B, 2: [00 ou 01]}`.
- **Cancelamento com um fone (`0x05`)**:
  - Leitura: `{1: 05, 2: b""}`.
  - Escrita: `{1: 05, 2: [00 ou 01]}`.
- **Controle de cabeça (`0x0B`)**:
  - Leitura: `{1: 0B}`. `TLV 2` = ativado (0/1), `TLV 3` = aceno (0 nenhum, 1 atender), `TLV 4` = balanço (0 nenhum, 2 rejeitar).
  - Escrita: `{1: 0B, 2: [00 ou 01], 3: [aceno], 4: [balanço]}`.

#### 4.6.3. Detecção de uso (Wear Detection)

- Leitura: `0x2B11` `{1: b""}`. `TLV 1` = 0 ou 1.
- Escrita: `0x2B10` `{1: [00 ou 01]}`.

#### 4.6.4. Qualidade de transmissão Bluetooth

- Leitura: `0x2BA3` `{}`. `TLV 2` = 0 (priorizar conexão) ou 1 (priorizar qualidade sonora).
- Escrita: `0x2BA2` `{1: [00 ou 01]}`.

#### 4.6.5. Modo de baixa latência de áudio (Gaming Mode)

- Leitura: `0x2B6C` `{2: b""}`. `TLV 2` = 0 ou 1.
- Escrita: `0x2B6C` `{1: [00 ou 01]}`.

#### 4.6.6. Gestos de toque e pressão

- **Pressionar e segurar (Press & Hold)**:
  - Leitura: `0x2B17` `{1: b"", 2: b""}` (1 = esquerdo, 2 = direito).
  - Escrita: `0x2B16` `{lado: [ação]}` (ações: `0x00` assistente, `0x0A` controle de ruído, `0xFF` nenhum).
- **Pinçar e segurar (Pinch & Hold)**:
  - Leitura: `0x2B93` `{1: 03, 2: 00}`.
  - Escrita: `0x2B92` `{1: 03, 2: 00, lado: [ação]}` (3 = esquerdo, 4 = direito; ações: `0x06` controle de ruído, `0xFF` nenhum).
- **Toque duplo (Double Tap)**:
  - Leitura: `0x0120` `{1: b"", 2: b""}`.
  - Escrita: `0x011F` `{1: [esquerdo], 2: [direito]}` (ações: `0x01` reproduzir/pausar, `0xFF` nenhum).
- **Toque triplo (Triple Tap)**:
  - Leitura: `0x0126` `{1: b"", 2: b""}`.
  - Escrita: `0x0125` `{lado: [ação]}` (ações: `0x07` faixa anterior, `0x02` próxima faixa, `0xFF` nenhum).
- **Deslizar (Swipe)**:
  - Leitura: `0x2B19` `{1: b"", 2: b""}`.
  - Escrita: nenhuma escrita HCI observada; mantido estritamente como somente leitura na UI.

#### 4.6.7. Multi-conexão / Multiponto

- Leitura: `0x2B2F` `{1: b""}`. `TLV 1` = 0 ou 1.
- Escrita: `0x2B2E` — **não implementada/bloqueada**. Desativar o multiponto
  pode derrubar conexões ativas com outros dispositivos emparelhados. Permanece
  somente leitura na UI.

## 5. Comandos conhecidos e status de implementação

| Leitura | Escrita | Função | Status no FreeBuds Client |
|---|---|---|---|
| `0x0107` | — | Identificação do dispositivo | Implementado (leitura) |
| `0x0108` | — | Bateria global, fones e estojo | Implementado (leitura) |
| `0x0127` | — | Notificação espontânea de bateria | Preservado |
| `0x2B2A` | `0x2B04` | ANC (Normal, Cancelamento, Transparência) | Implementado (leitura e escrita com 11 níveis adaptativos) |
| `0x2B4A` | `0x2B49` | HUAWEI SOUND (Perfis de equalização) | Implementado (leitura e escrita de perfis/custom) |
| `0x2BB4:18` | `0x2BB4:18` | Áudio espacial (modo) | Implementado (leitura e escrita) |
| `0x2BB4:02` | `0x2BB4:02` | Volume adaptável | Implementado (leitura e escrita) |
| `0x2BB4:1B` | `0x2BB4:1B` | Reconhecimento de conversa | Implementado (leitura e escrita) |
| `0x2BB4:05` | `0x2BB4:05` | ANC com um fone | Implementado (leitura e escrita) |
| `0x2BB4:0B` | `0x2BB4:0B` | Controle de movimentos de cabeça | Implementado (leitura e escrita) |
| `0x2B11` | `0x2B10` | Detecção de uso | Implementado (leitura e escrita) |
| `0x2BA3` | `0x2BA2` | Qualidade do som (conexão vs áudio) | Implementado (leitura e escrita) |
| `0x2B6C` | `0x2B6C` | Modo de baixa latência de áudio | Implementado (leitura e escrita) |
| `0x2B17` | `0x2B16` | Gesto pressionar e segurar | Implementado (leitura e escrita) |
| `0x2B93` | `0x2B92` | Gesto pinçar e segurar | Implementado (leitura e escrita) |
| `0x0120` | `0x011F` | Toque duplo | Implementado (leitura e escrita) |
| `0x0126` | `0x0125` | Toque triplo | Implementado (leitura e escrita) |
| `0x2B19` | — | Gesto deslizar | Implementado (somente leitura; sem escrita HCI) |
| `0x2B2F` | `0x2B2E` | Multi-conexão / Multiponto | Implementado (somente leitura por segurança) |
| — | — | Atualização de firmware | Fora de escopo permanente |

## 6. Procedimento para validar um comando

1. Capture no Android com HCI snoop log, uma ação por vez. Veja
   [`CAPTURE_GUIDE.md`](CAPTURE_GUIDE.md).
2. Separe os pacotes SPP/RFCOMM do dispositivo alvo.
3. Decodifique com `freebuds decode` ou use o parser para conferir CRC e TLVs.
4. Compare request/response e confirme o efeito observável no fone.
5. Preencha uma linha da tabela abaixo com modelo, firmware e captura.
6. Só depois implemente e teste uma escrita, com confirmação e opção de reverter.

| Modelo | Firmware | Ação no app | Direção | Canal | Request (hex) | Response (hex) | Observação |
|---|---|---|---|---|---|---|---|
| FreeBuds Pro 5 (`BTFT0023`) | HarmonyOS 7.0.0.350 (F003H003C91) | `freebuds probe` | leitura | 1 | `0x0107`, `0x0108`, `0x2B2A` | ver §4 | handshake, bateria e os três modos de ANC OK em 2026-10-21 |
| FreeBuds Pro 5 (`BTFT0023`) | HarmonyOS 7.0.0.350 (F003H003C91) | UI / script de ANC | escrita | 1 | `0x2B04` com `00 00`, `01 FF`, `02 02`, `02 04`, `01 02`, `01 03` | eco `0x2B04` + `0x2B2A` | três modos, níveis de cancelamento e 11 níveis adaptativos OK em 2026-10-23; estado restaurado |
| FreeBuds Pro 5 (`BTFT0023`) | HarmonyOS 7.0.0.350 (F003H003C91) | UI / recursos avançados | escrita | 1 | `0x2B49`, `0x2BB4`, `0x2B10`, `0x2BA2`, `0x2B6C`, `0x2B16`, `0x2B92`, `0x011F`, `0x0125` | respostas e confirmações por releitura | HUAWEI SOUND, espacial, adaptativo, cabeça, uso, qualidade, latência e gestos OK em 2026-10-23; estado restaurado |

## 7. Limitações e dúvidas abertas

- O canal RFCOMM é fixo por modelo na implementação atual; uma consulta SDP
  dinâmica seria mais robusta.
- Nem todo firmware responde `0x0108`; algumas notificações usam `0x0127`.
- O significado dos flags de carga e a presença de nível por componente variam;
  no FreeBuds Pro 5 observamos `01 01 01` e depois `00 00 01`, compatível com
  flags L/R/estojo, mas ainda não confirmado.
- Os parâmetros `4`, `5` e `6` do `0x0108` foram observados, mas não
  interpretados.
- O parâmetro `2` do `0x2B2A` é a posição do Reconhecimento adaptável quando o
  modo é transparência e o nível é `4`; nos outros modos ele pode permanecer com
  o último valor e não é interpretado.
- Os três modos ANC foram observados em hardware: normal (`00 00`),
  cancelamento dynamic (`03 01`) e transparência adaptável (`04 02`). A escrita
  de `0x2B04` confirmou os níveis de cancelamento `0` a `3` e os 11 níveis do
  Reconhecimento adaptável (`0x00..0x0A` no TLV `4`).
- Escrita de multiponto (`0x2B2E`) não é enviada para evitar desconectar
  inadvertidamente outros dispositivos pareados.
- Gesto de deslizar e efeitos sonoros do estojo não geraram escrita observável no
  HCI; mantidos como somente leitura.
- A notificação `0x2BAC` é preservada como bruta, mas seu significado é
  desconhecido.
- No FreeBuds Pro 5, mudanças de ANC chegaram como `0x2B2A` espontâneo, não
  como `0x2B03`. Outros firmwares podem usar `0x2B03`; ele não foi observado
  aqui.
- Vários campos de `0x0107` (`0x02`, `0x19`, `0x1B`, `0x1D`, `0x1E`, `0x21`,
  `0x22`) ainda não têm significado confirmado. O campo `0x20` foi identificado
  como o endereço Bluetooth local invertido.
- O mapeamento de nível de ANC pode variar por modelo (por exemplo, "dynamic"
  só existe em alguns).
- A compatibilidade com FreeBuds 4i/5i, FreeClip, FreeArc etc. não foi testada.
- Não há suporte a atualização de firmware e ele não será implementado por
  engenharia reversa.

## 8. Referências

- OpenFreebuds — <https://github.com/melianmiko/OpenFreebuds>
  - `driver/huawei/package.py` (codec)
  - `driver/huawei/constants/spp_commands.py` (IDs)
  - `driver/huawei/handler/info.py`, `battery.py`, `anc.py` (layouts)
- LibreBuds — <https://github.com/librebuds/librebuds>
  - `android/protocol/.../command/Anc.kt` (intensidade adaptativa no TLV `4`;
    confirmada neste projeto no FreeBuds Pro 5)
- Protocolo FreeBuds 4i — <https://mmk.pw/en/posts/freebuds-4i-proto/>
- Gadgetbridge — <https://codeberg.org/Freeyourgadget/Gadgetbridge>
- Wireshark, filtro SPP — <https://www.wireshark.org/docs/dfref/b/btspp.html>
