from datetime import datetime, time
import ast
import base64
import csv
from io import BytesIO
import os
import re
from pathlib import Path

import django
import pandas as pd
import streamlit as st
from django.apps import apps as django_apps
from django.db.models import Q

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
if not django_apps.ready:
    django.setup()

from core.db_utils import save_streamlit_entry, update_production_entry
from core.excel_utils import (
    get_acabados_for_cliente,
    get_process_choices_for_acabado_e_ferramental,
    get_unique_choices,
    get_operadores,
)
from core.models import ProductionEntry


st.set_page_config(
    page_title="Registro de Producao",
    page_icon="RP",
    layout="centered",
)


@st.cache_data
def load_base_choices():
    """Carrega as listas base da planilha (cacheadas para evitar reprocessar)."""
    return {
        "clientes": [value for value, _ in get_unique_choices("CLIENTE") if value],
        "acabados": [value for value, _ in get_unique_choices("ACABADO") if value],
        "ferramentais": [value for value, _ in get_unique_choices("FERRAMENTAL") if value],
    }


def options_from_choices(choices):
    """Converte a lista de choices (value, label) para apenas os values, descartando vazios."""
    return [value for value, _ in choices if value]


choices = load_base_choices()
operadores = get_operadores()
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR = Path(os.environ.get("REGISTROS_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass
OUTPUT_FILE = Path(
    os.environ.get("REGISTROS_OUTPUT_FILE", str(OUTPUT_DIR / "registros.csv"))
)
DEFAULT_FALLBACK_DIR = Path.home() / "mtech_registros"
FALLBACK_DIR = Path(
    os.environ.get("REGISTROS_FALLBACK_DIR", str(DEFAULT_FALLBACK_DIR))
)
FALLBACK_FILE = Path(
    os.environ.get("REGISTROS_FALLBACK_FILE", str(FALLBACK_DIR / "registros.csv"))
)
SCHEMA_VERSION = "1.2"
PROCESSO_OUTRO = "__PROCESSO_OUTRO__"
BG_IMAGE_PATH = Path(__file__).resolve().parent / "assets" / "background.png"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"
CSV_FIELDS = [
    "ID",
    "Timestamp",
    "Cliente",
    "Display",
    "Numero Display",
    "Maquinário",
    "Processo",
    "Data",
    "Operadores",
    "Numero Operadores",
    "Hora Início",
    "Hora Fim",
    "Quantidade",
    "Peças Mortas",
    "Quantidade Total",
]


@st.cache_resource
def load_image_base64(image_path: Path) -> str | None:
    """Retorna a imagem em base64 ou None se nao existir."""
    if not image_path.exists():
        return None
    return base64.b64encode(image_path.read_bytes()).decode()


def set_background(image_path: Path) -> None:
    """Aplica imagem de fundo (se existir) e gradient com bom contraste."""
    encoded = load_image_base64(image_path)
    bg_image_layer = f'url("data:image/png;base64,{encoded}") center/cover fixed no-repeat,' if encoded else ""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap');

        .stApp {{
            background: {bg_image_layer} linear-gradient(135deg, rgba(0,0,0,0.05), rgba(0,0,0,0.15));
            color: #0c1b1f;
            font-family: 'Manrope', 'Segoe UI', sans-serif;
        }}

        .block-container {{
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 980px;
        }}

        .app-hero {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            background: rgba(255, 255, 255, 0.82);
            border-radius: 14px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            border: 1px solid rgba(255,255,255,0.6);
            backdrop-filter: blur(4px);
        }}

        .app-hero img {{
            height: 70px;
            width: auto;
        }}

        .logo-fallback {{
            height: 70px;
            width: 70px;
            border-radius: 14px;
            background: linear-gradient(135deg, #0b4453, #0a7b8c);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            letter-spacing: 0.06em;
        }}

        .hero-text h1 {{
            font-size: 1.8rem;
            margin: 0;
            color: #0a4a52;
            letter-spacing: 0.02em;
        }}

        .hero-text p {{
            margin: 2px 0 0;
            color: #0f282f;
            font-weight: 600;
        }}

        .form-card {{
            background: rgba(255,255,255,0.9);
            border-radius: 14px;
            padding: 1.25rem 1.25rem 1rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            border: 1px solid rgba(10,68,83,0.12);
            backdrop-filter: blur(4px);
            color: #0a2a33;
        }}

        .form-card + .form-card {{
            margin-top: 1rem;
        }}

        .section-title {{
            font-weight: 700;
            color: #0c4a53;
            margin-bottom: 0.35rem;
        }}

        .stButton button {{
            background: linear-gradient(135deg, #0b4453, #0a7b8c);
            color: #fff;
            border: 1px solid #08333f;
            border-radius: 10px;
            padding: 0.65rem 1.05rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            box-shadow: 0 10px 22px rgba(10, 68, 83, 0.35);
        }}

        .stButton button:hover {{
            filter: brightness(1.05);
            transform: translateY(-1px);
        }}

        .stSelectbox > div, .stMultiSelect > div, .stNumberInput > div, .stDateInput > div, .stTimeInput > div {{
            border-radius: 10px;
            border: 1px solid rgba(10, 68, 83, 0.3);
        }}

        .metric-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(14,165,165,0.1);
            color: #0c4a53;
            padding: 6px 10px;
            border-radius: 999px;
            font-weight: 700;
        }}

        /* Keep full labels visible in multiselect tags (no ellipsis cut). */
        [data-baseweb="select"] [data-baseweb="tag"] {{
            max-width: 100% !important;
            height: auto !important;
            overflow: visible !important;
        }}

        [data-baseweb="select"] [data-baseweb="tag"] > span:first-child {{
            max-width: none !important;
            overflow: visible !important;
            text-overflow: clip !important;
            white-space: normal !important;
            line-height: 1.2 !important;
            word-break: break-word !important;
        }}

        section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
            height: auto !important;
            min-height: 42px !important;
            align-items: flex-start !important;
            padding-top: 4px !important;
            padding-bottom: 4px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


set_background(BG_IMAGE_PATH)


def normalize_operadores(value) -> str:
    """Serializa operadores para string amigavel ao CSV."""
    if isinstance(value, list):
        return "; ".join(str(v).strip() for v in value if str(v).strip())
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, list):
                    return "; ".join(str(v).strip() for v in parsed if str(v).strip())
            except Exception:
                pass
        return text
    return str(value)


