# API Demo con FastAPI + Uvicorn + Docker

API REST de ejemplo (CRUD de *items*) construida con **Python 3.11**, **FastAPI**, **Pydantic v2**, **Uvicorn** y **PostgreSQL 16**, lista para ejecutarse con **Docker** y **Docker Compose**.

Incluye:

- CRUD completo (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) con almacenamiento persistente en PostgreSQL.
- Validación y serialización con Pydantic v2 + documentación interactiva en Swagger UI y ReDoc.
- Paginación (`limit` / `offset`), búsqueda por texto (`q`) y filtro por stock (`in_stock`).
- Códigos de estado correctos (`201`, `204`, `404`, `409`, `422`) y cabecera `Location` al crear.
- Configuración por variables de entorno (archivo `.env` en la raíz).
- Imagen Docker con usuario sin privilegios, `HEALTHCHECK` y Compose con una red para API y base de datos.
- Inicialización automática del schema SQL y carga opcional de 3 items de ejemplo.
- Pruebas automatizadas con `pytest` (usan un repositorio aislado en memoria, sin requerir PostgreSQL).

---

## 1. Estructura del proyecto

```text
Lab/
├── app/                        # Código de la aplicación
│   ├── __init__.py
│   ├── config.py               # Configuración tipada (pydantic-settings)
│   ├── dependencies.py         # Dependencias de FastAPI (repositorio)
│   ├── main.py                 # Punto de entrada: app, CORS, routers, / y /health
│   ├── models.py               # Esquemas Pydantic de entrada/salida
│   ├── repository.py           # Repositorio PostgreSQL asíncrono (CRUD)
│   ├── requirements.txt        # Dependencias de ejecución
│   ├── requirements-dev.txt    # Dependencias para pruebas
│   ├── routers/
│   │   ├── __init__.py
│   │   └── items.py            # Endpoints /api/v1/items
│   └── tests/
│       ├── __init__.py
│       ├── fakes.py            # Repositorio en memoria para pruebas
│       └── test_api.py         # Pruebas HTTP
├── .dockerignore
├── .env                        # Variables de entorno usadas por la app y Compose
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
├── database/
│   └── init.sql                # Creación de la tabla e índice de items
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 2. Requisitos previos

| Herramienta | Versión mínima | Verificación |
|---|---|---|
| Docker Engine / Docker Desktop | 20.10 | `docker --version` |
| Docker Compose (plugin v2) | 2.0 | `docker compose version` |

> Todos los comandos de este README se ejecutan **desde la raíz del proyecto** (la carpeta que contiene `docker-compose.yml`).
>
> Si además quieres ejecutar la app o las pruebas **sin Docker**, necesitas **Python 3.11+** (`python --version`).

Antes de empezar, comprueba que el motor de Docker está activo:

```bash
docker info
```

Si aparece un error de conexión, inicia **Docker Desktop** y espera a que el motor termine de arrancar.

---

## 3. Variables de entorno

La configuración vive en `.env` (raíz del proyecto). Se entrega un archivo `.env` funcional y una plantilla `.env.example`:

```bash
# En Linux / macOS / Git Bash
cp .env.example .env

# En PowerShell
Copy-Item .env.example .env
```

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `APP_NAME` | `FastAPI Demo API` | Nombre mostrado en la documentación |
| `APP_VERSION` | `1.0.0` | Versión reportada por `/health` y `/` |
| `ENVIRONMENT` | `development` | Entorno lógico (`development`, `staging`, `production`) |
| `DEBUG` | `true` | Activa el modo depuración de FastAPI |
| `LOG_LEVEL` | `info` | Nivel de logging (`debug`, `info`, `warning`, `error`) |
| `API_PREFIX` | `/api/v1` | Prefijo de los endpoints de negocio |
| `CORS_ORIGINS` | `*` | Orígenes permitidos, separados por comas (`*` = todos) |
| `SEED_DEMO_DATA` | `true` | Inserta 3 items de ejemplo si la tabla está vacía |
| `DATABASE_URL` | `postgresql://app:app@db:5432/itemsdb` | Cadena de conexión PostgreSQL de la API |
| `POSTGRES_DB` | `itemsdb` | Nombre de la base de datos en Compose |
| `POSTGRES_USER` | `app` | Usuario de PostgreSQL en Compose |
| `POSTGRES_PASSWORD` | `app` | Contraseña de PostgreSQL en Compose |
| `APP_PORT` | `8000` | **Solo Compose**: puerto del host publicado hacia el `8000` del contenedor |

