[← Volver al índice](INDEX.md)

# Guía para contribuir — RAG Service

Esta guía describe el flujo de desarrollo, las convenciones de código y cómo contribuir al microservicio de RAG.

---

## Flujo de desarrollo recomendado

1. **Crear una rama:** Crea una rama desde `main` con un nombre descriptivo:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   # o
   git checkout -b fix/nombre-del-bug
   ```

2. **Desarrollar y probar localmente:**
   - Escribe el código en las carpetas correspondientes (`api/`, `core/`, o `services/`).
   - Verifica que no rompas la API ejecutando la suite de pruebas o enviando peticiones de prueba a uvicorn.

3. **Formateo y Estilo:**
   - Sigue los estándares de PEP 8 para Python.
   - Utiliza `loguru` para logs informativos/depuración y `logging` estándar configurado con OpenTelemetry para logs integrados.

4. **Integración Continua:**
   - Al abrir un Pull Request (PR), se disparará un workflow de GitHub Actions (`.github/workflows/telegram-notify.yml`) que notificará al grupo de Telegram del equipo sobre el estado del PR (abierto, cerrado o solicitud de revisión).

---

## Estructura de ramas

- `main`: Contiene el código de producción estable. Todo PR debe integrarse aquí tras ser revisado y aprobado.
- `feature/*`: Desarrollo de nuevas características.
- `fix/*`: Correcciones de errores.

---

## Convenciones de código

- **Control de errores:** Utiliza `HTTPException` en la capa de endpoints (`api/routes.py`) para retornar códigos de estado HTTP semánticos (400, 401, 404, etc.) junto con un mensaje claro en `detail`.
- **Inyección de Dependencias:** Utiliza el sistema de inyección `Depends` de FastAPI para instanciar servicios. Evita crear instancias globales directamente dentro de las rutas, a menos que sean Singletons estrictos.
- **Tipado:** Utiliza `typing` (e.g. `List`, `Dict`, `Optional`, `Any`) de Python y validadores de `pydantic` para garantizar la integridad de los datos de entrada y salida.

---

## Última revisión

- **Fecha:** 2026-05-24
- **Commit:** `5cfbd82`

## Instrucciones para actualizar este doc

- Si cambias el workflow de CI/CD (GitHub Actions), actualiza la sección correspondiente.
- Si se añaden nuevas herramientas de formateo de código (como Black o Flake8), descríbelas aquí.
- Si cambia la estructura de archivos, actualiza [INDEX.md](INDEX.md).

[← Volver al índice](INDEX.md)