def normalize_text(value) -> str:
    """Normaliza texto para exibicao consistente em widgets."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return re.sub(r"\s+", " ", text)


def unique_preserve_order(values):
    """Remove duplicados mantendo a ordem original."""
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def count_operadores_from_cell(value) -> str:
    """Conta operadores a partir do campo de texto."""
    normalized = normalize_operadores(value)
    if not normalized:
        return ""
    parts = [p.strip() for p in re.split(r"[;|,]", normalized) if p.strip()]
    return str(len(parts)) if parts else ""


def ensure_output_schema_for(output_file: Path) -> None:
    """Garante que o CSV tenha o schema atual, migrando se necessario."""
    if not output_file.exists():
        return

    with output_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            existing_fields = next(reader)
        except StopIteration:
            return

    existing_fields = [field.strip().lstrip("\ufeff") for field in existing_fields]
    if existing_fields == CSV_FIELDS:
        return

    backup_path = output_file.with_name(
        f"{output_file.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{output_file.suffix}"
    )
    output_file.replace(backup_path)

    with backup_path.open("r", encoding="utf-8", newline="") as f_in, output_file.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for row in reader:
            new_row = {field: row.get(field, "") for field in CSV_FIELDS}
            if not new_row.get("Numero Operadores"):
                new_row["Numero Operadores"] = count_operadores_from_cell(row.get("Operadores", ""))
            writer.writerow(new_row)


def append_csv_row(output_file: Path, payload_to_save: dict, is_new: bool) -> None:
    """Append ao CSV com schema esperado."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(payload_to_save)


def build_save_error_message(*args) -> str:
    """Mensagem amigavel para falhas de escrita."""
    err = args[-1] if args else Exception("Falha desconhecida")
    return (
        "Nao foi possivel salvar o registro no banco SQLite. "
        f"Detalhe tecnico: {err}"
    )


