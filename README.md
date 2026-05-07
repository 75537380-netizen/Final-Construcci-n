# Steam Price Checker

Aplicacion web para consultar ofertas de videojuegos en Steam, ver precios por region y comparar el precio actual con un minimo historico de referencia.

## Descripcion

Steam Price Checker permite:

- Buscar juegos por nombre.
- Explorar ofertas activas desde la portada.
- Filtrar resultados por generos y tags de Steam.
- Cambiar la region para visualizar precios en distintas monedas.
- Ver el detalle de cada juego con informacion general y comparacion grafica de precios.
- Consultar el minimo historico usando CheapShark como referencia externa.

El proyecto esta desarrollado como una SPA ligera con frontend en HTML, CSS y JavaScript vanilla, y backend en Python con FastAPI.

## Tecnologias utilizadas

- Python 3.11
- FastAPI
- Uvicorn
- httpx
- HTML5
- CSS3
- JavaScript
- Chart.js
- pytest
- pytest-asyncio
- Docker

## Requisitos previos

- Python 3.11 o superior
- pip
- Docker opcional, si deseas ejecutar el proyecto en contenedor

No se necesita base de datos ni claves de API externas.

## Ejecucion local

### 1. Crear entorno virtual

```bash
python -m venv .venv
```

### 2. Activar entorno virtual

PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

CMD:

```bash
.\.venv\Scripts\activate.bat
```

Linux o macOS:

```bash
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar el servidor

```bash
uvicorn app.main:app --reload
```

La aplicacion queda disponible en:

```text
http://127.0.0.1:8000
```

## Pruebas

Para ejecutar todas las pruebas:

```bash
python -m pytest tests/ -q
```

Para ver mas detalle:

```bash
python -m pytest tests/ -v
```

Resultado esperado:

```text
27 passed
```

## Docker

Construir la imagen:

```bash
docker build -t steam-price-checker .
```

Ejecutar el contenedor:

```bash
docker run -p 8000:8000 steam-price-checker
```

Con Docker Compose:

```bash
docker-compose up --build
```

## Endpoints principales

- `GET /`
- `GET /api/search?q=NAME&cc=US`
- `GET /api/game/{appid}?cc=US`
- `GET /api/featured-deals?category=specials&cc=US&start=0`
- `GET /api/deals?page=0&page_size=24&cc=US`
- `GET /api/genre?tags=19,699&cc=US&start=0`
- `GET /api/genres`

Documentacion automatica:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Estructura del proyecto

```text
steam-price-checker/
├── app/
│   ├── main.py
│   ├── services/
│   │   ├── steam.py
│   │   └── cheapshark.py
│   └── static/
│       ├── index.html
│       ├── css/style.css
│       └── js/app.js
├── docs/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pytest.ini
```

## Caracteristicas del proyecto

- Busqueda por nombre de juego.
- Filtros por genero con tags de Steam.
- Soporte multi-moneda por region.
- Comparacion entre precio actual, precio base y minimo historico.
- Interfaz inspirada visualmente en Steam.
- Pruebas unitarias para la capa de servicios.
