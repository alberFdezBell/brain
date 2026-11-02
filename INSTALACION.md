# Guía Completa de Instalación y Migración — Project Brain

> Sistema universal de memoria persistente, contexto y recuperación RAG para asistentes de IA (**Google Antigravity**, **Claude Code**, **OpenAI Codex / Cursor**).

---

## 1. Introducción y Arquitectura

**Project Brain** es una infraestructura de memoria persistente para el desarrollo de software asistido por IA. Permite que cualquier modelo o agente mantenga memoria acumulativa, aprenda de errores pasados, registre decisiones técnicas y consulte el historial de un proyecto sin saturar su ventana de contexto.

```
                           +---------------------------+
                           |     Asistentes de IA      |
                           | Antigravity / Claude /... |
                           +-------------+-------------+
                                         |
                       (Protocolo estricto: PROTOCOL.md)
                                         v
   +-----------------------------------------------------------------------+
   |                            PROJECT BRAIN                              |
   |                                                                       |
   |   +-----------------------+              +------------------------+   |
   |   |   Bóvedas (<slug>/)   |              |  Motor RAG & CLI       |   |
   |   | - Capa Caliente:      |              | - brain-ask            |   |
   |   |   context, index, todo| <----------> | - brain-index (BM25)   |   |
   |   | - Capa Fría:          |              | - brain-capture        |   |
   |   |   decisions, learnings|              | - brain-quality        |   |
   |   |   sessions, archive   |              | - brain-doctor         |   |
   |   +-----------------------+              +-----------+------------+   |
   |                                                      |                |
   |   +--------------------------------------------------v------------+   |
   |   |  Brain Chat (GUI Nativa de Escritorio)                        |   |
   |   |  llama.cpp standalone + Qwen2.5-1.5B (GGUF)                   |   |
   |   |  0 MB en reposo al cerrar • Modo oscuro DWM en Windows 11     |   |
   |   +---------------------------------------------------------------+   |
   +-----------------------------------------------------------------------+
```

---

## 2. Requisitos Previos

* **Python 3.10 o superior** (probado en Python 3.10, 3.11, 3.12, 3.13 y 3.14).
* **Git 2.30 o superior** (disponible en el `PATH`).
* **Sistema Operativo**: Windows 10/11, Linux (Ubuntu, Debian, Fedora, Arch) o macOS.
* *(Opcional)* **Obsidian** para explorar visualmente el grafo interactivo de notas y enlaces bidireccionales.

---

## 3. Instalación Automatizada (Recomendada)

Project Brain incluye instaladores desatendidos que configuran variables de entorno, directorios, dependencias e integraciones con un solo comando.

### A) En Windows (PowerShell)

Abre PowerShell y ejecuta:

```powershell
# 1. Clonar el repositorio en tu carpeta de usuario
git clone https://github.com/tu-usuario/brain.git "$HOME\Brain"
cd "$HOME\Brain"

# 2. Ejecutar el instalador automatizado
.\install.ps1
```

