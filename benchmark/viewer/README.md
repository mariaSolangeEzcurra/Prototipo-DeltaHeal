# Visor del benchmark DeltaHeal

El visor muestra los resultados ya guardados. No ejecuta el benchmark ni llama
a Gemini. Los archivos de `benchmark/results/` se leen sin modificarlos.

## Ejecutar en Windows PowerShell

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run benchmark\viewer\app.py
```

Streamlit abre la interfaz en el navegador. Si PowerShell bloquea la activación
del entorno virtual, usa la política aprobada para tu equipo o ejecuta los
comandos de instalación y arranque con el Python de `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run benchmark\viewer\app.py
```

El visor lee `results.csv`, las figuras `fig_*.png` y las hojas del libro
`evidencia_experimento.xlsx`. Si ese libro falta o no tiene una hoja, intenta
cargarla de `evidencia_petstore3.xlsx`, `evidencia_vampi.xlsx` y
`evidencia_fastapi_template.xlsx`.

La pestaña **Revisión manual** permite editar la plantilla de `Registro_manual`.
Al guardar, crea o reemplaza únicamente `benchmark/viewer/revision_humana.csv`;
no guarda cambios en los libros Excel.
