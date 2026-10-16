# CrediNoda 💰

> **Sistema de escritorio moderno para la administración, simulación, cobranza y control de microcréditos y préstamos personales.**

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)
![UI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet)
![Database](https://img.shields.io/badge/database-SQLite3-lightgrey?logo=sqlite)
![Documents](https://img.shields.io/badge/PDF-ReportLab-red)
![Charts](https://img.shields.io/badge/charts-Matplotlib-orange)
![Packaging](https://img.shields.io/badge/build-PyInstaller%20.exe-informational)
![Code Style](https://img.shields.io/badge/code%20style-Ruff-261230?logo=ruff)

---

## 📖 Descripción del Proyecto

**CrediNoda** es una aplicación de escritorio todo-en-uno escrita en Python que permite gestionar de principio a fin el ciclo de vida de préstamos personales y microcréditos. Está diseñada específicamente para prestamistas independientes, fondos familiares, cooperativas pequeñas o negocios locales que requieren llevar un control contable exacto, emitir recibos formales y monitorear el estado de su cartera **100% offline** (sin depender de internet ni pagar suscripciones en la nube).

---

## 🎯 ¿Qué problema resuelve?

Llevar el control de préstamos y cobranzas en cuadernos físicos, notas del teléfono o en hojas de cálculo manuales (Excel) genera problemas críticos a medida que crece la cartera de clientes:

| Problema habitual (Cuadernos / Excel) | Cómo lo resuelve **CrediNoda** |
| :--- | :--- |
| **Desorden y pérdida de información:** Hojas dañadas, fórmulas borradas por accidente o archivos dispersos. | **Base de datos relacional centralizada (SQLite)** con copias de seguridad (backups) y restauración en un clic. |
| **Descuadre de centavos:** Al dividir un préstamo en cuotas semanales o quincenales, los decimales sobrantes crean diferencias al final del crédito. | **Algoritmo de ajuste contable exacto:** Usa redondeo bancario (`ROUND_HALF_UP`) y ajusta el residuo en la última cuota para que la suma cuadre al centavo. |
| **Disputas con clientes por pagos:** *"Yo ya le aboné esa cuota la semana pasada y no me la anotó"*. | **Comprobantes en PDF con Código QR:** Genera al instante recibos de caja formales listos para enviar por WhatsApp o imprimir, con saldo anterior, abono y saldo restante. |
| **Descontrol de cuotas atrasadas (Mora):** Revisar cliente por cliente para saber quién venció ayer o hace una semana. | **Detección automática de mora:** Identifica en tiempo real las cuotas vencidas sin perder el rastro de si tienen abonos parciales o están pendientes. |
| **Falta de visibilidad financiera:** No saber cuánto capital está en la calle, cuánto interés real se ha ganado o cuánto dinero debe entrar esta semana. | **Dashboard y Reportes Estadísticos:** Indicadores en tiempo real y gráficos de recaudación vs. proyección y distribución de cartera. |

---

## ✨ Características Principales

### 👥 1. Gestión de Clientes
* Registro de clientes con validación de documento de identidad único (C.C. / DNI / Pasaporte) y teléfono de contacto.
* Buscador instantáneo por nombre o número de documento.
* Ficha detallada por cliente con el resumen histórico de todos sus créditos (activos, pagados o con mora).

### 💳 2. Simulación y Otorgamiento de Créditos
* Cálculo bajo el modelo de **interés simple mensual** (tasa configurable por préstamo, 12% mensual por defecto).
* Frecuencias de cobro flexibles:
  * **Semanal** (4 cuotas por mes).
  * **Quincenal** (2 cuotas por mes).
* **Simulador interactivo:** Previsualiza el cronograma completo de pagos (fechas de vencimiento y montos exactos) antes de desembolsar el crédito.

### 💵 3. Cobranza Inteligente y Control Automático de Mora
* Soporte para **pagos totales** o **abonos parciales** sobre cualquier cuota.
* Bloqueo automático contra sobrepagos (impide cobrar por error un monto mayor al saldo pendiente de la cuota).
* **Transición automática de estados:**
  * Cuotas: `PENDIENTE` $\to$ `PARCIAL` $\to$ `PAGADA`.
  * Crédito: Pasa automáticamente de `ACTIVO` a `PAGADO` al liquidar la totalidad de sus cuotas.
* **Monitoreo de Mora en tiempo real:** Al iniciar la aplicación (y automáticamente al cambiar de día), el sistema marca en mora las cuotas cuya fecha de vencimiento ya pasó, conservando su estado de avance (`PENDIENTE` o `PARCIAL`).

### 📄 4. Recibos de Pago en PDF con Código QR
* Generación automática de **Comprobantes de Pago** profesionales con `ReportLab`.
* Incluye número de recibo único (`REC-00001`), datos del cliente, detalle del crédito, valor abonado, saldo restante de la cuota, saldo global del préstamo y barra/porcentaje de progreso.
* **Código QR integrado** con los metadatos de verificación de la transacción y espacio para firmas.
* Apertura automática en el lector de PDF del sistema o guardado en ruta personalizada.

### 📊 5. Dashboard y Reportes Financieros
* **Panel de Inicio (Dashboard):** Resumen de cartera activa, capital colocado, alertas de cuotas vencidas y tabla de próximos cobros.
* **Módulo de Reportes con filtros por fecha** (*Hoy, Esta Semana, Este Mes, Año o Rango Personalizado*):
  * KPIs financieros: Tasa de morosidad, margen de ganancia líquida cobrada, ticket promedio, etc.
  * **Gráfico de Barras:** Recaudos cobrados vs. Proyección esperada.
  * **Gráfico Circular (Donut/Pie):** Distribución de la cartera (*Al día, En mora, Saldados*).

### 💾 6. Copias de Seguridad y Restauración en Caliente
* Creación de respaldos completos de la base de datos en cualquier momento desde el menú lateral (**Copia de Seguridad**).
* Validación de integridad (`PRAGMA integrity_check`) antes de restaurar cualquier archivo.
* **Respaldo preventivo automático (`pre_restauracion`)** antes de sobrescribir datos para evitar pérdidas accidentales.

---

## 🚀 Cómo Usar el Proyecto

Puedes utilizar **CrediNoda** de dos maneras: ejecutando el código fuente con Python o generando el ejecutable independiente (`.exe`) para Windows.

### Opción A: Ejecutar desde el código fuente (Desarrollo / Multiplataforma)

#### 1. Requisitos previos
* **Python 3.10 o superior** instalado en tu equipo.
* **Git** (opcional, para clonar el repositorio).

#### 2. Instalación paso a paso

1. **Clona este repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/CrediNoda.git
   cd CrediNoda
   ```

2. **Crea y activa un entorno virtual:**
   * **En Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * **En Windows (CMD):**
     ```cmd
     python -m venv venv
     venv\Scripts\activate.bat
     ```
   * **En Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicia la aplicación:**
   ```bash
   python -m credito_app.main
   ```

---

### Opción B: Generar el Ejecutable `.exe` Portable para Windows

Si deseas usar el programa sin abrir la consola o distribuirlo a otra computadora con Windows que no tenga Python instalado:

```bash
python -m credito_app.build_exe
```

Al finalizar el proceso se crearán automáticamente en `credito_app/dist/`:
1. `CrediNoda.exe`: Ejecutable único con el ícono oficial.
2. `CrediNoda_Portable_Windows.zip`: Paquete listo para compartir o llevar en una memoria USB con sus carpetas de datos, comprobantes y respaldos.

---

## 📖 Guía Rápida de Uso (Flujo de Trabajo)

```text
[ 1. Crear Cliente ] ──▶ [ 2. Otorgar Crédito ] ──▶ [ 3. Registrar Abono ] ──▶ [ 4. Emitir Recibo PDF ]
                                                                                       │
                                                                                       ▼
                                                   [ 6. Backup de Datos ] ◀── [ 5. Revisar Reportes ]
```

1. **Registrar un Cliente:**
   * En el menú izquierdo, entra a **Clientes** y haz clic en **`+ Nuevo Cliente`**.
   * Ingresa el nombre completo, documento de identidad y teléfono.
2. **Simular y Crear un Crédito:**
   * Entra a la ficha del cliente y pulsa **`Nuevo Crédito`** (o desde la vista de créditos).
   * Ingresa el **Capital a prestar**, la **Tasa de interés mensual (%)**, el **Plazo en meses** y la **Frecuencia de pago** (*Semanal* o *Quincenal*).
   * Verifica la tabla de amortización generada en pantalla y haz clic en **`Crear Crédito`**.
3. **Registrar un Cobro (Total o Parcial):**
   * Abre el detalle del crédito, selecciona una cuota pendiente y haz clic en **`Registrar Pago`**.
   * Escribe el valor recibido (puedes abonar una parte o la cuota completa).
   * Mantén activa la opción **`Generar y abrir comprobante en PDF`** para obtener el recibo al instante.
4. **Consultar Historial y Reimprimir Recibos:**
   * En la sección **Pagos** del menú lateral puedes buscar cualquier cobro por nombre de cliente, número de crédito (`#12`) o número de recibo (`REC-00015`) y volver a exportar su PDF cuando lo necesites.
5. **Analizar el Negocio y Respaldar tu Información:**
   * Revisa **Dashboard** para tus cobros del día y **Reportes** para evaluar tus ganancias reales.
   * Antes de cerrar tu jornada, haz clic en **`Copia de Seguridad`** en la barra lateral y pulsa **`Crear Copia Ahora`** para guardar un respaldo seguro.

---

## 🏛️ Arquitectura y Estructura del Proyecto

El proyecto sigue una **Arquitectura en Capas (Layered Architecture)** con separación estricta entre interfaz gráfica, lógica de negocio y persistencia de datos:

```text
CrediNoda/
├── credito_app/
│   ├── main.py                  # Punto de entrada de la aplicación
│   ├── config.py                # Parámetros globales y rutas dinámicas (fuente / .exe)
│   ├── build_exe.py             # Script automatizado de compilación con PyInstaller
│   ├── assets/                  # Íconos y recursos gráficos de la aplicación
│   ├── modules/                 # Capa de Dominio: Entidades (@dataclass), Enums y Excepciones
│   │   ├── cliente.py
│   │   ├── credito.py
│   │   ├── cuota.py
│   │   ├── pago.py
│   │   └── excepciones.py
│   ├── services/                # Capa de Negocio: Casos de uso, cálculos y generación de archivos
│   │   ├── cliente_service.py
│   │   ├── credito_service.py
│   │   ├── pago_service.py
│   │   ├── reporte_service.py
│   │   ├── pdf_service.py
│   │   └── backup_service.py
│   ├── database/                # Capa de Persistencia: SQLite3 y Patrón Repositorio
│   │   ├── connection.py
│   │   ├── schema.py
│   │   └── repositories/
│   ├── ui/                      # Capa de Presentación: Interfaz Gráfica con CustomTkinter
│   │   ├── app.py               # Controlador principal y enrutador de vistas en caché
│   │   ├── theme.py             # Paleta de colores y tipografías
│   │   ├── components/          # Widgets reutilizables (Tablas, Diálogos, Tarjetas, Sidebar)
│   │   ├── views/               # Vistas principales (Dashboard, Clientes, Créditos, Pagos, Reportes)
│   │   └── utils/               # Formateadores de moneda, fechas y validadores de entrada
│   ├── data/                    # Base de datos local (creditos.db) [Ignorado en Git]
│   ├── comprobantes/            # Recibos de pago generados en PDF [Ignorado en Git]
│   ├── backups/                 # Copias de seguridad locales (.db) [Ignorado en Git]
│   └── tests/                   # Suite de pruebas unitarias y de integración
├── docs/                        # Documentación técnica y hoja de ruta (ROADMAP)
├── pyproject.toml               # Configuración de Pytest, Coverage y Ruff
├── requirements.txt             # Dependencias del proyecto
└── README.md                    # Documentación principal
```

---

## 🧪 Pruebas Automatizadas y Calidad de Código

El proyecto cuenta con una suite exhaustiva de pruebas automatizadas que validan la precisión matemática de los créditos, el cuadre de centavos, las restricciones de pagos, la detección de mora, las copias de seguridad y los diálogos de la interfaz gráfica usando bases de datos aisladas en memoria (`:memory:`) y directorios temporales.

* **Ejecutar todas las pruebas:**
  ```bash
  python -m pytest
  ```

* **Ejecutar pruebas con reporte de cobertura de código:**
  ```bash
  python -m pytest --cov=credito_app
  ```

* **Verificar el estilo y calidad del código con Ruff:**
  ```bash
  python -m ruff check .
  ```

---

## 🔒 Privacidad y Seguridad de los Datos

* **100% Local y Privado:** Todos los registros financieros y personales de tus clientes se guardan únicamente en tu equipo dentro de `credito_app/data/creditos.db`. Ningún dato se envía a internet.
* **Precisión Financiera:** Los montos monetarios se procesan utilizando el tipo `Decimal` de Python y se almacenan como texto exacto en SQLite, evitando los errores de coma flotante (`float`).

---

## 📄 Licencia

Este proyecto se distribuye bajo la **Licencia MIT**. Eres libre de usarlo, modificarlo y adaptarlo a tus necesidades.
