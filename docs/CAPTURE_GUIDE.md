# Guia de captura e correlação de comandos

Este guia descreve como capturar o tráfego SPP do app oficial no Android e
transformá-lo em informação utilizável para validar o protocolo deste projeto.
A captura é a fonte de verdade; código decompilado e projetos públicos servem
como hipótese.

> **Segurança:** capture apenas dispositivos seus. Não publique seriais,
> endereços Bluetooth completos ou capturas com dados pessoais sem redigir.
> Não replique comandos de escrita ou firmware sem entender o efeito.

## 1. Antes de começar

- Use o **HUAWEI AI Life** (ou o app oficial compatível) no Android, com o fone
  já pareado e funcionando.
- Desconecte o FreeBuds Client no Windows e, de preferência, desative o
  Bluetooth do PC durante a captura. O SPP aceita uma sessão de controle por
  vez.
- Deixe o fone ligado e fora do estojo.
- Anote modelo e versão de firmware mostrados no app.
- Faça uma ação por vez, com intervalo de 5–10 segundos, e anote a hora e a
  ação. Isso é essencial para correlacionar os pacotes.

Exemplo de caderno de captura:

```text
14:02:10  abri a tela do dispositivo
14:02:25  alterei ANC para cancelamento
14:02:40  alterei ANC para transparência
14:02:55  mudei o equalizador para "Voz"
14:03:10  toquei em "Teste de ajuste"
```

## 2. Ativar o log HCI no Android

1. Ative as opções de desenvolvedor (toque 7 vezes em "Número da versão").
2. Abra **Configurações → Opções do desenvolvedor**.
3. Ative **Depuração USB**.
4. Ative **Ativar log de snoop de Bluetooth HCI** (o nome varia por fabricante).
   Se houver opções, escolha o modo **completo/Full**, não "filtrado".
5. Desligue e ligue o Bluetooth do celular para o log entrar em vigor.
6. Conecte o fone pelo app oficial e faça as ações planejadas.
7. Ao terminar, desative o log HCI. Ele pode conter dados sensíveis de outros
   dispositivos.

Em algumas versões o log fica em:

```text
/data/misc/bluetooth/logs/btsnoop_hci.log
/data/misc/bluetooth/logs/btsnoop_hci.log.last
```

O caminho pode variar. O método recomendado em aparelhos sem root é extrair o
log de um bugreport.

## 3. Obter o arquivo

### Opção A — bugreport (sem root, recomendada)

No PC, com `adb` no `PATH` e o celular autorizado:

```powershell
New-Item -ItemType Directory -Force .\captures | Out-Null
adb devices
adb bugreport .\captures\bugreport.zip
```

Depois extraia e localize o log:

```powershell
Expand-Archive -LiteralPath .\captures\bugreport.zip `
  -DestinationPath .\captures\bugreport -Force

Get-ChildItem .\captures\bugreport -Recurse -Filter 'btsnoop_hci*.log' |
  Select-Object FullName, Length
```

O arquivo costuma aparecer em `FS\data\misc\bluetooth\logs\`. Se o bugreport
trouxer apenas `btsnooz_hci.log` ou um formato compactado, pode ser necessário
converter com o script `btsnooz.py` do AOSP. Em caso de dúvida, prefira um
aparelho/versão em que o `btsnoop_hci.log` esteja disponível.

### Opção B — acesso root

```powershell
adb root
adb pull /data/misc/bluetooth/logs/btsnoop_hci.log .\captures\
```

Sem root, `adb pull` de `/data/misc` normalmente é negado.

## 4. Filtrar no Wireshark

1. Abra `btsnoop_hci.log` no Wireshark.
2. Aplique o filtro de exibição:

```text
btspp
```

3. Restrinja ao fone (substitua pelo MAC do seu dispositivo, em minúsculas):

```text
btspp && bluetooth.addr == aa:bb:cc:dd:ee:ff
```

ou, se a versão do Wireshark usar os campos de origem/destino:

```text
btspp && (bluetooth.src == aa:bb:cc:dd:ee:ff || bluetooth.dst == aa:bb:cc:dd:ee:ff)
```

4. Para ver o canal RFCOMM em uso:

```text
btspp && btrfcomm.channel == 1
```

Troque `1` por `16` se for o caso. O canal aparece no pacote RFCOMM e no
`btspp.data`.

5. Adicione a coluna **Bluetooth SPP → Data** (`btspp.data`) e observe o campo
   no painel de detalhes. O payload começa com `5a` nos quadros Huawei.
6. Pacotes de áudio (A2DP/AVRCP/HFP) não contêm o protocolo de controle. O
   filtro `btspp` deve eliminar esse ruído.

### Exportar texto para a CLI

Com `tshark` instalado (ele acompanha o Wireshark):

```powershell
tshark -r .\captures\btsnoop_hci.log `
  -Y "btspp && bluetooth.addr == aa:bb:cc:dd:ee:ff" `
  -T fields -e btspp.data > .\captures\spp.txt

