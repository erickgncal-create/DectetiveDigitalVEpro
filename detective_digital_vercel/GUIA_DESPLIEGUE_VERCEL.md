# Guía de Despliegue en Vercel — Detective Digital Pro

Este paquete está configurado con arquitectura **Serverless (FastAPI en Python) + Frontend Estático Apple Style**, listo para publicarse en Vercel.

---

## Estructura del Proyecto
```
detective_digital_vercel/
├── api/
│   ├── index.py              # Handler serverless de FastAPI
│   └── detective_core/       # Motor de inteligencia OSINT y custodia
├── public/
│   ├── index.html            # Dashboard visual interactivo (Apple Style)
│   ├── matriz_evidencias_osint.xlsx
│   └── dossier_investigacion_forense.pdf
├── requirements.txt          # Dependencias para las Serverless Functions de Vercel
├── vercel.json               # Reglas de enrutamiento y rewrites
└── README.md
```

---

## Método 1: Despliegue con un Clic vía Vercel CLI (Recomendado)

Si tienes Node.js instalado en tu equipo:

1. Abre tu terminal en la carpeta descomprimida del proyecto.
2. Ejecuta el comando de despliegue:
   ```bash
   npx vercel
   ```
3. Sigue las instrucciones interactivas:
   * **Set up and deploy?** [Y]
   * **Which scope?** [Tu cuenta de Vercel]
   * **Link to existing project?** [N]
   * **What's your project's name?** `detective-digital-osint`
   * **In which directory is your code located?** `./`
4. Para publicar a producción definitiva:
   ```bash
   npx vercel --prod
   ```

---

## Método 2: Despliegue desde GitHub (Git Integration)

1. Sube esta carpeta a un nuevo repositorio privado en GitHub (ej. `github.com/tu-usuario/detective-digital`).
2. Entra en tu panel de control de [Vercel](https://vercel.com).
3. Haz clic en **"Add New..."** → **"Project"**.
4. Selecciona tu repositorio de GitHub y haz clic en **"Import"**.
5. En **Framework Preset**, déjalo en **"Other"**.
6. Haz clic en **"Deploy"**. Vercel detectará automáticamente `requirements.txt`, compilará las funciones en `api/index.py` y servirá el frontend de `public/`.

---

## Consideraciones Críticas para Venezuela

1. **Uso de Dominio Personalizado:**
   * Los subdominios gratuitos `*.vercel.app` sufren periódicamente bloqueos de resolución DNS por parte de proveedores estatales (CANTV).
   * **Recomendación:** Asocia un dominio propio (ej. `.org`, `.io` o `.lat`) desde la pestaña **Settings → Domains** de Vercel y utiliza servidores DNS externos (como Cloudflare con DNSSEC activado).
2. **Seguridad y Confidencialidad de Datos:**
   * Dado que Vercel ejecuta funciones serverless con almacenamiento efímero (`/tmp`), los datos que se deseen preservar a largo plazo deben descargarse periódicamente en matrices Excel/PDF o conectarse a un bucket de almacenamiento seguro (ej. Supabase o S3 cifrado en reposo).