def render_header():
    """Exibe o logo e a headline do app."""
    logo_b64 = load_image_base64(LOGO_PATH)

    logo_img = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="MTECH Displays logo" />'
        if logo_b64
        else '<div class="logo-fallback" aria-label="Logo MTECH">MTECH</div>'
    )
    st.markdown(
        f"""
        <div class="app-hero">
            {logo_img}
            <div class="hero-text">
                <h1>Controle de Producao - MTECH</h1>
                <p>Displays com tecnologia</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def salvar_registro_csv_legacy(payload: dict):
    """
    Salva o payload em CSV (append) no formato padronizado.
    Formato: ID, Timestamp, Cliente, Display, Maquinário, Processo, Data, 
    Operadores, Hora Início, Hora Fim, Quantidade, Peças Mortas, Quantidade Total
    """
    # Formato padronizado do CSV
    payload_to_save = {
        "ID": SCHEMA_VERSION,
        "Timestamp": datetime.now().isoformat(),
        "Cliente": payload.get("cliente", ""),
        "Display": payload.get("acabado", ""),
        "Numero Display": payload.get("numero_display", ""),
        "Maquinário": payload.get("ferramental", ""),
        "Processo": payload.get("processo", ""),
        "Data": payload.get("data_producao", ""),
        "Operadores": normalize_operadores(payload.get("operadores", [])),
        "Numero Operadores": payload.get("numero_operadores", ""),
        "Hora Início": payload.get("hora_iniciada", ""),
        "Hora Fim": payload.get("hora_finalizada", ""),
        "Quantidade": payload.get("quantidade_produzida", 0),
        "Peças Mortas": payload.get("pecas_mortas", 0),
        "Quantidade Total": payload.get("quantidade_total", 0),
    }

    primary_path = OUTPUT_FILE
    targets = [primary_path]
    if FALLBACK_FILE != primary_path:
        targets.append(FALLBACK_FILE)

    primary_error = None
    for target_path in targets:
        try:
            ensure_output_schema_for(target_path)
            is_new = not target_path.exists()
            append_csv_row(target_path, payload_to_save, is_new)
            used_fallback = target_path != primary_path
            return target_path, used_fallback, None
        except PermissionError as exc:
            primary_error = exc
            if target_path == primary_path:
                continue
            return None, False, build_save_error_message(primary_path, exc)
        except OSError as exc:
            primary_error = exc
            if target_path == primary_path:
                continue
            return None, False, build_save_error_message(primary_path, exc)

    if primary_error:
        return None, False, build_save_error_message(primary_path, primary_error)
    return None, False, "Nao foi possivel salvar o registro."


def salvar_registro(payload: dict):
    """Salva o payload no SQLite via Django ORM."""
    payload_to_save = dict(payload)
    payload_to_save["operadores"] = normalize_operadores(payload.get("operadores", []))

    try:
        entry = save_streamlit_entry(payload_to_save, schema_version=SCHEMA_VERSION)
        return entry, None
    except Exception as exc:
        return None, build_save_error_message(exc)


render_header()

# Guardamos o ferramental anterior para resetar o processo quando trocar
if "last_ferramental" not in st.session_state:
    st.session_state.last_ferramental = None
if "last_cliente" not in st.session_state:
    st.session_state.last_cliente = None
if "last_acabado" not in st.session_state:
    st.session_state.last_acabado = None
if "operadores_selecionados" not in st.session_state:
    st.session_state.operadores_selecionados = []
if "operadores_multiselect" not in st.session_state:
    st.session_state.operadores_multiselect = list(st.session_state.operadores_selecionados)


def reset_form_state():
    """Limpa todos os campos do formulario."""
    st.session_state.clear()


def reset_form_fields():
    """Limpa campos do formulario sem limpar caches."""
    keys_to_clear = [
        "cliente",
        "acabado",
        "ferramental",
        "processo",
        "processo_custom",
        "numero_display",
        "data_producao",
        "hora_iniciada",
        "hora_finalizada",
        "quantidade_produzida",
        "pecas_mortas",
        "quantidade_total",
        "numero_operadores",
        "operadores_selecionados",
        "operadores_multiselect",
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)
    st.session_state.last_ferramental = None
    st.session_state.last_cliente = None
    st.session_state.last_acabado = None
    st.session_state.operadores_selecionados = []


def validate_inputs(
    cliente,
    acabado,
    numero_display,
    ferramental,
    processo,
    data_producao,
    hora_iniciada,
    hora_finalizada,
    quantidade_produzida,
    quantidade_total,
    numero_operadores,
    operadores_selecionados,
):
    """Retorna lista de mensagens de erro encontradas na validacao."""
    erros = []

    obrigatorios = [
        (cliente, "Cliente"),
        (acabado, "Display (Acabado)"),
        (numero_display, "Codigo do lote"),
        (ferramental, "Ferramental / Maquina"),
        (processo, "Processo"),
        (data_producao, "Data da producao"),
    ]
    for valor, label in obrigatorios:
        if not valor:
            erros.append(f"{label} e obrigatorio.")

    if numero_operadores < 1:
        erros.append("Numero de operadores deve ser maior ou igual a 1.")

    if numero_display and not re.fullmatch(r"\d{8}", str(numero_display).strip()):
        erros.append("Codigo do lote deve ter exatamente 8 digitos.")

    if not operadores_selecionados:
        erros.append("Selecione ao menos um operador.")
    elif len(operadores_selecionados) != numero_operadores:
        erros.append("A quantidade de operadores selecionados deve coincidir com o numero informado.")

    if hora_iniciada and hora_finalizada and hora_finalizada < hora_iniciada:
        erros.append("Hora finalizada deve ser maior ou igual a hora iniciada.")

    if quantidade_total < quantidade_produzida:
        erros.append("Quantidade total deve ser maior ou igual a quantidade produzida.")

    return erros


def render_lancamento_screen():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    cliente = st.selectbox(
        "Cliente",
        choices["clientes"],
        index=None,
        placeholder="Selecione",
        key="cliente",
        help="Selecione o cliente do pedido.",
    )
    if st.session_state.last_cliente != cliente:
        st.session_state.pop("acabado", None)
        st.session_state.pop("processo", None)
        st.session_state.pop("processo_custom", None)
    st.session_state.last_cliente = cliente

    acabado_options = (
        options_from_choices(get_acabados_for_cliente(cliente))
        if cliente
        else choices["acabados"]
    )

    acabado = st.selectbox(
        "Display (Acabado)",
        acabado_options,
        index=None,
        placeholder="Selecione",
        key="acabado",
        help="Escolha o display/acabado para producao.",
    )
    numero_display = st.text_input(
        "Codigo do lote",
        key="numero_display",
        max_chars=8,
        placeholder="Digite 8 digitos",
        help="Informe o codigo do lote com 8 digitos.",
    )
    ferramental = st.selectbox(
        "Ferramental / Maquina",
        choices["ferramentais"],
        index=None,
        placeholder="Selecione",
        key="ferramental",
        help="Ferramental ou maquina utilizada.",
    )

    processo_options = options_from_choices(
        get_process_choices_for_acabado_e_ferramental(acabado, ferramental)
    )

    # se mudar o ferramental ou o acabado, limpa a selecao anterior de processo
    if st.session_state.last_ferramental != ferramental:
        st.session_state.pop("processo", None)
        st.session_state.pop("processo_custom", None)
    st.session_state.last_ferramental = ferramental

    if st.session_state.last_acabado != acabado:
        st.session_state.pop("processo", None)
        st.session_state.pop("processo_custom", None)
    st.session_state.last_acabado = acabado

    processo_options_with_outro = processo_options + [PROCESSO_OUTRO]

    processo = st.selectbox(
        "Processo",
        processo_options_with_outro,
        index=None,
        placeholder="Selecione",
        key="processo",
        format_func=lambda opt: "Outro (digitar)" if opt == PROCESSO_OUTRO else opt,
        help="Etapa/processo que sera executado.",
    )
    processo_custom = ""
    if processo == PROCESSO_OUTRO:
        processo_custom = st.text_input(
            "Nome do processo (novo)",
            key="processo_custom",
            placeholder="Digite o processo",
            help="Informe um processo que nao aparece na lista.",
        )
    processo_selecionado = processo_custom.strip() if processo == PROCESSO_OUTRO else processo

    data_producao = st.date_input(
        "Data da producao",
        value=datetime.today().date(),
        # Streamlit exige ano com 4 digitos na exibicao; o CSV continua com 2 digitos.
        format="DD/MM/YYYY",
        key="data_producao",
        help="Data em que a producao ocorreu.",
    )

    hora_iniciada = st.time_input("Hora iniciada", value=time(0, 0), key="hora_iniciada", help="Horario de inicio do processo.")
    hora_finalizada = st.time_input("Hora finalizada", value=time(0, 0), key="hora_finalizada", help="Horario de termino do processo.")
    quantidade_produzida = st.number_input("Quantidade produzida", min_value=0, step=1, key="quantidade_produzida", help="Quantidade concluida neste registro.")
    pecas_mortas = st.number_input("Peças mortas", min_value=0, step=1, key="pecas_mortas", help="Quantidade de peças descartadas ou com defeito.")
    quantidade_total = st.number_input("Quantidade total", min_value=0, step=1, key="quantidade_total", help="Quantidade total prevista para a ordem.")
    numero_operadores = st.number_input("Numero de operadores", min_value=1, step=1, key="numero_operadores", help="Total de operadores alocados.")

    # Normaliza lista base e selecao atual para evitar valores invisiveis/invalidos
    operadores_base = unique_preserve_order(
        [name for name in (normalize_text(o) for o in operadores) if name]
    )

    selecionados_raw = st.session_state.get(
        "operadores_multiselect", st.session_state.get("operadores_selecionados", [])
    )
    if not isinstance(selecionados_raw, list):
        selecionados_raw = [selecionados_raw]
    selecionados_norm = unique_preserve_order(
        [name for name in (normalize_text(o) for o in selecionados_raw) if name]
    )

    # Limita a selecao ao total informado
    if len(selecionados_norm) > numero_operadores:
        selecionados_norm = selecionados_norm[:numero_operadores]

    # Mantem disponiveis os ja selecionados mesmo se o filtro nao os contiver
    opcoes_multiselect = unique_preserve_order(operadores_base + selecionados_norm)
    st.session_state.operadores_multiselect = selecionados_norm

    col1, col2 = st.columns(2)
    with col2:
        if st.button("Limpar operadores selecionados", key="limpar_operadores_btn"):
            st.session_state.operadores_selecionados = []
            st.session_state.operadores_multiselect = []
            st.rerun()

    operadores_selecionados = st.multiselect(
        f"Operadores (selecionados: {len(st.session_state.operadores_multiselect)}/{numero_operadores})",
        opcoes_multiselect,
        key="operadores_multiselect",
        placeholder="Selecione",
        max_selections=numero_operadores,
        disabled=numero_operadores < 1,
        help="Selecione os operadores responsaveis, limitado ao numero informado.",
    )
    st.session_state.operadores_selecionados = operadores_selecionados

    with col1:
        st.caption(f"Selecionados: {len(operadores_selecionados)}/{numero_operadores}")

    submitted = st.button("Salvar")

    if submitted:
        erros = validate_inputs(
            cliente,
            acabado,
            numero_display,
            ferramental,
            processo_selecionado,
            data_producao,
            hora_iniciada,
            hora_finalizada,
            quantidade_produzida,
            quantidade_total,
            numero_operadores,
            operadores_selecionados,
        )

        if erros:
            st.error("Corrija os itens antes de salvar:\n- " + "\n- ".join(erros), icon="⚠️")
        else:
            registro = {
                "cliente": cliente,
                "acabado": acabado,
                "numero_display": str(numero_display).strip() if numero_display else "",
                "ferramental": ferramental,
                "processo": processo_selecionado,
                "data_producao": data_producao.strftime("%d/%m/%y") if data_producao else None,
                "operadores": operadores_selecionados,
                "hora_iniciada": hora_iniciada.strftime("%H:%M") if hora_iniciada else None,
                "hora_finalizada": hora_finalizada.strftime("%H:%M") if hora_finalizada else None,
                "quantidade_produzida": quantidade_produzida,
                "pecas_mortas": pecas_mortas,
                "numero_operadores": numero_operadores,
                "quantidade_total": quantidade_total,
            }
            saved_entry, error_message = salvar_registro(registro)
            if saved_entry:
                st.session_state["ultimo_registro"] = registro
                st.session_state["form_salvo"] = True
                st.success(f"Registro salvo no banco SQLite. ID #{saved_entry.id}")
            else:
                st.session_state["form_salvo"] = False
                st.error(error_message or "Nao foi possivel salvar o registro.")

    if st.session_state.get("form_salvo") and st.session_state.get("ultimo_registro"):
        reg = st.session_state["ultimo_registro"]
        st.markdown(
            f"""
            <div class="form-card">
                <div class="section-title">Resumo salvo</div>
                <ul>
                    <li><strong>Cliente:</strong> {reg.get("cliente")}</li>
                    <li><strong>Acabado:</strong> {reg.get("acabado")}</li>
                    <li><strong>Codigo do Lote:</strong> {reg.get("numero_display")}</li>
                    <li><strong>Ferramental:</strong> {reg.get("ferramental")}</li>
                    <li><strong>Processo:</strong> {reg.get("processo")}</li>
                    <li><strong>Data:</strong> {reg.get("data_producao")}</li>
                    <li><strong>Quantidade:</strong> {reg.get("quantidade_produzida")} / {reg.get("quantidade_total")}</li>
                    <li><strong>Peças Mortas:</strong> {reg.get("pecas_mortas", 0)}</li>
                    <li><strong>Operadores ({len(reg.get("operadores") or [])}):</strong> {", ".join(reg.get("operadores") or [])}</li>
                    <li><strong>Horário:</strong> {reg.get("hora_iniciada")} - {reg.get("hora_finalizada")}</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Novo registro", key="novo_registro_btn"):
            reset_form_fields()
            st.session_state.pop("form_salvo", None)
            st.session_state.pop("ultimo_registro", None)
            st.rerun()

    # Botao unico para recarregar a pagina e limpar tudo
    if st.button("Recarregar pagina", key="recarregar_btn"):
        reset_form_state()
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def parse_data_producao_edit(value):
    text = normalize_text(value)
    if not text:
        return None
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_hora_edit(value):
    text = normalize_text(value)
    if not text:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def split_operadores_edit(value):
    normalized = normalize_operadores(value)
    if not normalized:
        return []
    return unique_preserve_order(
        [part.strip() for part in re.split(r"[;|,]", normalized) if part.strip()]
    )


def validate_edit_form(
    numero_display,
    data_producao_text,
    hora_inicio_text,
    hora_fim_text,
    quantidade,
    quantidade_total,
    numero_operadores,
    operadores_text,
):
    errors = []
    data_producao = parse_data_producao_edit(data_producao_text) if data_producao_text else None
    hora_inicio = parse_hora_edit(hora_inicio_text) if hora_inicio_text else None
    hora_fim = parse_hora_edit(hora_fim_text) if hora_fim_text else None
    operadores_lista = split_operadores_edit(operadores_text)

    if numero_display and not re.fullmatch(r"\d{8}", numero_display.strip()):
        errors.append("Codigo do lote deve ter exatamente 8 digitos.")
    if data_producao_text and data_producao is None:
        errors.append("Data da producao deve estar no formato DD/MM/AA ou DD/MM/AAAA.")
    if hora_inicio_text and hora_inicio is None:
        errors.append("Hora iniciada deve estar no formato HH:MM.")
    if hora_fim_text and hora_fim is None:
        errors.append("Hora finalizada deve estar no formato HH:MM.")
    if hora_inicio and hora_fim and hora_fim < hora_inicio:
        errors.append("Hora finalizada deve ser maior ou igual a hora iniciada.")
    if quantidade_total < quantidade:
        errors.append("Quantidade total deve ser maior ou igual a quantidade produzida.")
    if numero_operadores < 0:
        errors.append("Numero de operadores nao pode ser negativo.")
    if operadores_lista and numero_operadores and len(operadores_lista) != numero_operadores:
        errors.append("A quantidade de operadores digitados deve coincidir com o numero informado.")

    return errors, data_producao, hora_inicio, hora_fim, operadores_lista


def format_timestamp_edit(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")


def build_management_dataframe(entries):
    return pd.DataFrame(
        [
            {
                "ID": entry.id,
                "Lancado em": format_timestamp_edit(entry.timestamp),
                "Cliente": entry.cliente,
                "Display": entry.display,
                "Lote": entry.numero_display,
                "Maquina": entry.maquinario,
                "Processo": entry.processo,
                "Data producao": entry.data_producao,
                "Quantidade": entry.quantidade,
                "Perdas": entry.pecas_mortas,
                "Operadores": entry.operadores,
            }
            for entry in entries
        ]
    )


def build_export_csv_bytes(export_df: pd.DataFrame) -> bytes:
    return export_df.to_csv(index=False).encode("utf-8-sig")


def build_export_excel_bytes(export_df: pd.DataFrame) -> bytes:
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="registros")
    return excel_buffer.getvalue()


@st.fragment
def render_export_buttons(export_df: pd.DataFrame, export_stamp: str) -> None:
    csv_data = build_export_csv_bytes(export_df)
    excel_data = build_export_excel_bytes(export_df)

    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.download_button(
            "Exportar CSV filtrado",
            data=csv_data,
            file_name=f"registros_filtrados_{export_stamp}.csv",
            mime="text/csv",
            key="mgmt_export_csv",
            on_click="ignore",
            use_container_width=True,
        )
    with export_col2:
        st.download_button(
            "Exportar Excel filtrado",
            data=excel_data,
            file_name=f"registros_filtrados_{export_stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mgmt_export_excel",
            on_click="ignore",
            use_container_width=True,
        )


def load_entries_for_management(busca, cliente, display, lote, data_inicio, data_fim, page_size, page_number):
    queryset = ProductionEntry.objects.all().order_by("-timestamp", "-id")
    if busca:
        queryset = queryset.filter(
            Q(cliente__icontains=busca)
            | Q(display__icontains=busca)
            | Q(numero_display__icontains=busca)
            | Q(maquinario__icontains=busca)
            | Q(processo__icontains=busca)
            | Q(operadores__icontains=busca)
        )
    if cliente:
        queryset = queryset.filter(cliente__icontains=cliente)
    if display:
        queryset = queryset.filter(display__icontains=display)
    if lote:
        queryset = queryset.filter(numero_display__icontains=lote)
    if data_inicio:
        queryset = queryset.filter(timestamp__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(timestamp__date__lte=data_fim)

    total = queryset.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(max(page_number, 1), total_pages)
    offset = (current_page - 1) * page_size
    entries = list(queryset[offset : offset + page_size])
    filtered_entries = list(queryset)
    return entries, filtered_entries, total, total_pages, current_page


def format_entry_label(entry):
    return (
        f"#{entry.id} | {entry.cliente} | {entry.display} | "
        f"{entry.processo} | {entry.data_producao or 'sem data'}"
    )


def render_management_screen():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Consulta e Edicao</div>', unsafe_allow_html=True)
    st.caption("Use esta area para localizar, corrigir, paginar e exportar registros.")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        busca = st.text_input(
            "Busca geral",
            key="mgmt_busca",
            placeholder="Cliente, display, processo, operador...",
        )
    with col2:
        filtro_cliente = st.text_input("Cliente", key="mgmt_cliente")
    with col3:
        filtro_display = st.text_input("Display", key="mgmt_display")
    with col4:
        page_size = st.selectbox("Por pagina", [10, 25, 50, 100], index=1, key="mgmt_page_size")

    col5, col6, col7 = st.columns(3)
    with col5:
        filtro_lote = st.text_input("Codigo do lote", key="mgmt_lote")
    with col6:
        data_inicio = st.date_input("Data inicial", value=None, format="DD/MM/YYYY", key="mgmt_data_inicio")
    with col7:
        data_fim = st.date_input("Data final", value=None, format="DD/MM/YYYY", key="mgmt_data_fim")

    pagina_solicitada = st.number_input(
        "Pagina",
        min_value=1,
        step=1,
        value=int(st.session_state.get("mgmt_page_number", 1)),
        key="mgmt_page_number_input",
    )

    entries, filtered_entries, total, total_pages, current_page = load_entries_for_management(
        busca=normalize_text(busca),
        cliente=normalize_text(filtro_cliente),
        display=normalize_text(filtro_display),
        lote=normalize_text(filtro_lote),
        data_inicio=data_inicio,
        data_fim=data_fim,
        page_size=page_size,
        page_number=int(pagina_solicitada),
    )
    st.session_state["mgmt_page_number"] = current_page

    st.caption(f"{total} registro(s) encontrado(s). Pagina {current_page} de {total_pages}.")
    if not filtered_entries:
        st.info("Nenhum registro encontrado com os filtros atuais.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    export_df = build_management_dataframe(filtered_entries)
    export_stamp = datetime.now().strftime("%Y%m%d")
    render_export_buttons(export_df, export_stamp)

    st.dataframe(build_management_dataframe(entries), hide_index=True)

    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
    with nav_col1:
        if st.button("Pagina anterior", disabled=current_page <= 1, key="mgmt_prev_page"):
            st.session_state["mgmt_page_number"] = current_page - 1
            st.rerun()
    with nav_col2:
        if st.button("Proxima pagina", disabled=current_page >= total_pages, key="mgmt_next_page"):
            st.session_state["mgmt_page_number"] = current_page + 1
            st.rerun()
    with nav_col3:
        st.caption(f"Mostrando {len(entries)} item(ns) nesta pagina.")

    entry_map = {entry.id: entry for entry in entries}
    selected_id = st.selectbox(
        "Registro para editar",
        options=list(entry_map.keys()),
        format_func=lambda value: format_entry_label(entry_map[value]),
        key="mgmt_selected_id",
    )
    selected_entry = entry_map[selected_id]

    st.caption(
        f"Editando registro #{selected_entry.id}. Lancado em: "
        f"{format_timestamp_edit(selected_entry.timestamp) or 'sem timestamp'}"
    )

    with st.form(f"mgmt_edit_form_{selected_entry.id}"):
        edit_col1, edit_col2, edit_col3 = st.columns(3)
        with edit_col1:
            cliente_edit = st.text_input("Cliente", value=selected_entry.cliente)
            display_edit = st.text_input("Display", value=selected_entry.display)
            lote_edit = st.text_input("Codigo do lote", value=selected_entry.numero_display or "")
            data_edit = st.text_input(
                "Data da producao",
                value=selected_entry.data_producao or "",
                placeholder="DD/MM/AA",
            )
        with edit_col2:
            maquinario_edit = st.text_input("Ferramental / Maquina", value=selected_entry.maquinario)
            processo_edit = st.text_input("Processo", value=selected_entry.processo)
            hora_inicio_edit = st.text_input(
                "Hora iniciada",
                value=selected_entry.hora_inicio or "",
                placeholder="HH:MM",
            )
            hora_fim_edit = st.text_input(
                "Hora finalizada",
                value=selected_entry.hora_fim or "",
                placeholder="HH:MM",
            )
        with edit_col3:
            quantidade_edit = st.number_input(
                "Quantidade produzida",
                min_value=0,
                step=1,
                value=int(selected_entry.quantidade or 0),
            )
            perdas_edit = st.number_input(
                "Pecas mortas",
                min_value=0,
                step=1,
                value=int(selected_entry.pecas_mortas or 0),
            )
            quantidade_total_edit = st.number_input(
                "Quantidade total",
                min_value=0,
                step=1,
                value=int(selected_entry.quantidade_total or 0),
            )
            numero_operadores_edit = st.number_input(
                "Numero de operadores",
                min_value=0,
                step=1,
                value=int(selected_entry.numero_operadores or 0),
            )

        operadores_edit = st.text_area(
            "Operadores",
            value=selected_entry.operadores or "",
            height=100,
            help="Separe os operadores por ponto e virgula.",
        )
        salvar_alteracoes = st.form_submit_button("Salvar alteracoes")

    if salvar_alteracoes:
        errors, data_parsed, hora_inicio_parsed, hora_fim_parsed, operadores_lista = validate_edit_form(
            lote_edit,
            data_edit,
            hora_inicio_edit,
            hora_fim_edit,
            quantidade_edit,
            quantidade_total_edit,
            numero_operadores_edit,
            operadores_edit,
        )
        if errors:
            st.error("Corrija os itens antes de salvar:\n- " + "\n- ".join(errors))
        else:
            payload = {
                "schema_version": selected_entry.schema_version or SCHEMA_VERSION,
                "timestamp": selected_entry.timestamp,
                "cliente": normalize_text(cliente_edit),
                "display": normalize_text(display_edit),
                "numero_display": normalize_text(lote_edit),
                "maquinario": normalize_text(maquinario_edit),
                "processo": normalize_text(processo_edit),
                "data_producao": data_parsed.strftime("%d/%m/%y") if data_parsed else "",
                "operadores": normalize_operadores(operadores_lista),
                "numero_operadores": int(numero_operadores_edit) if numero_operadores_edit else None,
                "hora_inicio": hora_inicio_parsed.strftime("%H:%M") if hora_inicio_parsed else "",
                "hora_fim": hora_fim_parsed.strftime("%H:%M") if hora_fim_parsed else "",
                "quantidade": int(quantidade_edit),
                "pecas_mortas": int(perdas_edit),
                "quantidade_total": int(quantidade_total_edit),
            }
            update_production_entry(selected_entry, payload)
            st.success(f"Registro #{selected_entry.id} atualizado.")
            st.rerun()

    confirm_delete = st.checkbox(
        "Confirmo a exclusao permanente deste registro.",
        key=f"mgmt_confirm_delete_{selected_entry.id}",
    )
    if st.button(
        "Excluir registro",
        key=f"mgmt_delete_btn_{selected_entry.id}",
        disabled=not confirm_delete,
    ):
        deleted_id = selected_entry.id
        selected_entry.delete()
        st.success(f"Registro #{deleted_id} excluido.")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


st.divider()
tab_lancamento, tab_gestao = st.tabs(["Lancamento", "Consultar / editar"])
with tab_lancamento:
    render_lancamento_screen()
with tab_gestao:
    render_management_screen()
