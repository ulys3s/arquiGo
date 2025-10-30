# ConstruyeSeguro

ConstruyeSeguro es una plataforma integral para autoconstructores que ofrece generación automática de planos, manuales constructivos interactivos, videos educativos, un marketplace de profesionales y proveedores, y simulación de financiamiento.

La solución se divide en un backend en Flask y un frontend web responsivo compatible con empaquetado móvil mediante Capacitor o React Native WebView.

## Estructura del proyecto

```
.
├── backend/
│   ├── __init__.py          # Fábrica de aplicación Flask
│   ├── database.py          # Inicialización y consultas SQLite
│   ├── routes.py            # API REST principal
│   ├── services/
│   │   ├── financing.py     # Productos y simulador de financiamiento
│   │   ├── manual_builder.py# Manuales y generación de PDF
│   │   ├── marketplace.py   # Arquitectos, proveedores y alertas
│   │   ├── plan_generator.py# IA basada en plantillas para planos
│   │   └── youtube_service.py # Catálogo de videos educativos
│   └── validation.py        # Validación de formularios del proyecto
├── frontend/
│   ├── index.html           # SPA estática con Tailwind + Leaflet
│   ├── js/
│   │   ├── app.js           # Lógica de UI y consumo de APIs
│   │   └── offline.js       # Manejo de cache local y service worker
│   ├── assets/
│   │   ├── styles.css       # Estilos complementarios
│   │   └── manifest.json    # Manifest PWA para empaquetado móvil
│   └── service-worker.js    # Caché offline básico
├── construyeseguro.py       # Punto de entrada para ejecutar Flask
├── construyeseguro.db       # Base de datos SQLite (se crea/actualiza automáticamente)
└── README.md
```

## Requisitos

- Python 3.11+
- Pipenv o `pip` convencional

## Instalación y ejecución

1. Crear entorno virtual y dependencias básicas:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install flask
   ```

   > SQLite viene incluido con Python. No se requieren dependencias externas para la generación del PDF.

2. Iniciar el servidor backend:

   ```bash
   python construyeseguro.py
   ```

   El servidor quedará disponible en `http://localhost:5000`. Al iniciar se crearán las tablas necesarias y datos de ejemplo.

3. Abrir el frontend navegando a `http://localhost:5000`.

## Funcionalidades principales

- **Formulario “Mi Proyecto”**: campos predefinidos y checklists que alimentan al generador de planos.
- **Generación automática de planos**: presenta tres opciones (Proyecto A/B/C) con compatibilidad, SVG 2D y volúmenes 3D simplificados.
- **Manual constructivo**: pasos con videos asociados, materiales por etapa y exportación a PDF.
- **Videos educativos**: biblioteca filtrable con integración a YouTube mediante IDs almacenados en la base de datos.
- **Marketplace**: arquitectos verificados, proveedores locales y mapa interactivo con Leaflet.
- **Financiamiento**: listado filtrable y simulador de pagos mensuales.
- **Extras**: modo offline básico, alertas de seguridad, botón de asistencia inmediata y testimonios reales.

## Exportación del manual a PDF

Cada vez que se genera un proyecto se crea automáticamente un PDF ligero en `backend/generated/manual_<id>.pdf`. El enlace “Descargar manual PDF” obtiene dicho archivo vía `GET /api/projects/<id>/manual/pdf`.

## Empaquetado móvil

El frontend es una SPA estática compatible con empaquetado mediante [Capacitor](https://capacitorjs.com/) o una WebView en React Native. Pasos sugeridos con Capacitor:

1. Inicializar un proyecto Capacitor apuntando al directorio `frontend` como `webDir`.
2. Ejecutar `npx cap add android` o `ios` para generar las plataformas.
3. Sincronizar los archivos con `npx cap sync` y compilar desde Android Studio o Xcode.

## API REST

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| POST | `/api/projects` | Genera proyecto completo (planos, manual, materiales, alertas). |
| GET | `/api/projects/<id>` | Recupera un proyecto almacenado. |
| GET | `/api/projects/<id>/manual/pdf` | Descarga el manual en PDF. |
| GET | `/api/manual/steps` | Manual base por niveles con videos sugeridos. |
| GET | `/api/videos` | Listado filtrable de videos educativos. |
| GET | `/api/marketplace/architects` | Arquitectos verificados. |
| GET | `/api/marketplace/suppliers` | Proveedores locales. |
| GET | `/api/marketplace/alerts` | Alertas de seguridad recomendadas. |
| GET | `/api/maps/suppliers` | Coordenadas para el mapa interactivo. |
| GET | `/api/financing/products` | Productos de crédito filtrables. |
| GET | `/api/financing/simulate` | Simulador de pagos con tasa plana. |
| GET | `/api/testimonials` | Testimonios cargados desde la base de datos. |

Todas las respuestas son JSON codificado en UTF-8.

## Datos y persistencia

- La base de datos SQLite se inicializa con arquitectos, proveedores, videos, financiamientos y testimonios de ejemplo.
- Cada proyecto creado almacena el formulario original y los resultados generados para futuras consultas.

## Desarrollo y pruebas

- Ejecuta `python -m compileall backend frontend/js` para validar sintaxis rápida.
- Para pruebas manuales, usa herramientas como `curl` o `HTTPie` apuntando al API.

## Licencia

Este proyecto se entrega como referencia y puede adaptarse libremente a las necesidades de tu organización.
