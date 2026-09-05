# CrediNoda

Sistema de gestión de créditos simple con pagos parciales y cálculo de intereses fijos.

## Descripción

CrediNoda es una aplicación backend en Python para la administración de clientes, créditos y pagos. Está diseñada para negocios pequeños que manejan un interés mensual fijo y opciones de pago semanales o quincenales, permitiendo el registro de abonos parciales y el control del saldo pendiente.

## Requisitos

- Python 3.10 o superior
- SQLite3 (incluido en la biblioteca estándar de Python)
- `pytest` para la ejecución de pruebas (opcional)

## Estructura del Proyecto

```
credito_app/
├── database/
│   ├── connection.py
│   └── schema.py
├── modules/
│   ├── cliente.py
│   ├── credito.py
│   ├── pago.py
│   └── excepciones.py
├── services/
│   ├── cliente_service.py
│   ├── credito_service.py
│   └── pago_service.py
├── tests/
│   ├── test_cliente.py
│   ├── test_credito.py
│   └── test_pago.py
├── main.py
└── README.md
```

## Arquitectura

- **Módulos (`modules/`)**: Contienen los modelos de datos (implementados con `dataclasses`) y las enumeraciones necesarias para la lógica del negocio. También se definen las excepciones personalizadas de la aplicación.
- **Servicios (`services/`)**: Agrupan la lógica de negocio. Todas las operaciones de cálculo, creación de registros y transacciones de base de datos se manejan a través de los servicios (`ClienteService`, `CreditoService`, `PagoService`).
- **Base de Datos (`database/`)**: Se encarga de la conexión a la base de datos SQLite y la creación del esquema inicial de tablas.
- **Pruebas (`tests/`)**: Pruebas unitarias para los servicios utilizando una base de datos en memoria para garantizar aislamiento.

## Reglas de Negocio

- **Interés**: Se aplica un interés mensual simple por defecto del 12% sobre el capital inicial.
- **Frecuencia de Pago**: Los pagos pueden ser semanales (4 cuotas por mes) o quincenales (2 cuotas por mes).
- **Cálculo de Cuotas**: El monto de la cuota se determina sumando el capital y los intereses, dividido por el número total de cuotas.
- **Pagos**: Se permiten pagos completos o parciales de las cuotas. Una cuota solo se considera `PAGADA` cuando la suma de sus abonos iguala o supera el monto de la cuota.
- **Estados**: 
  - Créditos: `ACTIVO` o `PAGADO`
  - Cuotas: `PENDIENTE`, `PARCIAL` o `PAGADA`

## Cómo Ejecutar la Aplicación

Para ejecutar la demostración principal, que inicializa la base de datos y crea un caso de prueba con cliente, crédito y pagos:

Desde el directorio padre (`CrediNoda`):
```bash
python -m credito_app.main
```

O desde dentro del directorio `credito_app/`:
```bash
python main.py
```

## Cómo Ejecutar las Pruebas

Se recomienda usar `pytest` para ejecutar las pruebas.

Desde el directorio padre (`CrediNoda`):
```bash
python -m pytest credito_app/tests/ -v
```

Desde dentro del directorio `credito_app/`:
```bash
python -m pytest tests/ -v
```

Alternativamente, puedes usar `unittest` de la biblioteca estándar:
```bash
python -m unittest discover -s credito_app/tests -v
```

## Alcance Fase 1

La Fase 1 abarca exclusivamente el diseño de la lógica backend y la persistencia en base de datos. No incluye interfaz gráfica (GUI) ni endpoints HTTP (API REST). Todo el manejo se realiza a través de las clases de servicio.