#### Opciones avanzadas del script en Windows:
* **Descarga completa del motor local**:
  ```powershell
  .\install.ps1 -DownloadModel
  ```
  *(Descarga `llama-server.exe` precompilado y los pesos de `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf` de ~986 MB en `tools\bin\`)*.
* **Instalación ultraligera sin modelos pesados**:
  ```powershell
  .\install.ps1 -SkipModel
  ```
* **Especificar ruta personalizada**:
  ```powershell
  .\install.ps1 -BrainHome "D:\MiBrain"
  ```

---

### B) En Linux / macOS (Bash)

Abre tu terminal y ejecuta:

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/brain.git "$HOME/Brain"
cd "$HOME/Brain"

# 2. Dar permisos y ejecutar
chmod +x install.sh
./install.sh
```

#### Opciones avanzadas del script en Unix:
* **Descarga automática de modelos y binarios**:
  ```bash
  ./install.sh --download-model
  ```
* **Modo ligero**:
  ```bash
  ./install.sh --skip-model
  ```

El script configurará automáticamente `export BRAIN_HOME="$HOME/Brain"` en tus archivos `~/.bashrc`, `~/.zshrc` y `~/.profile`.

---

## 4. Configuración para Asistentes de IA

Los scripts de instalación configuran estas integraciones automáticamente. Si deseas configurarlas o verificarlas manualmente:

### 1. Google Antigravity
Project Brain se conecta a Antigravity mediante una regla persistente y sus skills oficiales.

* **Regla global**: Añade al archivo `~/.gemini/AGENTS.md` (o en la regla del workspace `.gemini/rules/project-brain.md`):
  ```markdown
  # Project Brain - Memoria Persistente Obligatoria
  En cada sesión, chat y proyecto, debes leer y seguir obligatoriamente `$BRAIN_HOME/PROTOCOL.md` antes de actuar y antes de dar nada por terminado:
  1. **Inicio de sesión**: Leer capa caliente del proyecto (`<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`) y las 3 últimas sesiones. Ejecutar `python ~/Brain/tools/brain-capture.py --start --slug <slug>`.
  2. **Durante la sesión**: Registrar decisiones en `decisions/` y aprendizajes en `learnings/` con hechos reales y reproducibles.
  3. **Cierre de sesión / finalización de tarea**: La tarea NO está completa hasta que se ejecute `python ~/Brain/tools/brain-session.py --slug <slug>`, se completen las secciones narrativas obligatorias sin expresiones vagas, y pasen con éxito tanto `python ~/Brain/tools/brain-quality.py --strict --slug <slug>` como `python ~/Brain/tools/brain-commit.py --slug <slug>`.
  ```
* **Skills instaladas**: Las herramientas se exponen como skills en `~/.gemini/config/skills/` (`project-brain`, `brain-ask`, `brain-search`, `brain-save`, `brain-quality`, `brain-audit`, `brain-compact`).

### 2. Claude Code
Añade las instrucciones al archivo global `~/.claude/CLAUDE.md` o en la raíz de tus repositorios:

```markdown
## Memoria Persistente (Project Brain)
- En cada sesión y proyecto, lee y sigue `$BRAIN_HOME/PROTOCOL.md` (por defecto `~/Brain/PROTOCOL.md`) antes de actuar y antes de dar nada por terminado.
- **Al iniciar**: Lee capa caliente (`<slug>-index.md`, `<slug>-context.md`, `<slug>-todo.md`) y ejecuta `python ~/Brain/tools/brain-capture.py --start --slug <slug>`.
- **Durante**: Documenta decisiones técnicas y aprendizajes reales en `decisions/` y `learnings/`.
- **Al cerrar**: La tarea NO está completa hasta que `python ~/Brain/tools/brain-session.py --slug <slug>` genere la sesión, `python ~/Brain/tools/brain-quality.py --strict --slug <slug>` pase con score >= 85 sin expresiones vagas, y `python ~/Brain/tools/brain-commit.py --slug <slug>` guarde los cambios en git.
- **Consultas**: Responde preguntas retrospectivas usando `python ~/Brain/tools/brain-ask.py "<pregunta>" --project <slug>`.
```

### 3. OpenAI Codex / Cursor / Copilot CLI
Copia el archivo `adapters/codex.md` a `~/.codex/instructions.md`, o añade su contenido a tu archivo `.cursorrules` o `.github/copilot-instructions.md`.

---

## 5. Motor de Inferencia Local (Brain Chat)

Brain Chat incluye una interfaz de escritorio estilo ChatGPT escrita 100% en Python estándar (`tkinter`) que se conecta a un servidor local `llama.cpp` de arranque instantáneo.

### Colocación Manual de Pesos (si no usaste `-DownloadModel`)
Si no descargaste el modelo mediante el instalador, puedes colocar los archivos manualmente en `tools/bin/`:

1. **Binario `llama-server`**:
   * Descarga la última versión de [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases).
   * Para Windows: `llama-server.exe` (ej. build AVX2 x64).
   * Para Linux: `llama-server` con permisos de ejecución (`chmod +x`).
   * Guarda el binario en: `tools/bin/llama-server.exe` (Windows) o `tools/bin/llama-server` (Linux).
2. **Pesos del Modelo (GGUF)**:
   * Descarga [Qwen2.5-1.5B-Instruct-Q4_K_M.gguf](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf) (~986 MB).
   * Guárdalo exactamente en: `tools/bin/qwen2.5-1.5b-instruct-q4_k_m.gguf`.

### Ejecutar Brain Chat
```bash
python tools/brain_chat.py
```
* **Ventana Nativa con Dark Mode**: En Windows 11, la barra de título nativa se sincroniza con el color `#171717`.
* **Atajos de Edición**: Soporta `Ctrl+Delete` (borrado de palabra hacia adelante), `Ctrl+Backspace` y `Ctrl+A`.
* **Menciones Rápidas**: Escribe `@` para desplegar el autocompletado de proyectos (`@dj`, `@portafolio-dev`, etc.).
* **0 MB en reposo**: Al cerrar la ventana, el proceso del servidor `llama.cpp` se mata de inmediato liberando el 100% de la memoria RAM y CPU.

---

## 6. Acceso Directo en el Escritorio (Icono Cerebro y Cero Consolas)

Puedes crear un acceso directo en tu Escritorio para abrir **Brain Chat** con un solo doble clic, luciendo el icono nativo de `cerebro.ico` y ejecutándose limpiamente sin ventanas negras de consola.

### Opción A: Creación Automática (1 Comando)

* **En Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\create_shortcut.ps1
  ```
  *(Crea automáticamente `Project Brain.lnk` en tu Escritorio vinculado a `pythonw.exe` y a `assets\cerebro.ico`)*.

* **En Linux / macOS (Bash)**:
  ```bash
  chmod +x scripts/create_shortcut.sh
  ./scripts/create_shortcut.sh
  ```
  *(Crea un lanzador `.desktop` en `~/.local/share/applications/` y en tu Escritorio)*.

---

### Opción B: Creación Manual en Windows (Paso a Paso)

Si prefieres crearlo manualmente:

1. Ve a tu **Escritorio**, haz clic derecho en un espacio vacío y selecciona **Nuevo > Acceso directo**.
2. En la casilla **Escriba la ubicación del elemento**, introduce:
   ```cmd
   pythonw.exe "C:\Users\tu-usuario\Brain\tools\brain_chat.py"
   ```
   > [!TIP]
   > Usar `pythonw.exe` en lugar de `python.exe` es el truco estándar de Windows para ejecutar aplicaciones de interfaz gráfica de Python **sin que aparezca ninguna ventana negra de terminal de fondo**.
3. Haz clic en **Siguiente** y ponle de nombre: `Project Brain`.
4. Haz clic derecho sobre el acceso directo recién creado y selecciona **Propiedades**.
5. En la pestaña **Acceso directo**:
   * En **Iniciar en**, escribe la ruta a tu carpeta Brain: `C:\Users\tu-usuario\Brain`
   * Haz clic en el botón **Cambiar icono...**
   * Pulsa **Examinar...**, navega hasta `C:\Users\tu-usuario\Brain\assets\cerebro.ico` y selecciona el icono.
6. Pulsa **Aceptar** y luego **Aplicar**.

¡Listo! Ya tienes un icono de escritorio profesional con el cerebro que abre tu asistente local al instante.

---

## 7. Migración y Gestión de Bóvedas

Cada proyecto documentado vive dentro de su propia carpeta bóveda (`<slug>/`).

### Estructura de una Bóveda
```
Brain/<slug>/
├── .brain.yml                # Metadatos, slug, repo_path y versión de esquema
├── <slug>-context.md         # Stack, arquitectura, dependencias y estado
├── <slug>-index.md           # MOC (Mapa de Contenido) con enlaces bidireccionales
├── <slug>-todo.md            # Backlog priorizado y tareas recientes
├── decisions/                # Registros de arquitectura (ADRs)
├── learnings/                # Resolución de bugs y gotchas reproducibles
├── sessions/                 # Notas de sesiones de trabajo cronológicas
└── archive/                  # Sesiones compactadas para optimizar tokens
```

---

### Escenario 1: Mudar Project Brain a un Nuevo Ordenador o Disco

Cuando clonas o mueves tu carpeta `Brain` a una nueva máquina, es posible que las rutas locales a tus proyectos (`repo_path`) hayan cambiado (por ejemplo, de `C:\Users\antiguo\Desktop\proyecto` a `D:\Dev\proyecto` o `/home/usuario/dev/proyecto`).

**Pasos de migración:**

1. **Clonar o copiar la carpeta `Brain`**:
   ```bash
   git clone <tu-repo-de-brain> ~/Brain
   cd ~/Brain
   ```
2. **Ejecutar el instalador**:
   ```powershell
   # En Windows:
   .\install.ps1 -SkipModel
   # En Linux:
   ./install.sh --skip-model
   ```
3. **Actualizar rutas de repositorios (`repo_path`)**:
   Abre `<slug>/.brain.yml` en cada bóveda y actualiza la clave `repo_path` con la ruta real en tu nuevo equipo:
   ```yaml
   slug: mi-proyecto
   repo_path: /home/usuario/dev/mi-proyecto    # Ruta en el nuevo equipo
   schema_version: 1
   created_at: 2026-11-01T18:00:00+01:00
   ```
4. **Verificar estado con `brain-doctor`**:
   ```bash
   python tools/brain-doctor.py
   ```
   `brain-doctor` verificará que todas las carpetas `repo_path` existan en disco y reportará cualquier enlace roto.
5. **Reconstruir el índice de búsqueda BM25**:
   ```bash
   python tools/brain-index.py
   ```

---

### Escenario 2: Importar una Bóveda de Otro Proyecto o Equipo

Si un compañero de equipo te comparte una carpeta de bóveda (ej. `nueva-app/`):

1. **Copiar la carpeta a `$BRAIN_HOME`**:
   Coloca la carpeta `nueva-app/` directamente dentro de tu directorio `Brain/`.
2. **Ejecutar migraciones de esquema**:
   ```bash
   python tools/brain-migrate.py
   ```
   `brain-migrate.py` compara el `schema_version` de la bóveda importada contra `schema/VERSION` y aplica cualquier migración de estructura necesaria.
3. **Verificar integridad y calidad documental**:
   ```bash
   python tools/brain-lint.py
   python tools/brain-quality.py --strict --slug nueva-app
   ```
4. **Actualizar el índice de búsqueda global**:
   ```bash
   python tools/brain-index.py
   ```

---

### Escenario 3: Exportar o Respaldar una Bóveda Específica

Para compartir la memoria de un proyecto específico sin entregar todo tu almacén central:

1. **Comprimir la carpeta del proyecto**:
   ```bash
   # En Windows PowerShell:
   Compress-Archive -Path .\mi-proyecto -DestinationPath mi-proyecto-brain.zip
   # En Linux:
   tar -czvf mi-proyecto-brain.tar.gz mi-proyecto/
   ```
2. La bóveda es 100% autosuficiente: contiene sus notas en Markdown puro, metadatos YAML y enlaces bidireccionales compatibles con cualquier visor de Markdown o editor Obsidian.

---

### Escenario 4: Inicializar una Bóveda desde Cero

Para conectar un nuevo proyecto a Project Brain:

```bash
python tools/brain-init.py mi-nuevo-proyecto --repo-path "C:\Ruta\Al\Repositorio"
```
Esto creará la estructura estándar en `Brain/mi-nuevo-proyecto/` con sus plantillas iniciales.

---

## 8. Preparación y Subida a GitHub

Project Brain está configurado con un archivo `.gitignore` estricto que previene la fuga de pesos pesados (`*.gguf`), binarios (`*.exe`), archivos efímeros de caché (`.cache/`, `*.tmp`) y estados locales de Obsidian.

### Pasos para publicar en tu repositorio de GitHub:

```bash
# 1. Verificar estado del repositorio
git status

# 2. Si no has configurado tu remoto:
git remote add origin https://github.com/tu-usuario/brain.git

# 3. Asegurar rama principal
git branch -M main

# 4. Hacer commit y subir
git add .
git commit -m "feat: inicializacion de Project Brain con instaladores y chat local"
git push -u origin main
```

---

## 9. Tabla Rápida de Comandos CLI (Cheat Sheet)

| Comando | Descripción |
| :--- | :--- |
| `python tools/brain_chat.py` | Abre la aplicación de escritorio nativa estilo ChatGPT con motor local. |
| `python tools/brain-doctor.py` | Diagnóstico completo de entorno, dependencias, rutas y bóvedas. |
| `python tools/brain-index.py` | Reconstruye el índice BM25 de búsqueda rápida en `.cache/`. |
| `python tools/brain-ask.py "<pregunta>"` | Consulta RAG sobre las notas y decisiones documentadas. |
| `python tools/brain-init.py <slug> --repo-path <ruta>` | Inicializa una nueva bóveda para un repositorio de código. |
| `python tools/brain-capture.py --start --slug <slug>` | Registra el inicio de sesión y hash base de git. |
| `python tools/brain-quality.py --strict --slug <slug>` | Valida calidad estricta (100/100) sin placeholders ni vaguedades. |
| `python tools/brain-session.py --slug <slug>` | Genera la nota de sesión al finalizar una tarea. |
| `python tools/brain-commit.py --slug <slug>` | Valida calidad, linter y crea commit de memoria en Git. |
| `python tools/brain-migrate.py` | Aplica migraciones incrementales de esquema en todas las bóvedas. |
| `python tools/brain-lint.py` | Escanea secretos, enlaces rotos y notas huérfanas. |
| `python tools/brain-compact.py --slug <slug>` | Compacta sesiones antiguas en `archive/` para ahorrar tokens. |

---

## 10. Soporte y Licencia

Project Brain es software libre y de código abierto diseñado para maximizar la autonomía, reproducibilidad y memoria a largo plazo en equipos que desarrollan con inteligencia artificial.