.\venv\Scripts\freebuds.exe decode --file .\captures\spp.txt
```

O arquivo pode ser concatenado de vários pacotes; o parser tolera isso. Se
quiser separar direções:

```powershell
# Sentido celular -> fone
tshark -r .\captures\btsnoop_hci.log `
  -Y "btspp && bluetooth.src == aa:bb:cc:dd:ee:ff" `
  -T fields -e btspp.data > .\captures\spp-tx.txt

# Sentido fone -> celular
tshark -r .\captures\btsnoop_hci.log `
  -Y "btspp && bluetooth.dst == aa:bb:cc:dd:ee:ff" `
  -T fields -e btspp.data > .\captures\spp-rx.txt
```

O `decode` aceita hex com espaços, dois-pontos, vírgulas, hífens, linhas de
dump com offset e comentários iniciados por `#`, `//` ou `;`.

## 5. Interpretar e correlacionar

Um quadro completo tem a forma:

```text
5A LL LL 00 CC CC [TT LL VV...] CRC CRC
```

Comece pelo handshake e pelas leituras. Compare a captura do app com o que a
CLI envia:

```powershell
.\venv\Scripts\freebuds.exe decode "5A 00 43 00 01 07 ..."
```

Checklist para cada ação:

1. Qual comando apareceu imediatamente depois da ação?
2. Foi uma leitura (`GET`) ou uma escrita (`SET`)?
3. Quais parâmetros mudaram entre duas capturas da mesma ação?
4. O fone respondeu com o mesmo comando? Veio uma notificação diferente?
5. O efeito físico corresponde ao que os bytes sugerem?
6. O CRC fecha? Se não, pode haver fragmentação/perda de bytes no export.
7. A ação aparece em mais de um modelo/firmware?

Ferramentas úteis:

- **Edit → Find Packet → Hex value** no Wireshark para procurar `5a`;
- ordenar por tempo e comparar antes/depois de uma ação;
- salvar um quadro como texto e rodar `freebuds decode`;
- manter capturas separadas por ação para não misturar notificações.

## 6. Análise estática do app (opcional)

Use o APK já instalado no seu aparelho, não distribua o APK. Isso ajuda a
formular hipóteses, mas não substitui a captura.

```powershell
adb shell pm list packages | Select-String huawei
adb shell pm path <pacote>
```

Copie os caminhos retornados (base e splits) e puxe cada APK:

```powershell
adb pull /data/app/.../base.apk .\captures\ai-life-base.apk
```

Abra no **jadx-gui** e procure por:

- `00001101-0000-1000-8000-00805F9B34FB` (UUID SPP);
- strings `FreeBuds`, `spp`, `battery`, `anc`;
- literais de comando como `0x2b2a`, `0x0107`, `0x0108`;
- classes de pacote/TLV e tabelas de CRC.

Limitações: o app é ofuscado e parte do protocolo pode estar em bibliotecas
nativas. Um ID encontrado no código só deve ser implementado depois de
confirmado por captura e teste controlado.

## 7. Preencher a tabela de comandos

Adicione uma linha para cada ação validada:

| Modelo | Firmware | Ação no app oficial | Direção | Canal | Request (hex) | Response (hex) | Efeito observado |
|---|---|---|---|---|---|---|---|
| FreeBuds Pro 5 | (preencher) | abrir tela | celular → fone | 1 | `5A 00 43 00 01 07 ...` |  |  |
| FreeBuds Pro 5 | (preencher) | ler ANC | celular → fone | 1 | `5A 00 07 00 2B 2A 01 00 02 00 1D 33` |  |  |
|  |  |  |  |  |  |  |  |

Registre também:

- data da captura;
- versão do Android;
- modelo/versão do fone;
- se o app oficial estava aberto durante a sessão;
- qualquer comando repetido ou notificação espontânea;
- se o teste foi só leitura ou se houve alteração real.

## 8. Enviar uma captura para o projeto

Ao abrir um issue ou compartilhar resultados:

- remova MACs, seriais, nomes de pessoas e outros dados pessoais;
- informe modelo e firmware;
- informe o comando e o efeito, não apenas o hex;
- anexe um trecho mínimo e legível (não o bugreport inteiro);
- diga se o teste foi feito apenas observando ou se também houve escrita.

Nunca envie firmware, APK proprietário ou chaves de pareamento.
