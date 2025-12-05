from datetime import datetime, time
import base64
import csv
from pathlib import Path

import streamlit as st

from core.excel_utils import (
    get_acabados_for_cliente,
    get_process_choices_for_acabado_e_ferramental,
    get_unique_choices,
    get_operadores,
)


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
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "registros.csv"
SCHEMA_VERSION = "1.0"
BG_IMAGE_PATH = Path(__file__).resolve().parent / "assets" / "background.png"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"


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
        </style>
        """,
        unsafe_allow_html=True,
    )


set_background(BG_IMAGE_PATH)


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


def salvar_registro(payload: dict):
    """
    Salva o payload em CSV (append). Escreve cabecalho se o arquivo ainda nao existir.
    Adiciona versao de schema e timestamp de criacao para rastreabilidade.
    """
    is_new = not OUTPUT_FILE.exists()
    payload_to_save = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.utcnow().isoformat(),
        **payload,
    }
    fieldnames = list(payload_to_save.keys())

    with OUTPUT_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(payload_to_save)


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
        "data_producao",
        "hora_iniciada",
        "hora_finalizada",
        "quantidade_produzida",
        "quantidade_total",
        "numero_operadores",
        "operadores_selecionados",
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
        (ferramental, "Ferramental / Maquina"),
        (processo, "Processo"),
        (data_producao, "Data da producao"),
    ]
    for valor, label in obrigatorios:
        if not valor:
            erros.append(f"{label} e obrigatorio.")

    if numero_operadores < 1:
        erros.append("Numero de operadores deve ser maior ou igual a 1.")

    if not operadores_selecionados:
        erros.append("Selecione ao menos um operador.")
    elif len(operadores_selecionados) != numero_operadores:
        erros.append("A quantidade de operadores selecionados deve coincidir com o numero informado.")

    if hora_iniciada and hora_finalizada and hora_finalizada < hora_iniciada:
        erros.append("Hora finalizada deve ser maior ou igual a hora iniciada.")

    if quantidade_total < quantidade_produzida:
        erros.append("Quantidade total deve ser maior ou igual a quantidade produzida.")

    return erros


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
st.session_state.last_ferramental = ferramental

if st.session_state.last_acabado != acabado:
    st.session_state.pop("processo", None)
st.session_state.last_acabado = acabado

processo = st.selectbox(
    "Processo",
    processo_options,
    index=None,
    placeholder="Selecione",
    key="processo",
    help="Etapa/processo que sera executado.",
)

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
quantidade_total = st.number_input("Quantidade total", min_value=0, step=1, key="quantidade_total", help="Quantidade total prevista para a ordem.")
numero_operadores = st.number_input("Numero de operadores", min_value=1, step=1, key="numero_operadores", help="Total de operadores alocados.")

# Limita a selecao ao total informado e so permite marcar depois de definir o numero
if len(st.session_state.operadores_selecionados) > numero_operadores:
    st.session_state.operadores_selecionados = st.session_state.operadores_selecionados[:numero_operadores]

operadores_filtrados = operadores

# Mantem disponiveis os ja selecionados mesmo se o filtro nao os contiver
opcoes_multiselect = list(dict.fromkeys(operadores_filtrados + st.session_state.operadores_selecionados))

col1, col2 = st.columns(2)
with col2:
    if st.button("Limpar operadores selecionados", key="limpar_operadores_btn"):
        st.session_state.operadores_selecionados = []
        st.rerun()

operadores_selecionados = st.multiselect(
    f"Operadores (selecionados: {len(st.session_state.operadores_selecionados)}/{numero_operadores})",
    opcoes_multiselect,
    key="operadores_selecionados",
    placeholder="Selecione",
    max_selections=numero_operadores,
    disabled=numero_operadores < 1,
    help="Selecione os operadores responsaveis, limitado ao numero informado.",
)

with col1:
    st.caption(f"Selecionados: {len(operadores_selecionados)}/{numero_operadores}")

submitted = st.button("Salvar")

if submitted:
    erros = validate_inputs(
        cliente,
        acabado,
        ferramental,
        processo,
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
            "ferramental": ferramental,
            "processo": processo,
            "data_producao": data_producao.strftime("%d/%m/%y") if data_producao else None,
            "operadores": operadores_selecionados,
            "hora_iniciada": hora_iniciada.strftime("%H:%M") if hora_iniciada else None,
            "hora_finalizada": hora_finalizada.strftime("%H:%M") if hora_finalizada else None,
            "quantidade_produzida": quantidade_produzida,
            "numero_operadores": numero_operadores,
            "quantidade_total": quantidade_total,
        }
        salvar_registro(registro)
        st.session_state["ultimo_registro"] = registro
        st.session_state["form_salvo"] = True
        st.success("Registro salvo em output/registros.csv")

if st.session_state.get("form_salvo") and st.session_state.get("ultimo_registro"):
    reg = st.session_state["ultimo_registro"]
    st.markdown(
        f"""
        <div class="form-card">
            <div class="section-title">Resumo salvo</div>
            <ul>
                <li><strong>Cliente:</strong> {reg.get("cliente")}</li>
                <li><strong>Acabado:</strong> {reg.get("acabado")}</li>
                <li><strong>Ferramental:</strong> {reg.get("ferramental")}</li>
                <li><strong>Processo:</strong> {reg.get("processo")}</li>
                <li><strong>Data:</strong> {reg.get("data_producao")}</li>
                <li><strong>Quantidade:</strong> {reg.get("quantidade_produzida")} / {reg.get("quantidade_total")}</li>
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