> `APP_PORT` no la lee la aplicación: se usa únicamente para el mapeo de puertos de `docker-compose.yml`.
> Si cambias `POSTGRES_DB`, `POSTGRES_USER` o `POSTGRES_PASSWORD`, configura también `DATABASE_URL` con esos mismos valores.

---

## 4. Ejecución con Docker Compose (recomendado)

### 4.1 Construir y levantar

```bash
docker compose up --build
```

- `--build` fuerza la reconstrucción de la imagen (necesario la primera vez y tras cambiar código o dependencias).
- Compose crea la base PostgreSQL 16, espera a que pase su healthcheck y luego inicia la API.
- `database/init.sql` se ejecuta automáticamente al inicializar por primera vez el volumen de PostgreSQL.
- Los logs de Uvicorn se muestran en la terminal.

Para dejarlo corriendo en segundo plano:

```bash
docker compose up -d --build
```

### 4.2 Verificar el estado

```bash
docker compose ps
```

Debes ver los servicios `api` y `db` con estado `healthy`. Los contenedores se llaman `fastapi-demo-api` y `fastapi-demo-db`.

La base de datos conserva los items mediante el volumen `postgres_data`. El script de inicialización se ejecuta únicamente cuando PostgreSQL crea un directorio de datos vacío. Para volver a inicializarlo desde cero y eliminar los datos persistidos, ejecuta `docker compose down -v` y después `docker compose up --build`.

```bash
# Seguir los logs en vivo
docker compose logs -f

# Últimas 50 líneas
docker compose logs --tail 50
```

### 4.3 Cambiar el puerto

Si el puerto `8000` está ocupado (error `bind: address already in use`), edita `.env`:

```dotenv
APP_PORT=8100
```

Y vuelve a levantar el servicio:

```bash
docker compose up -d
```

La API quedará en `http://localhost:8100`. También puedes sobrescribirlo solo para un comando:

```bash
# Linux / macOS / Git Bash
APP_PORT=8100 docker compose up -d

# PowerShell
$env:APP_PORT="8100"; docker compose up -d
```

---

## 5. Cómo probar la aplicación

### 5.1 Verificación rápida (30 segundos)

Con la API en marcha en `http://localhost:8000`:

| # | Acción | Resultado esperado |
|---|---|---|
| 1 | Abrir <http://localhost:8000/health> | `{"status":"ok","environment":"development","version":"1.0.0"}` |
| 2 | Abrir <http://localhost:8000/> | Nombre, versión y rutas de documentación |
| 3 | Abrir <http://localhost:8000/docs> | Swagger UI interactivo |
| 4 | Abrir <http://localhost:8000/api/v1/items> | 3 items de ejemplo (`total: 3`) |
| 5 | `docker compose ps` | Estado `healthy` |

### 5.2 Endpoints disponibles

