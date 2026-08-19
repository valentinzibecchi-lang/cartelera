# Bot aviso de ofertas ALE / Materias Optativas — FCE UNICEN (Tandil)

Revisa cada 10 minutos la página de ofertas:
https://www.econ.unicen.edu.ar/alumnos/ale/ofertas-ale-y-optativas

y te manda un mail a Gmail apenas aparece una oferta nueva (materia optativa,
ALE, etc.), para que puedas anotarte en SIU Guaraní antes de que se llene el cupo.

Corre gratis en GitHub Actions, no depende de que tengas tu PC prendida.

---

## Paso 1 — Generar la contraseña de aplicación de Gmail

1. Andá a https://myaccount.google.com/security
2. Activá la verificación en 2 pasos si no la tenés activada (es obligatorio
   para poder generar contraseñas de aplicación).
3. Buscá "Contraseñas de aplicaciones" (o entrá directo a
   https://myaccount.google.com/apppasswords).
4. Creá una nueva, ponele un nombre como "cartelera-bot", y copiá el código
   de 16 letras que te da (sin espacios). **Guardalo, no lo vas a volver a ver.**

## Paso 2 — Crear el repositorio en GitHub

1. Entrá a https://github.com y creá una cuenta si no tenés.
2. Creá un repositorio nuevo (podés llamarlo `cartelera-bot`), puede ser
   **privado** (recomendado, ya que vas a guardar tu mail en secrets igual
   está protegido, pero privado es más prolijo).
3. Subí estos archivos manteniendo la misma estructura de carpetas:

```
cartelera-bot/
├── scraper.py
├── requirements.txt
├── seen_ofertas.json
├── README.md
└── .github/
    └── workflows/
        └── check-ofertas.yml
```

   La forma más fácil si no usás git desde la terminal: en la página del
   repo en GitHub, botón "Add file" → "Upload files", y arrastrás todos los
   archivos (asegurate de que `check-ofertas.yml` quede dentro de
   `.github/workflows/`, GitHub respeta las carpetas si arrastrás la
   estructura completa, o podés crear los archivos uno por uno con
   "Create new file" y escribir la ruta completa, ej:
   `.github/workflows/check-ofertas.yml`).

## Paso 3 — Configurar los Secrets

En el repo: **Settings** → **Secrets and variables** → **Actions** → pestaña
**Secrets** → **New repository secret**. Creá estos tres:

| Nombre | Valor |
|---|---|
| `GMAIL_USER` | tu dirección de Gmail (la que envía el mail) |
| `GMAIL_APP_PASSWORD` | la contraseña de 16 letras del Paso 1 |
| `GMAIL_TO` | a dónde querés que llegue el aviso (puede ser la misma que `GMAIL_USER`) |

(Opcional) En la pestaña **Variables** de esa misma sección podés agregar:

| Nombre | Valor |
|---|---|
| `KEYWORDS` | por ejemplo `Materia Optativa` si querés que te avise **solo** de materias optativas y no de ofertas ALE en general. Dejalo vacío o no lo crees si querés que te avise de todo lo nuevo. |

## Paso 4 — Activar el workflow

1. Andá a la pestaña **Actions** del repo.
2. Si GitHub te pregunta si querés habilitar los workflows, aceptá.
3. Vas a ver "Chequear cartelera ALE/Optativas" en la lista. Hacé clic,
   después **"Run workflow"** (botón a la derecha) para probarlo manualmente
   una vez y ver que funcione, en vez de esperar los 10 minutos.
4. Revisá los logs del run: te va a decir cuántas ofertas encontró.

> **Importante:** la primera vez que corre, como no tiene nada guardado
> todavía, va a tratar **todas** las ofertas actuales como "nuevas" y te va a
> mandar un mail con todo el listado actual — es normal, es el punto de
> partida. De ahí en adelante solo te va a avisar de lo que realmente sea
> nuevo.

## Paso 5 — Listo

A partir de ahí corre solo cada 10 minutos, 24/7, sin que hagas nada.
Si en algún momento querés pausarlo: **Settings** → **Actions** →
**General** → "Disable Actions".

---

## Notas técnicas

- El bot usa códigos únicos de oferta (ej. `MO237`) para no repetir avisos.
- Guarda el estado en `seen_ofertas.json`, que se actualiza solo con cada
  corrida (commit automático del propio bot).
- GitHub Actions no garantiza el minuto exacto del cron en horas de mucho
  uso (puede demorar unos minutos de más), pero para este caso de uso es
  más que suficiente.
- Si la facultad cambia el diseño de la página en el futuro, puede que el
  scraper deje de reconocer los bloques — avisame y lo ajustamos.
