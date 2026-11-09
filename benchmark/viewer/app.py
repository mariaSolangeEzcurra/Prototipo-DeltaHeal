"""Visor de solo lectura para los resultados del benchmark DeltaHeal."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "benchmark" / "results"
REVIEW_FILE = Path(__file__).resolve().parent / "revision_humana.csv"
APIS = ["petstore3", "vampi", "fastapi_template"]
CONFIGS = ["traditional", "llm_full", "deltaheal", "delta_only", "full_heal"]
METRICS = [
    "executable_rate",
    "http_coverage",
    "total_tokens",
    "cost_usd",
    "duration_s",
]
REVIEW_HEADER_ROW = 4
MANUAL_COLUMNS = [
    "Fecha",
    "Ejecutor",
    "API",
    "Configuración",
    "Rep.",
    "Herramienta",
    "Prompt usado (texto exacto)",
    "Tests escritos/generados",
    "Tests ejecutables",
    "Pasan",
    "Fallan",
    "Códigos HTTP observados",
    "Tiempo empleado (min)",
    "Tokens (si la herramienta los muestra)",
    "Evidencia (captura / archivo)",
    "Observaciones",
    "Tasa ejecutable",
]

st.set_page_config(page_title="Benchmark DeltaHeal", layout="wide")


def show_empty(message: str) -> None:
    """Muestra un aviso consistente cuando falta un archivo o no hay datos."""
    st.info(message)


@st.cache_data(show_spinner=False)
def read_results() -> pd.DataFrame:
    """Lee el CSV principal sin escribir en la carpeta de resultados."""
    path = RESULTS_DIR / "results.csv"
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró {path}")
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def read_evidence_sheet(sheet_name: str) -> pd.DataFrame:
    """Lee una hoja del libro consolidado o combina los libros por API."""
    consolidated = RESULTS_DIR / "evidencia_experimento.xlsx"
    header = REVIEW_HEADER_ROW if sheet_name == "Registro_manual" else 0

    if consolidated.is_file():
        try:
            return pd.read_excel(
                consolidated,
                sheet_name=sheet_name,
                header=header,
                engine="openpyxl",
            )
        except ValueError:
            # Si el consolidado no contiene la hoja, intenta los libros por API.
            pass

    frames = []
    errors = []
    for api in APIS:
        path = RESULTS_DIR / f"evidencia_{api}.xlsx"
        if not path.is_file():
            errors.append(f"No se encontró {path}")
            continue
        try:
            frame = pd.read_excel(
                path,
                sheet_name=sheet_name,
                header=header,
                engine="openpyxl",
            )
            if not frame.empty:
                frames.append(frame)
        except (ValueError, OSError) as exc:
            errors.append(f"{path.name}, hoja {sheet_name}: {exc}")

    if frames:
        return pd.concat(frames, ignore_index=True)
    if errors:
        raise FileNotFoundError("; ".join(errors))
    return pd.DataFrame()


def load_optional_sheet(sheet_name: str) -> pd.DataFrame | None:
    """Carga una hoja y convierte errores de archivo en avisos visibles."""
    try:
        return read_evidence_sheet(sheet_name)
    except (FileNotFoundError, OSError, ValueError, ImportError) as exc:
        show_empty(f"No se pudo cargar la hoja **{sheet_name}**: {exc}")
        return None


def filter_evidence(
    frame: pd.DataFrame,
    api: str | None = None,
    config: str | None = None,
    rep: int | None = None,
) -> pd.DataFrame:
    """Aplica filtros solo si la hoja contiene las columnas correspondientes."""
    result = frame.copy()
    filters = [("API", api), ("Config.", config), ("Rep.", rep)]
    for column, value in filters:
        if value is not None and column in result.columns:
            result = result[result[column].astype(str) == str(value)]
    return result


def choose_filters(
    frame: pd.DataFrame,
    prefix: str,
    include_api: bool = True,
) -> tuple[str | None, str | None, int | None]:
    """Dibuja filtros usando los valores que existen en la hoja."""
    api = None
    config = None
    rep = None
    columns = st.columns(3 if include_api else 2)

    if include_api:
        apis = sorted(frame["API"].dropna().astype(str).unique()) if "API" in frame else []
        if apis:
            api = columns[0].selectbox("API", apis, key=f"{prefix}-api")
        else:
            columns[0].caption("La hoja no tiene columna API.")

    config_column = "Config." if "Config." in frame else None
    if config_column:
        configs = sorted(frame[config_column].dropna().astype(str).unique())
        if configs:
            config = columns[1 if include_api else 0].selectbox(
                "Configuración", configs, key=f"{prefix}-config"
            )
    else:
        columns[1 if include_api else 0].caption("La hoja no tiene columna Config.")

    if "Rep." in frame:
        reps = sorted(
            frame["Rep."].dropna().astype(str).unique(),
            key=lambda value: int(value) if value.isdigit() else value,
        )
        if reps:
            rep_value = columns[2 if include_api else 1].selectbox(
                "Repetición", reps, key=f"{prefix}-rep"
            )
            rep = int(rep_value) if rep_value.isdigit() else None
    return api, config, rep


def display_sheet(sheet_name: str, prefix: str) -> pd.DataFrame | None:
    """Carga una hoja, agrega filtros y muestra sus filas."""
    frame = load_optional_sheet(sheet_name)
    if frame is None:
        return None
    if frame.empty:
        show_empty(f"La hoja **{sheet_name}** está vacía.")
        return frame

    api, config, rep = choose_filters(frame, prefix)
    filtered = filter_evidence(frame, api, config, rep)
    if filtered.empty:
        show_empty("No hay filas para los filtros seleccionados.")
    else:
        st.dataframe(filtered, width="stretch", hide_index=True)
    return filtered


def render_summary() -> None:
    """Presenta corridas filtrables, promedios y figuras generadas."""
    st.header("Resumen")
    try:
        results = read_results()
    except (FileNotFoundError, OSError, ImportError) as exc:
        show_empty(f"No se pudo cargar results.csv: {exc}")
        return

    filtered = results.copy()
    filters = st.columns(3)
    for column, label in zip(("api", "config", "rep"), ("API", "Configuración", "Repetición")):
        values = sorted(filtered[column].dropna().unique())
        selected = filters[("api", "config", "rep").index(column)].multiselect(
            label, values, default=values, key=f"results-{column}"
        )
        filtered = filtered[filtered[column].isin(selected)]

    st.subheader("Corridas")
    st.dataframe(filtered, width="stretch", hide_index=True)

    st.subheader("Métricas medias por configuración")
    if filtered.empty:
        show_empty("No hay corridas para los filtros seleccionados.")
    else:
        numeric = filtered.copy()
        for metric in METRICS:
            numeric[metric] = pd.to_numeric(numeric[metric], errors="coerce")
        st.dataframe(
            numeric.groupby("config", as_index=False)[METRICS].mean(),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Figuras")
    available = [
        RESULTS_DIR / f"fig_{metric}.png"
        for metric in METRICS
        if (RESULTS_DIR / f"fig_{metric}.png").is_file()
    ]
    if not available:
        show_empty("No se encontraron figuras fig_*.png en benchmark/results.")
    for path in available:
        st.image(str(path), caption=path.stem, width="stretch")


def render_generated_tests() -> None:
    """Permite filtrar casos y ver código Python con formato."""
    st.header("Casos de prueba generados")
    cases = load_optional_sheet("Casos_de_prueba")
    code = load_optional_sheet("Codigo_generado")
    if cases is None or code is None:
        return

    if cases.empty:
        show_empty("La hoja **Casos_de_prueba** está vacía.")
    else:
        api, config, rep = choose_filters(cases, "cases")
        filtered = filter_evidence(cases, api, config, rep)
        search = st.text_input("Buscar en casos (test, resultado o mensaje)")
        if search:
            text = filtered.fillna("").astype(str).agg(" ".join, axis=1)
            filtered = filtered[text.str.contains(search, case=False, regex=False)]
        if filtered.empty:
            show_empty("No se encontraron casos con esos filtros.")
        else:
            st.dataframe(filtered, width="stretch", hide_index=True)

    st.subheader("Código generado")
    if code.empty:
        show_empty("La hoja **Codigo_generado** está vacía.")
        return
    api, config, rep = choose_filters(code, "code")
    filtered_code = filter_evidence(code, api, config, rep)
    if filtered_code.empty:
        show_empty("No hay código para los filtros seleccionados.")
        return
    code_column = "Código"
    if code_column not in filtered_code.columns:
        show_empty(f"No se encontró la columna **{code_column}** en Codigo_generado.")
        return

    labels = []
    for index, row in filtered_code.iterrows():
        file_name = row.get("Archivo", f"Código {index + 1}")
        origin = row.get("Origen del código", "")
        labels.append(f"{file_name} — {origin}")
    selected_index = st.selectbox(
        "Archivo de código",
        filtered_code.index.tolist(),
        format_func=lambda index: labels[filtered_code.index.get_loc(index)],
        key="generated-code-file",
    )
    selected_code = filtered_code.loc[selected_index, code_column]
    if pd.isna(selected_code) or not str(selected_code).strip():
        show_empty("La fila seleccionada no contiene código.")
    else:
        st.code(str(selected_code), language="python", line_numbers=True)


def render_llm() -> None:
    """Muestra el registro de llamadas y permite consultar prompts y respuestas."""
    st.header("Prompts y llamadas al LLM")
    st.info(
        "Las corridas traditional no usan Gemini, por lo que no tienen filas "
        "en Prompts ni Llamadas_LLM. Los campos LLM vacíos en esos casos son normales."
    )
    calls = load_optional_sheet("Llamadas_LLM")
    prompts = load_optional_sheet("Prompts")
    if calls is not None:
        if calls.empty:
            show_empty("La hoja **Llamadas_LLM** está vacía. Es normal para traditional.")
        else:
            api, config, rep = choose_filters(calls, "calls")
            filtered_calls = filter_evidence(calls, api, config, rep)
            cols = [
                column
                for column in (
                    "API",
                    "Config.",
                    "Rep.",
                    "N° llamada",
                    "Fase",
                    "Tokens entrada",
                    "Tokens salida",
                    "Tokens razonamiento",
                    "Latencia (s)",
                    "Costo equiv. (USD)",
                    "¿Cortada?",
                )
                if column in filtered_calls.columns
            ]
            st.dataframe(
                filtered_calls[cols],
                width="stretch",
                hide_index=True,
            )

    if prompts is not None:
        st.subheader("Prompts y respuestas")
        if prompts.empty:
            show_empty("La hoja **Prompts** está vacía. Es normal para traditional.")
            return
        api, config, rep = choose_filters(prompts, "prompts")
        filtered_prompts = filter_evidence(prompts, api, config, rep)
        if filtered_prompts.empty:
            show_empty("No hay prompts para los filtros seleccionados.")
            return
        for index, row in filtered_prompts.iterrows():
            title = (
                f"{row.get('API', '')} · {row.get('Config.', '')} · "
                f"rep {row.get('Rep.', '')} · llamada {row.get('N° llamada', '')} "
                f"({row.get('Fase', '')})"
            )
            with st.expander(title):
                st.text_area(
                    "Prompt enviado",
                    str(row.get("Prompt enviado (texto exacto)", "")),
                    height=220,
                    key=f"prompt-{index}",
                )
                st.text_area(
                    "Respuesta recibida",
                    str(row.get("Respuesta recibida (texto exacto)", "")),
                    height=220,
                    key=f"response-{index}",
                )


def render_manual_review() -> None:
    """Edita la plantilla manual solo en un CSV nuevo del visor."""
    st.header("Casos humanos / revisión manual")
    manual = load_optional_sheet("Registro_manual")
    if manual is None:
        return

    if REVIEW_FILE.is_file():
        try:
            manual = pd.read_csv(REVIEW_FILE).reindex(columns=MANUAL_COLUMNS)
            st.caption(f"Editando la copia local: {REVIEW_FILE}")
        except (OSError, pd.errors.ParserError) as exc:
            show_empty(f"No se pudo leer la revisión local: {exc}")
            return
    else:
        if manual.empty or (
            "Fecha" in manual.columns
            and manual["Fecha"].fillna("").astype(str).str.strip().eq("").all()
        ):
            st.caption("El Excel solo aporta una plantilla vacía; no tiene casos manuales.")
            manual = pd.DataFrame(columns=MANUAL_COLUMNS)
        else:
            st.dataframe(manual, width="stretch", hide_index=True)
            st.caption("La edición se guarda aparte; el Excel original no se modifica.")

    edited = st.data_editor(
        manual,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="manual-review-editor",
    )
    if st.button("Guardar revisión en CSV nuevo", type="primary"):
        try:
            edited.to_csv(REVIEW_FILE, index=False, encoding="utf-8-sig")
            st.success(f"Revisión guardada en {REVIEW_FILE}")
        except OSError as exc:
            st.error(f"No se pudo guardar la revisión: {exc}")


def render_comparison() -> None:
    """Compara casos y código de tres configuraciones para una corrida."""
    st.header("Comparar configuraciones")
    cases = load_optional_sheet("Casos_de_prueba")
    code = load_optional_sheet("Codigo_generado")
    if cases is None or code is None:
        return

    apis = sorted(cases["API"].dropna().astype(str).unique()) if "API" in cases else []
    if not apis:
        show_empty("No hay APIs en la hoja Casos_de_prueba.")
        return
    api = st.selectbox("API", apis, key="compare-api")
    api_cases = filter_evidence(cases, api=api)
    reps = sorted(
        api_cases["Rep."].dropna().astype(str).unique(),
        key=lambda value: int(value) if value.isdigit() else value,
    )
    if not reps:
        show_empty("No hay repeticiones para esta API.")
        return
    rep_value = st.selectbox("Repetición", reps, key="compare-rep")
    rep = int(rep_value) if rep_value.isdigit() else None
    columns = st.columns(3)

    for column, config in zip(columns, ("traditional", "llm_full", "deltaheal")):
        with column:
            st.subheader(config)
            selected_cases = filter_evidence(api_cases, config=config, rep=rep)
            if selected_cases.empty:
                show_empty("No hay casos para esta corrida.")
            else:
                st.dataframe(selected_cases, width="stretch", hide_index=True)

            selected_code = filter_evidence(code, api=api, config=config, rep=rep)
            if selected_code.empty:
                show_empty("No hay código registrado.")
            elif "Código" in selected_code:
                value = selected_code.iloc[0]["Código"]
                if pd.isna(value) or not str(value).strip():
                    show_empty("El código está vacío.")
                else:
                    st.code(str(value), language="python", line_numbers=True)


def render_traffic_coverage() -> None:
    """Filtra y muestra solicitudes HTTP y pares de cobertura."""
    st.header("Tráfico HTTP y cobertura")
    st.subheader("Tráfico HTTP")
    display_sheet("Trafico_HTTP", "traffic")
    st.subheader("Cobertura")
    display_sheet("Cobertura", "coverage")


st.title("Benchmark DeltaHeal")
st.caption(
    "Visor de solo lectura de benchmark/results. No ejecuta corridas ni llama al LLM."
)

tabs = st.tabs(
    [
        "Resumen",
        "Casos y código",
        "Prompts y LLM",
        "Revisión manual",
        "Comparar configs",
        "Tráfico y cobertura",
    ]
)
with tabs[0]:
    render_summary()
with tabs[1]:
    render_generated_tests()
with tabs[2]:
    render_llm()
with tabs[3]:
    render_manual_review()
with tabs[4]:
    render_comparison()
with tabs[5]:
    render_traffic_coverage()