| Método | Ruta | Descripción | Respuesta correcta |
|---|---|---|---|
| `GET` | `/` | Información de la API | `200` |
| `GET` | `/health` | Estado de salud (usado por el healthcheck) | `200` |
| `GET` | `/docs` | Swagger UI | `200` |
| `GET` | `/redoc` | ReDoc | `200` |
| `GET` | `/openapi.json` | Esquema OpenAPI | `200` |
| `GET` | `/api/v1/items` | Lista paginada con filtros `q`, `in_stock`, `limit`, `offset` | `200` |
| `GET` | `/api/v1/items/{item_id}` | Obtiene un item | `200` / `404` |
| `POST` | `/api/v1/items` | Crea un item (cabecera `Location`) | `201` / `409` / `422` |
| `PUT` | `/api/v1/items/{item_id}` | Reemplaza un item completo | `200` / `404` / `409` / `422` |
| `PATCH` | `/api/v1/items/{item_id}` | Actualiza campos parciales | `200` / `404` / `409` / `422` |
| `DELETE` | `/api/v1/items/{item_id}` | Elimina un item | `204` / `404` |

Los items creados con `SEED_DEMO_DATA=true` son:

| id | name | price | in_stock |
|---|---|---|---|
| 1 | Teclado mecánico | 49.99 | true |
| 2 | Mouse inalámbrico | 19.99 | true |
| 3 | Monitor 27 pulgadas | 299.0 | false |

### 5.3 Prueba guiada con `curl` (Linux, macOS, WSL o Git Bash)

Ejecuta los bloques **en orden** y compara cada resultado con el esperado.

**Paso 0 — variable con la URL base**

```bash
BASE=http://localhost:8000
```

**Paso 1 — estado de salud**

```bash
curl -s $BASE/health
```

Esperado: `{"status":"ok","environment":"development","version":"1.0.0"}`

**Paso 2 — listar la primera página**

```bash
curl -s "$BASE/api/v1/items?limit=2&offset=0"
```

Esperado: `total: 3`, `limit: 2`, dos elementos en `items`.

**Paso 3 — filtrar**

```bash
# Búsqueda por texto (nombre o descripción)
curl -s "$BASE/api/v1/items?q=monitor"

# Solo items sin stock
curl -s "$BASE/api/v1/items?in_stock=false"
```

Esperado: en ambos casos el monitor (id 3) y `total: 1`.

**Paso 4 — obtener un item por id**

```bash
curl -s $BASE/api/v1/items/1
```

Esperado: el item `Teclado mecánico`.

**Paso 5 — crear un item**

```bash
curl -s -i -X POST $BASE/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Webcam Full HD",
        "description": "Cámara USB 1080p con micrófono",
        "price": 35.5,
        "tags": ["video", "streaming"],
        "in_stock": true
      }'
```

Esperado: `201 Created`, cabecera `Location` con la URL del recurso y cuerpo con `"id": 4`.

**Paso 6 — actualización parcial (PATCH)**

```bash
curl -s -X PATCH $BASE/api/v1/items/4 \
  -H "Content-Type: application/json" \
  -d '{"price": 29.99, "in_stock": false}'
```

Esperado: `price: 29.99`, `in_stock: false` y el resto de campos sin cambios.

**Paso 7 — reemplazo completo (PUT)**

```bash
curl -s -X PUT $BASE/api/v1/items/4 \
  -H "Content-Type: application/json" \
  -d '{"name": "Webcam 4K", "description": null, "price": 89.0, "tags": [], "in_stock": true}'
```

Esperado: el item queda exactamente con esos valores e `id: 4`.

**Paso 8 — eliminar y comprobar**

```bash
curl -s -o /dev/null -w "DELETE -> %{http_code}\n" -X DELETE $BASE/api/v1/items/4
curl -s -o /dev/null -w "GET    -> %{http_code}\n" $BASE/api/v1/items/4
```

Esperado: `204` y luego `404`.

**Paso 9 — casos de error**

```bash
# Recurso inexistente -> 404
curl -s -o /dev/null -w "404 esperado -> %{http_code}\n" $BASE/api/v1/items/999

# Nombre duplicado (sin distinguir mayúsculas) -> 409
curl -s -o /dev/null -w "409 esperado -> %{http_code}\n" -X POST $BASE/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "teclado mecánico", "price": 10}'

# Precio inválido -> 422
curl -s -o /dev/null -w "422 esperado -> %{http_code}\n" -X POST $BASE/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Item inválido", "price": 0}'
```

