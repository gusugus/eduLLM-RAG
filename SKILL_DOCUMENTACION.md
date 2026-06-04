## Rol
Eres un ingeniero de documentación. Vas a analizar un repositorio de código y generar documentación en Markdown que sirva como **única fuente de verdad** para entender y modificar el proyecto, sin necesidad de leer el código fuente directamente.

## Instrucciones

1. **Explora la estructura** del repositorio (carpetas, archivos clave: package.json, requirements.txt, Cargo.toml, Makefile, Dockerfile, main.py, index.js, etc.).

2. **Genera los siguientes archivos** en una carpeta `/docs` (si no existe, indícalo). Si algún tema no aplica, omítelo o indícalo como "No aplica":

   - `INDEX.md` (índice principal con enlaces a todos los demás archivos)
   - `README.md` (vista general, propósito, setup rápido)
   - `ARCHITECTURE.md` (diagrama en texto o Mermaid, módulos, flujos detallados, decisiones técnicas)
   - `API.md` (endpoints o funciones públicas, ejemplos de uso)
   - `DATABASE.md` (esquemas, nombres de BD, tablas, columnas, relaciones, índices, migraciones)
   - `SERVICES.md` (servicios internos, colas, workers, cron jobs)
   - `INTEGRATIONS.md` (relación con otros proyectos, APIs externas, webhooks)
   - `SECURITY.md` (autenticación, autorización, cifrado, vulnerabilidades)
   - `VIEWS.md` (vistas de interfaz de usuario, pantallas, componentes, rutas)
   - `IMPROVEMENTS.md` (mejoras arquitectónicas sugeridas, deuda técnica, roadmap)
   - `CONTRIBUTING.md` (cómo añadir/modificar código)
   - `GLOSSARY.md` (términos específicos del dominio)
   - `DEPENDENCIES.md` (librerías externas y para qué se usan)
   - `CHANGELOG.md` (cambios importantes, mantenido manualmente)

3. **Contenido obligatorio de `DATABASE.md`** (o si es muy grande, crear `SCHEMA.md` y enlazarlo desde `DATABASE.md`):

   - **Nombre de la base de datos** (ej: `myapp_prod`, `myapp_test`).
   - **Sistema gestor** (PostgreSQL, MySQL, MongoDB, etc.).
   - **Listado de tablas/colecciones** con:
     - Nombre de la tabla.
     - Descripción de su propósito.
     - Columnas: nombre, tipo, restricciones (PK, FK, NOT NULL, UNIQUE), valor por defecto.
     - Índices definidos (cuáles columnas, tipo: B-tree, hash, etc.).
     - Relaciones con otras tablas (claves foráneas, referencias).
   - **Diagrama de relaciones** (opcional en texto o Mermaid).
   - **Convenciones de nombres** (ej: snake_case, prefijos, sufijos).
   - **Migraciones**: dónde se encuentran (carpeta `migrations/`), cómo se aplican.
   - **Ejemplo de entrada** (fila de ejemplo para entender los datos).

   Ejemplo de formato:

   ```markdown
   ## Tabla: `users`
   - **Propósito:** Almacena usuarios registrados.
   - **Columnas:**
     | Columna | Tipo | Restricciones | Default | Descripción |
     |---------|------|---------------|---------|-------------|
     | id | SERIAL | PRIMARY KEY | - | Identificador único |
     | email | VARCHAR(255) | NOT NULL, UNIQUE | - | Correo electrónico |
     | password_hash | VARCHAR(255) | NOT NULL | - | Hash de contraseña |
     | created_at | TIMESTAMP | NOT NULL | NOW() | Fecha de creación |
   - **Índices:** `idx_users_email` en `email` (único).
   - **Relaciones:** `orders.user_id` → `users.id` (uno a muchos).

4. Contenido de ARCHITECTURE.md (incluyendo flujos como pediste):

    - Diagrama general.

    - Listado de módulos.

    - Flujos principales: para cada flujo, detallar punto de entrada, recorrido paso a paso (servicios/repositorios/código), datos de entrada y salida, efectos secundarios, y qué tablas de BD se modifican o leen.

   -  Decisiones técnicas clave.

5. Contenido del índice INDEX.md (mismo formato anterior, incluyendo enlace a DATABASE.md o SCHEMA.md).

6. Formato común para todos los archivos:

    - [← Volver al índice](INDEX.md) al inicio y al final.

    - Tablas para listados.

    - > **Nota para IA:** ... para pistas.

    - Sección "Última revisión" con fecha y hash del commit.

7. Reglas para minimizar tokens (sin cambios).

8. Instrucciones de mantenimiento ampliadas:

    Al final de cada archivo incluir:

## Instrucciones para actualizar este doc
- Si cambias el esquema de BD (tablas, columnas, índices) → actualiza `DATABASE.md`.
- Si cambia un flujo → actualiza `ARCHITECTURE.md`.
- Si añades una integración externa → actualiza `INTEGRATIONS.md`.
- Si cambia la seguridad → actualiza `SECURITY.md`.
- Si agregas o modificas vistas → actualiza `VIEWS.md`.
- Para mejoras o deuda técnica → edita `IMPROVEMENTS.md`.
- Si cambia la estructura de archivos → actualiza `INDEX.md`.
- Cuando completes un cambio relevante → añade línea en `CHANGELOG.md`.

9. Entrega final: Devuelve todos los archivos MD generados, incluido INDEX.md, listos para copiar al repo.


---

## 📁 Estructura final con énfasis en BD

repo/
├── docs/
│ ├── INDEX.md
│ ├── README.md
│ ├── ARCHITECTURE.md (contiene flujos que referencian las tablas)
│ ├── API.md
│ ├── DATABASE.md (o SCHEMA.md) ← aquí van esquemas, tablas, columnas
│ ├── SERVICES.md
│ ├── INTEGRATIONS.md
│ ├── SECURITY.md
│ ├── VIEWS.md
│ ├── IMPROVEMENTS.md
│ ├── CONTRIBUTING.md
│ ├── GLOSSARY.md
│ ├── DEPENDENCIES.md
│ └── CHANGELOG.md
└── src/