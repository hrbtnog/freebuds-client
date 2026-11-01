# FreeBuds Client

[![CI](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml/badge.svg)](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

[**English**](README.md) | [**Português (Brasil)**](README.pt-BR.md) | [**Español**](README.es.md) | [**Русский**](README.ru.md) | [**简体中文**](README.zh-CN.md)

> ⚠️ **Nota:** Esta traducción fue realizada mediante inteligencia artificial (IA) y puede contener errores o imprecisiones. La documentación original de referencia está disponible en [inglés](README.md) y [portugués](README.pt-BR.md).

Cliente de escritorio **no oficial** para Windows para gestionar auriculares HUAWEI FreeBuds, inspirado en la ergonomía de Galaxy Buds Client. Su objetivo es proporcionar nivel de batería, control de ruido, perfiles de sonido, gestos, estado multipunto y pruebas de hardware sin cuenta de Huawei y sin HUAWEI AI Life.

---

## ⚡ Resumen Rápido (TL;DR)

Si solo estás de paso y quieres lo esencial:

- **Qué es:** Una aplicación ligera para Windows (con una moderna interfaz gráfica inspirada en HarmonyOS y una CLI) para consultar la batería y configurar tus HUAWEI FreeBuds directamente desde la PC.
- **Qué hace:**
  - Muestra porcentajes de batería en tiempo real para ambos auriculares (L/R) y el estuche de carga.
  - Alterna modos de control de ruido (ANC: Cancelación, Desactivado, Atención/Transparencia) y Reconocimiento Adaptativo (11 niveles).
  - Configura perfiles de audio (HUAWEI SOUND), audio espacial, detección de uso y gestos táctiles o de cabeza.
  - Se minimiza de forma fluida en la bandeja del sistema.
  - Soporte multilingüe (con selector de idioma en preferencias).
- **Qué NO hace:** No reemplaza la aplicación móvil oficial (no actualiza firmware, no ofrece ecualización paramétrica personalizada avanzada ni busca auriculares perdidos).
- **Inicio rápido:** Descarga el ejecutable listo para usar (`.exe`) desde la página de [Releases](https://github.com/hrbtnog/freebuds-client/releases) o ejecuta desde el código fuente con Python 3.10+ (`pip install -e ".[ui]"` y luego `freebuds-ui`).
- **Proyecto personal:** Un proyecto sin fines de lucro desarrollado por un aficionado con asistencia de IA. ¡Sugerencias, reportes de errores y PRs son bienvenidos!

---

## Sobre mí y por qué existe este proyecto

**No soy programador** y nunca he trabajado en desarrollo de software. Este es un proyecto personal de aprendizaje: quería una forma de ver la batería y controlar la cancelación de ruido de mis FreeBuds Pro 5 desde la PC, sin depender del teléfono y sin usar HUAWEI AI Life.

Cabe señalar que la propuesta de la aplicación no es sustituir completamente la necesidad de un smartphone con Huawei AI Life o Huawei Audio Connect para una gestión exhaustiva. Funciones como ecualizadores personalizados avanzados, ajustes de tonos del estuche, función de búsqueda o pruebas de ajuste de almohadillas no existen aquí por ahora (y algunas tal vez no se implementen debido a limitaciones técnicas).

La idea inicial es simplemente complementar la experiencia de uso, ofreciendo un acceso rápido y cómodo a las funciones clave directamente desde Windows, llenando un vacío que Huawei no cubre de forma nativa en escritorio.

No es un producto comercial. No tiene soporte oficial, plazos ni garantía. El código fue escrito con asistencia de IA y probado en el hardware que poseo. Si encuentras algún problema, repórtalo para intentar corregirlo. ¡Sugerencias, críticas constructivas, issues y pull requests son muy bienvenidos!

## Aviso Importante

- **Úsalo bajo tu propia responsabilidad.** Este software se comunica con los auriculares por Bluetooth y puede alterar configuraciones. No hay garantía de funcionamiento en otros modelos, firmwares o revisiones de hardware.
- **Proyecto no oficial.** No está afiliado, patrocinado ni respaldado por Huawei, HONOR ni ningún fabricante. Las marcas e imágenes pertenecen a sus respectivos dueños; consulta [`NOTICE.md`](NOTICE.md).
- **No realiza actualizaciones de firmware** y no intenta eludir el emparejamiento, PIN, passkey o confirmaciones de seguridad de Windows.
- **No compartas datos personales.** Evita publicar direcciones MAC Bluetooth completas, números de serie, volcados HCI o nombres de dispositivos en issues, capturas y PRs.

## Estado del Proyecto

> **Estado:** Fases principales implementadas. El núcleo de comunicación, la CLI de diagnóstico y la documentación de ingeniería inversa fueron validados en hardware el **2026-10-21** con unos FreeBuds Pro 5 en el canal `1`: enumeración, handshake, batería y los tres modos de ANC respondieron como se esperaba. El nivel de transparencia `4` se identificó como **Reconocimiento Adaptativo** con 11 niveles; los cambios de estado de ANC llegan mediante notificaciones push `0x2B2A`. El **2026-10-23**, la UI PySide6 con bandeja fue validada conectada al PC y al teléfono en simultáneo. La escritura de ANC (`0x2B04`) y las preferencias avanzadas (HUAWEI SOUND, audio espacial, volumen adaptativo, reconocimiento de voz/conversación, control de cabeza, detección de uso, prioridad de calidad de sonido, baja latencia y ANC con un auricular) se integraron con lecturas de confirmación. El **2026-10-28**, la interfaz fue rediseñada adaptando el lenguaje de diseño de HUAWEI Audio Connect con panel lateral HarmonyOS, tarjetas, controles segmentados, pastillas de batería e internacionalización. La suite cuenta con **89 pruebas automatizadas pasando**. La conexión multipunto y el gesto de deslizar permanecen en modo de solo lectura por seguridad.

## Documentación

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — Formato de tramas, CRC16, TLVs y comandos conocidos.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Capas de arquitectura, threading, sondeo CLI y workers de UI.
- [`docs/CAPTURE_GUIDE.md`](docs/CAPTURE_GUIDE.md) — Guía para capturar tráfico HCI Bluetooth en Android y correlacionar comandos.
- [`CHECKPOINT.md`](CHECKPOINT.md) — Punto de restauración, validaciones en hardware y notas técnicas.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Cómo probar, sugerir mejoras y enviar pull requests.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Código de conducta de la comunidad.
- [`SECURITY.md`](SECURITY.md) — Políticas de privacidad y reporte de vulnerabilidades.
- [`NOTICE.md`](NOTICE.md) — Marcas registradas, recursos visuales y licencias de terceros.
- [`LICENSE`](LICENSE) — Licencia MIT del proyecto.
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — Guía de publicación para releases y forks.

## Diseño de la Interfaz

La interfaz traslada el lenguaje visual de las aplicaciones móviles modernas a un formato de escritorio equilibrado:

- Barra de navegación lateral fija con selector de dispositivo;
- Contenido en columna central con ancho máximo para evitar que las tarjetas se estiren en monitores panorámicos;
- Tarjetas con esquinas redondeadas (24 px de radio, hero de 28 px) y divisores sutiles de 1 px;
- Jerarquía tipográfica clara con títulos de sección en mayúsculas de bajo contraste;
- Controles segmentados con icono y etiqueta para modos de ruido, chips de nivel e interruptores;
- Azul HUAWEI `#0A59F7` reservado para estados activos, enlaces y acciones primarias;
- Iconos SVG de alta definición en molduras circulares de color;
- Pastillas verticales de batería con anillo, icono de auricular/estuche y porcentajes centrados;
- Pestañas separadas para **Visión general**, **Audio**, **Gestos**, **Conexión** y **Diagnóstico** (manteniendo registros y ajustes organizados).

![FreeBuds Client Overview](docs/ui/visao-geral.png)

Otras vistas: [Audio](docs/ui/audio.png), [Gestos](docs/ui/gestos.png), [Conexión](docs/ui/conexao.png), [Diagnóstico](docs/ui/diagnostico.png), [Modo Adaptativo](docs/ui/adaptavel.png) y [Estado Desconectado](docs/ui/desconectado.png).

## Características

- Detección y enumeración de Bluetooth Clásico utilizando APIs nativas de Windows.
- Asistencia de emparejamiento en Windows (`BluetoothAuthenticateDeviceEx`) sin omitir confirmaciones de seguridad.
- Transporte RFCOMM/SPP con reintento automático en canales conocidos (`1` y `16`) y almacenamiento de canal en caché.
- Códec de protocolo Huawei robusto: tramas `0x5A`, TLVs, CRC16/XMODEM y parser con soporte para fragmentación y ruido.
- Handshake de identificación (`0x0107`), lectura de batería (`0x0108`) y estado de ANC (`0x2B2A`).
- Control total de ANC mediante `0x2B04`: Desactivado, Cancelación (Estándar, Confort, Ultra, Dinámico), Transparencia y deslizador de Reconocimiento Adaptativo (1 a 11).
- API de cliente de alto nivel (`core/client.py`) con workers en segundo plano, reconexión automática y notificaciones de snapshots.
- CLI potente con salida legible y `--json`, inspección hexadecimal en bruto (`--raw`) y escucha en vivo (`--listen`).
- Interfaz gráfica moderna en PySide6 con integración en la bandeja del sistema, supervisión de batería y tema oscuro.
- Ajustes avanzados de audio: perfiles HUAWEI SOUND, audio espacial, volumen adaptativo y realce de voz.
- Personalización de gestos: pellizcar/mantener pulsado, doble toque, triple toque, control por movimiento de cabeza (asentir/negar) y lectura de deslizamiento.
- Gestión de conexión: prioridad de calidad de códec, modo de baja latencia para juegos, detección inteligente de uso y vista de multipunto.
- Soporte de internacionalización completo.
- Configuración persistente guardada en `%APPDATA%\FreeBudsClient\settings.json`.

## Requisitos

- Windows 10/11 con Bluetooth.
- Auriculares emparejados en Windows, encendidos y fuera del estuche de carga.

## Para Usuarios No Programadores

Hay disponible un archivo ejecutable oficial listo para descargar en la sección de [Releases](https://github.com/hrbtnog/freebuds-client/releases). También puedes compilar un ejecutable localmente siguiendo [Compilar un ejecutable (.exe)](#compilar-un-ejecutable-independiente-exe). Para ejecutar el proyecto desde el código fuente, instala Python y sigue los pasos a continuación.

## Instalación Local

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ui]"
```

Para usar únicamente la interfaz de línea de comandos (CLI):
```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\freebuds.exe list
```

## Compilar un Ejecutable Independiente (.exe)

En Windows, con el entorno virtual activado:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui]" pyinstaller
.\.venv\Scripts\pyinstaller.exe FreeBudsClient.spec --clean -y
```

El ejecutable se generará en `dist\FreeBudsClient.exe`.

## Uso de la CLI

```powershell
# Versión instalada
freebuds --version

# Listar dispositivos emparejados/conocidos por Windows
freebuds list
freebuds list --json

# Escanear dispositivos no emparejados (inquiry Bluetooth Clásico)
freebuds scan --seconds 8

# Escanear todos los dispositivos Bluetooth, no solo Huawei/HONOR
freebuds scan --seconds 8 --all

# Emparejamiento asistido
freebuds pair AA:BB:CC:DD:EE:FF

# Handshake + Batería + ANC (prueba canales 1 y 16 automáticamente)
freebuds probe --name "FreeBuds"

# Forzar canal específico, ver bytes TX/RX y formatear en JSON
freebuds probe --address AA:BB:CC:DD:EE:FF --channel 1 --json --raw

# Escuchar notificaciones entrantes durante 15 segundos tras la lectura inicial
freebuds probe --name FreeBuds --listen 15

# Decodificar cadena de bytes en hexadecimal o archivo
freebuds decode "5A0006002B03080100A79D"
freebuds decode --file capturas/spp.txt
```

## Uso de la UI

La interfaz gráfica utiliza PySide6 y puede iniciarse de tres maneras:

```powershell
# Comando CLI
freebuds ui

# Lanzador dedicado
freebuds-ui

# Como módulo de Python
python -m freebuds ui
```

Para conectar directamente a una dirección MAC:

```powershell
freebuds ui --address AA:BB:CC:DD:EE:FF
```

## Pruebas y Verificación

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m compileall -q src tests
```

La suite cubre tramas, decodificadores de comandos, sesiones simuladas de RFCOMM, flujos de cliente y verificaciones de interfaz gráfica (**89 pruebas pasando**).

## Estructura del Proyecto

```text
src/freebuds/
  core/
    protocol.py      # Tramas, TLV, CRC y parser incremental
    commands.py      # Códigos de comando y decodificación semántica
    client.py        # Cliente de alto nivel y snapshots
    transport.py     # Conexión socket RFCOMM/SPP
    session.py       # Hilo lector y correlación petición/respuesta
    windows_bt.py    # Enumeración Bluetooth Clásico en Windows
    models.py        # Clases de datos de estado
  config/
    settings.py      # Preferencias de usuario persistentes
  cli/
    app.py           # Comandos de consola
  ui/
    app.py           # Entrada de QApplication
    main_window.py   # Ventana principal, navegación lateral y páginas
    worker.py        # Hilos en segundo plano para conexión y sondeo
    widgets.py       # Hero, pastillas de batería, tarjetas ANC y registros
    tray.py          # Icono y menú de la bandeja del sistema
    theme.py         # Hoja de estilos estilo HarmonyOS oscuro
    icons.py         # Iconos de marca, bandeja y navegación
    svg_icons.py     # Renderizado y tintado de SVGs
    assets/          # Recursos visuales e iconos/*.svg
docs/
  ARCHITECTURE.md
  PROTOCOL.md
  CAPTURE_GUIDE.md
  PUBLISHING.md
  ui/                # Capturas de pantalla para la documentación
tests/
```

## Limitaciones Conocidas

- El protocolo y los identificadores fueron analizados mediante ingeniería inversa a partir de investigaciones públicas (OpenFreebuds, LibreBuds, mmk.pw, Gadgetbridge) y validados en FreeBuds Pro 5. La disponibilidad de funciones varía según modelo y firmware.
- La lectura de batería vía `0x0108` es la principal; algunas versiones de firmware envían notificaciones push `0x0127`.
- El estado de carga de componentes (`param 3` de `0x0108`) solo se muestra si el formato de datos coincide con la estructura esperada.
- No se admite la actualización de firmware ni se intentará aplicar ingeniería inversa para ello.
- El canal RFCOMM está preconfigurado por modelo (`1` o `16`); la consulta SDP dinámica mejoraría la resiliencia en futuras versiones.

## Cómo Contribuir

¡El proyecto agradece sugerencias, correcciones y pull requests!

- **¿Encontraste un error?** Abre un reporte de bug incluyendo modelo de auricular, versión de firmware, versión de Windows y registros.
- **¿Tienes una idea?** Envía una propuesta; no se requieren conocimientos de programación.
- **¿Quieres colaborar con código?** Revisa [`CONTRIBUTING.md`](CONTRIBUTING.md), corre los tests y abre una PR.
- **No compartas datos personales** en issues, capturas ni PRs.

## Seguridad y Alcance

- Utilízalo únicamente con hardware de tu propiedad.
- Nunca publiques direcciones Bluetooth completas o números de serie sin anonimizar.
- Comienza siempre con comandos de solo lectura. Cualquier comando de escritura debe respaldarse con capturas de paquetes y una ruta de reversión segura.
- Consulta [`SECURITY.md`](SECURITY.md) antes de enviar registros.

## Licencia

El código original de este proyecto está licenciado bajo la **Licencia MIT** — consulta [`LICENSE`](LICENSE). Las fotos de producto, iconos de terceros y marcas de fabricantes pertenecen a sus respectivos propietarios; consulta [`NOTICE.md`](NOTICE.md).

## Referencias y Agradecimientos

- OpenFreebuds — https://github.com/melianmiko/OpenFreebuds
- LibreBuds — https://github.com/librebuds/librebuds
- Protocolo FreeBuds 4i — https://mmk.pw/en/posts/freebuds-4i-proto/
- Freebuds playground — https://gist.github.com/melianmiko/02f7c6a550808e38d9b6760fb688e125
- Gadgetbridge (FreeBuds) — https://codeberg.org/Freeyourgadget/Gadgetbridge
- GalaxyBudsClient — https://github.com/timschneeb/GalaxyBudsClient

¡Gracias a todos los que probaron, reportaron problemas y compartieron información sobre el protocolo!