### 5.4 Prueba guiada con PowerShell (`Invoke-RestMethod`)

> En PowerShell, `curl` es un alias de `Invoke-WebRequest` y **no** acepta las mismas opciones. Usa `Invoke-RestMethod` (o `curl.exe`). Para ver bien los acentos en consola: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`.

```powershell
$base = "http://localhost:8000"

# 1) Salud y raíz
Invoke-RestMethod "$base/health" | ConvertTo-Json
Invoke-RestMethod "$base/"       | ConvertTo-Json

# 2) Listar con filtros
Invoke-RestMethod "$base/api/v1/items?limit=2&offset=0" | ConvertTo-Json -Depth 5
Invoke-RestMethod "$base/api/v1/items?q=monitor&in_stock=false" | ConvertTo-Json -Depth 5

# 3) Crear
$body = @{
    name        = "Webcam Full HD"
    description = "Cámara USB 1080p con micrófono"
    price       = 35.5
    tags        = @("video", "streaming")
    in_stock    = $true
} | ConvertTo-Json

$item = Invoke-RestMethod -Method Post -Uri "$base/api/v1/items" `
    -ContentType "application/json; charset=utf-8" -Body $body
$item | ConvertTo-Json

# 4) Actualización parcial
Invoke-RestMethod -Method Patch -Uri "$base/api/v1/items/$($item.id)" `
    -ContentType "application/json" -Body (@{ price = 29.99 } | ConvertTo-Json) |
    ConvertTo-Json

# 5) Reemplazo completo
$replacement = @{ name = "Webcam 4K"; description = $null; price = 89.0; tags = @(); in_stock = $true } |
    ConvertTo-Json
Invoke-RestMethod -Method Put -Uri "$base/api/v1/items/$($item.id)" `
    -ContentType "application/json" -Body $replacement | ConvertTo-Json

# 6) Eliminar
Invoke-RestMethod -Method Delete -Uri "$base/api/v1/items/$($item.id)"
"Item $($item.id) eliminado"
```

### 5.5 Prueba desde el navegador con Swagger UI

1. Abre <http://localhost:8000/docs>.
2. Despliega `POST /api/v1/items` → **Try it out**.
3. Reemplaza el cuerpo por:

   ```json
   {
     "name": "Silla ergonómica",
     "description": "Silla con soporte lumbar",
     "price": 149.9,
     "tags": ["muebles", "oficina"],
     "in_stock": true
   }
   ```

4. Pulsa **Execute**. Verifica la respuesta `201` y la cabecera `location`.
5. Despliega `GET /api/v1/items` → **Try it out** → **Execute**: el nuevo item aparece en la lista.
6. Despliega `GET /api/v1/items/{item_id}`, usa el `id` devuelto y comprueba el `200`.
7. En `DELETE /api/v1/items/{item_id}` elimina el item y confirma el `204`.

El esquema OpenAPI completo está en <http://localhost:8000/openapi.json>.

---

## 6. Ejecutar las pruebas automatizadas

Las pruebas usan `pytest`, el `TestClient` de FastAPI y un doble del repositorio en memoria; no requieren Docker ni un servidor PostgreSQL levantado.

```powershell
# Windows (PowerShell), desde la raíz del proyecto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r app/requirements-dev.txt
python -m pytest app/tests -q
```

```bash
# Linux / macOS / Git Bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r app/requirements-dev.txt
python -m pytest app/tests -q
```

Salida esperada:

```text
11 passed
```

Cobertura de las pruebas: salud, raíz, paginación, filtros, creación, duplicados (`409`), validación (`422`), `404`, `PATCH`, `PUT` y `DELETE`.

---

## 7. Ejecutar sin Docker (opcional, para desarrollo)

```bash
# 1. Crear y activar el entorno virtual (ver sección 6)
# 2. Instalar dependencias de ejecución
python -m pip install -r app/requirements.txt

# 3. Arrancar con recarga automática
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Ejecuta el comando **desde la raíz del proyecto** para que se lea `.env`.
- Si lanzas Uvicorn desde otra carpeta, define las variables de entorno manualmente.
- Documentación: <http://127.0.0.1:8000/docs>.

Para probar la app en caliente dentro de Docker (código montado como volumen):

```bash
# Linux / macOS / Git Bash
docker compose run --rm -p 8000:8000 -v "$(pwd)/app:/code/app" api \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# PowerShell
docker compose run --rm -p 8000:8000 -v "${PWD}/app:/code/app" api `
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 8. Detener y limpiar

```bash
# Detener y eliminar el contenedor y la red
docker compose down

# Además, eliminar la imagen construida localmente
docker compose down --rmi local

# Reconstruir desde cero (ignorando la caché de capas)
docker compose build --no-cache
docker compose up -d
```

> Los datos de PostgreSQL se guardan en el volumen `postgres_data`; `docker compose down` lo conserva.

---

## 9. Solución de problemas

| Síntoma | Causa / solución |
|---|---|
| `bind: address already in use` al levantar | El puerto del host está ocupado. Cambia `APP_PORT` en `.env` (por ejemplo `8100`) y ejecuta `docker compose up -d`. Para ver qué proceso lo usa: `Get-NetTCPConnection -LocalPort 8000 -State Listen` (PowerShell) o `lsof -i :8000` (Linux/macOS). |
| `Cannot connect to the Docker daemon` | Docker Desktop/Engine no está iniciado. `docker info` debe responder sin errores. |
| La API responde pero mis cambios de código no aparecen | La imagen se construyó antes del cambio: `docker compose up -d --build`. |
| Cambié `.env` y no se aplica | Compose solo recrea el contenedor si detecta cambios: `docker compose up -d --force-recreate`. |
| `docker compose ps` muestra `starting` | Es normal durante los primeros ~40 s (`start_period` + `interval` del healthcheck). Espera y vuelve a comprobar. |
| Los datos desaparecen al reiniciar | Comprueba que el volumen `postgres_data` no se haya eliminado con `docker compose down -v`. |
| `curl` no reconoce `-H` o `-X` en PowerShell | `curl` es un alias de `Invoke-WebRequest`. Usa `curl.exe` o `Invoke-RestMethod` (sección 5.4). |
| JSON con comillas falla en PowerShell 5.1 | Las comillas dobles se pierden al pasarlas a programas nativos. Usa `Invoke-RestMethod` con `ConvertTo-Json` o `curl.exe --data-binary "@archivo.json"`. |
| `400 Bad Request` al enviar acentos desde PowerShell | El cuerpo se codificó con una página de códigos distinta de UTF-8. Añade `-ContentType "application/json; charset=utf-8"` o envía el JSON desde un archivo con `curl.exe --data-binary "@cuerpo.json"`. |
| Acentos mal mostrados en la terminal | Configura `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` (los datos almacenados están correctos en UTF-8). |
| Healthcheck en estado `unhealthy` | Revisa `docker compose logs`. Suele indicar un fallo al importar la app o un puerto interno distinto de `8000`. |

---

## 10. Notas y limitaciones

- PostgreSQL y la API comparten una única red de Compose. El SQL de inicialización solo se ejecuta al crear un volumen de datos vacío.
- No hay autenticación ni autorización; `CORS_ORIGINS=*` está pensado para la demo.
- `DEBUG=true` no debe usarse en producción (recomendado `DEBUG=false`, `ENVIRONMENT=production`).
- Las credenciales incluidas son de ejemplo. En producción, gestiona secretos fuera de `.env` y agrega controles de acceso, logging estructurado y límites de tasa.
- El contenedor se ejecuta con el usuario sin privilegios `appuser` (UID 1001) y expone el puerto `8000`.
