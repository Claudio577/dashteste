import re
import unicodedata
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Dashboard CEO — Suporte / Help Desk",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        .title-box {
            background: linear-gradient(135deg, #111827, #1f2937);
            padding: 26px 30px;
            border-radius: 18px;
            color: white;
            margin-bottom: 20px;
        }

        .title-box h1 {
            margin: 0;
            font-size: 32px;
        }

        .title-box p {
            margin-top: 8px;
            color: #d1d5db;
            font-size: 16px;
        }

        .kpi-card {
            padding: 22px;
            border-radius: 18px;
            color: white;
            min-height: 165px;
            box-shadow: 0px 10px 25px rgba(15, 23, 42, 0.16);
            margin-bottom: 14px;
        }

        .kpi-title {
            font-size: 12px;
            font-weight: 800;
            letter-spacing: .7px;
            text-transform: uppercase;
            opacity: .9;
        }

        .kpi-value {
            font-size: 34px;
            font-weight: 900;
            margin-top: 10px;
            line-height: 1.1;
        }

        .kpi-subtitle {
            font-size: 13px;
            opacity: .95;
            margin-top: 10px;
            line-height: 1.35;
        }

        .section-title {
            font-size: 24px;
            font-weight: 900;
            color: #0f172a;
            margin-top: 28px;
            margin-bottom: 8px;
        }

        .section-line {
            width: 185px;
            height: 4px;
            border-radius: 99px;
            background: #64748b;
            margin-bottom: 18px;
        }

        .alert-box {
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 18px;
            background: #ffffff;
            box-shadow: 0px 6px 16px rgba(15, 23, 42, 0.06);
            min-height: 95px;
            margin-bottom: 12px;
        }

        .small-muted {
            color: #64748b;
            font-size: 13px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def normalizar_texto(texto) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return texto.lower()


def limpar_nome_coluna(coluna: str) -> str:
    col = normalizar_texto(coluna)
    col = col.replace("º", "").replace("°", "")
    col = re.sub(r"[^a-z0-9 ]", " ", col)
    col = re.sub(r"\s+", " ", col).strip()
    return col


def formatar_numero(valor, casas=0):
    if valor is None or pd.isna(valor):
        return "-"
    if casas == 0:
        return f"{int(round(valor)):,}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor, casas=1):
    if valor is None or pd.isna(valor):
        return "-"
    return f"{valor:.{casas}f}%".replace(".", ",")


def formatar_horas(valor, casas=1):
    if valor is None or pd.isna(valor):
        return "-"
    return f"{valor:.{casas}f}h".replace(".", ",")


def encurtar_texto(texto, limite=45):
    texto = str(texto)
    if len(texto) <= limite:
        return texto
    return texto[:limite - 3] + "..."


def criar_card(titulo, valor, subtitulo, cor):
    st.markdown(
        f"""
        <div class="kpi-card" style="background:{cor};">
            <div class="kpi-title">{titulo}</div>
            <div class="kpi-value">{valor}</div>
            <div class="kpi-subtitle">{subtitulo}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def texto_delta(valor_atual, valor_comp, sufixo="", percentual=True, pp=False, horas=False):
    if valor_comp is None or pd.isna(valor_comp):
        return "Sem comparação"

    diff = valor_atual - valor_comp

    if pp:
        return f"Comparado: {formatar_percentual(valor_comp)} | {diff:+.1f} p.p.".replace(".", ",")

    if horas:
        return f"Comparado: {formatar_horas(valor_comp)} | {diff:+.1f}h".replace(".", ",")

    if percentual and valor_comp != 0:
        var = (diff / valor_comp) * 100
        return f"Comparado: {formatar_numero(valor_comp)} | {diff:+.0f} {sufixo} ({var:+.1f}%)".replace(".", ",")

    return f"Comparado: {formatar_numero(valor_comp)} | {diff:+.0f} {sufixo}".replace(".", ",")


# ============================================================
# MAPEAMENTO DAS COLUNAS
# ============================================================

CANDIDATOS_COLUNAS = {
    "id_chamado": [
        "solicitacao", "solicitação", "codigo", "código", "protocolo",
        "ticket", "id", "id chamado", "numero chamado", "n chamado", "chamado"
    ],
    "empresa": [
        "empresa", "cliente", "razao social", "razão social", "nome empresa",
        "empresa cliente", "nome do cliente", "cliente empresa"
    ],
    "abertura": [
        "abertura", "data abertura", "data de abertura", "criado em",
        "data criacao", "data de criacao", "início", "inicio"
    ],
    "primeiro_retorno": [
        "1 retorno", "primeiro retorno", "data primeiro retorno",
        "primeira resposta", "1 resposta", "data 1 retorno"
    ],
    "vencimento": [
        "vencimento", "data vencimento", "data de vencimento",
        "sla vencimento", "prazo", "data prazo"
    ],
    "encerramento": [
        "encerramento", "data encerramento", "data de encerramento",
        "finalizado em", "fechado em", "conclusao", "conclusão", "data conclusao"
    ],
    "status": ["status", "estado"],
    "prioridade": ["prioridade", "criticidade", "urgencia", "urgência"],
    "setor": [
        "setor de atendimento", "setor atendimento", "setor",
        "area", "área", "departamento", "fila"
    ],
    "responsavel": [
        "responsavel", "responsável", "atendente", "tecnico",
        "técnico", "agente", "operador"
    ],
    "tipo": ["tipo", "tipo chamado", "tipo de chamado"],
    "item": ["item", "item chamado", "item de chamado", "servico", "serviço", "produto"],
    "categoria": ["categoria", "categoria chamado", "categoria de chamado"],
    "situacao": ["situacao", "situação"],
    "assunto": ["assunto", "titulo", "título", "descricao", "descrição", "resumo"],
    "avaliacao": ["avaliacao", "avaliação", "nota", "satisfacao", "satisfação"],
    "horas_consumidas": [
        "horas consumidas", "horas", "tempo consumido",
        "tempo gasto", "horas gastas"
    ],
}


def mapear_colunas(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    colunas_originais = list(df.columns)
    colunas_limpas = {col: limpar_nome_coluna(col) for col in colunas_originais}
    mapeamento = {}

    for destino, candidatos in CANDIDATOS_COLUNAS.items():
        candidatos_limpos = [limpar_nome_coluna(c) for c in candidatos]
        encontrado = None

        for col_original, col_limpa in colunas_limpas.items():
            if col_limpa in candidatos_limpos:
                encontrado = col_original
                break

        if encontrado is None:
            for col_original, col_limpa in colunas_limpas.items():
                for cand in candidatos_limpos:
                    if cand and (cand in col_limpa or col_limpa in cand):
                        encontrado = col_original
                        break
                if encontrado:
                    break

        mapeamento[destino] = encontrado

    return mapeamento


def renomear_colunas_padrao(df: pd.DataFrame, mapeamento: Dict[str, Optional[str]]) -> pd.DataFrame:
    nomes_padrao = {
        "id_chamado": "ID_Chamado",
        "empresa": "Empresa",
        "abertura": "Abertura",
        "primeiro_retorno": "Primeiro_Retorno",
        "vencimento": "Vencimento",
        "encerramento": "Encerramento",
        "status": "Status",
        "prioridade": "Prioridade",
        "setor": "Setor",
        "responsavel": "Responsavel",
        "tipo": "Tipo",
        "item": "Item",
        "categoria": "Categoria",
        "situacao": "Situacao",
        "assunto": "Assunto",
        "avaliacao": "Avaliacao",
        "horas_consumidas": "Horas_Consumidas",
    }

    renomear = {}

    for destino, origem in mapeamento.items():
        if origem is not None and origem in df.columns:
            renomear[origem] = nomes_padrao[destino]

    df = df.rename(columns=renomear)

    for col in nomes_padrao.values():
        if col not in df.columns:
            df[col] = np.nan

    return df


# ============================================================
# TRATAMENTO DOS EXCEL
# ============================================================

MESES_PT = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "marco": 3, "março": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}

MESES_NOME = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def extrair_mes_arquivo(nome_arquivo: str) -> Tuple[Optional[int], Optional[int]]:
    nome = normalizar_texto(nome_arquivo)

    ano_match = re.search(r"(20\d{2})", nome)
    ano = int(ano_match.group(1)) if ano_match else None

    mes = None
    for nome_mes, num_mes in MESES_PT.items():
        if nome_mes in nome:
            mes = num_mes
            break

    if mes and not ano:
        ano = 2026

    return mes, ano


def converter_data(serie):
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def padronizar_empresa(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return "Não informado"

    texto_original = str(valor).strip()
    texto_limpo = normalizar_texto(texto_original).upper()

    if "CBLOC" in texto_limpo or "ACBLOC" in texto_limpo:
        return "CBLOC"

    texto_original = re.sub(r"\s+", " ", texto_original)
    return texto_original.title()


def preparar_dataframe(df: pd.DataFrame, nome_arquivo: str) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    mapeamento = mapear_colunas(df)
    df = renomear_colunas_padrao(df, mapeamento)

    df["Arquivo_Origem"] = nome_arquivo

    for col in ["Abertura", "Primeiro_Retorno", "Vencimento", "Encerramento"]:
        df[col] = converter_data(df[col])

    mes_arquivo, ano_arquivo = extrair_mes_arquivo(nome_arquivo)

    # Primeiro tenta mês pela coluna Abertura
    if df["Abertura"].notna().any():
        df["Ano"] = df["Abertura"].dt.year
        df["Mes"] = df["Abertura"].dt.month
    else:
        df["Ano"] = ano_arquivo
        df["Mes"] = mes_arquivo

    # Se não conseguir pela data, usa o nome do arquivo
    if mes_arquivo and ano_arquivo:
        df["Mes"] = df["Mes"].fillna(mes_arquivo)
        df["Ano"] = df["Ano"].fillna(ano_arquivo)

    df["Ano"] = df["Ano"].fillna(2026).astype(int)
    df["Mes"] = df["Mes"].fillna(1).astype(int)

    df["AnoMesNum"] = df["Ano"] * 100 + df["Mes"]
    df["MesAno"] = df["Mes"].map(MESES_NOME) + "/" + df["Ano"].astype(str)

    df["Empresa_Padronizada"] = df["Empresa"].apply(padronizar_empresa)

    for col in [
        "Status", "Prioridade", "Setor", "Responsavel", "Tipo",
        "Item", "Categoria", "Situacao", "Assunto", "Avaliacao"
    ]:
        df[col] = df[col].fillna("Não informado").astype(str).str.strip()
        df[col] = df[col].replace({"": "Não informado"})

    return df, mapeamento


@st.cache_data(show_spinner=False)
def carregar_dados_excel_cache(lista_arquivos: List[Tuple[str, bytes]]) -> Tuple[pd.DataFrame, List[str], Dict[str, Dict[str, Optional[str]]]]:
    lista = []
    arquivos = []
    mapas = {}

    for nome, conteudo in lista_arquivos:
        arquivos.append(nome)

        try:
            bio = BytesIO(conteudo)

            if nome.lower().endswith(".xls"):
                df = pd.read_excel(bio, engine="xlrd")
            else:
                df = pd.read_excel(bio, engine="openpyxl")

            df, mapa = preparar_dataframe(df, nome)
            mapas[nome] = mapa
            lista.append(df)

        except Exception as e:
            st.error(f"Erro ao ler o arquivo {nome}: {e}")

    if not lista:
        return pd.DataFrame(), arquivos, mapas

    df_final = pd.concat(lista, ignore_index=True)
    df_final = df_final.dropna(how="all")

    return df_final, arquivos, mapas


def carregar_dados_api(data_inicio: str, data_fim: str):
    """
    Função preparada para uso futuro via API.

    Usar somente GET.
    Não usar POST, PUT, PATCH ou DELETE.

    Exemplo futuro:
    GET /chamados?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD
    """
    return pd.DataFrame()


# ============================================================
# KPIs
# ============================================================

def total_chamados(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    if "ID_Chamado" in df.columns and df["ID_Chamado"].notna().any():
        ids = df["ID_Chamado"].astype(str).str.strip()
        ids = ids[~ids.isin(["", "nan", "None", "Não informado"])]
        if len(ids) > 0:
            return int(ids.nunique())

    return int(len(df))


def calcular_kpis(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {
            "total": 0,
            "empresas": 0,
            "encerrados": 0,
            "pendentes": 0,
            "sla": 0.0,
            "retorno_1h": 0.0,
            "resolucao_h": 0.0,
            "criticos": 0,
            "fora_sla": 0,
            "sem_avaliacao": 0,
        }

    total = total_chamados(df)

    empresas = int(
        df["Empresa_Padronizada"]
        .replace("Não informado", np.nan)
        .dropna()
        .nunique()
    )

    status_norm = df["Status"].apply(normalizar_texto)

    encerrado_status = status_norm.str.contains(
        "encerr|finaliz|fechad|conclu",
        na=False,
        regex=True
    )

    encerrado_data = df["Encerramento"].notna()
    encerrados_mask = encerrado_data | encerrado_status
    encerrados = int(encerrados_mask.sum())

    pendentes = int(total - encerrados)
    if pendentes < 0:
        pendentes = int((~encerrados_mask).sum())

    tem_datas_sla = df["Vencimento"].notna() & df["Encerramento"].notna()
    dentro_sla_mask = tem_datas_sla & (df["Encerramento"] <= df["Vencimento"])

    chamados_com_vencimento = int(df["Vencimento"].notna().sum())
    dentro_sla = int(dentro_sla_mask.sum())

    sla = (dentro_sla / chamados_com_vencimento) * 100 if chamados_com_vencimento > 0 else 0.0

    hoje = pd.Timestamp.today()

    fora_sla_mask = (
        (
            df["Vencimento"].notna()
            & df["Encerramento"].notna()
            & (df["Encerramento"] > df["Vencimento"])
        )
        |
        (
            df["Vencimento"].notna()
            & df["Encerramento"].isna()
            & (df["Vencimento"] < hoje)
        )
    )

    fora_sla = int(fora_sla_mask.sum())

    tem_retorno = df["Abertura"].notna() & df["Primeiro_Retorno"].notna()

    diff_retorno_min = (
        df["Primeiro_Retorno"] - df["Abertura"]
    ).dt.total_seconds() / 60

    retorno_1h_count = int(
        (
            tem_retorno
            & (diff_retorno_min <= 60)
            & (diff_retorno_min >= 0)
        ).sum()
    )

    base_retorno = int(tem_retorno.sum())
    retorno_1h = (retorno_1h_count / base_retorno) * 100 if base_retorno > 0 else 0.0

    tem_resolucao = df["Abertura"].notna() & df["Encerramento"].notna()

    diff_resolucao_h = (
        df["Encerramento"] - df["Abertura"]
    ).dt.total_seconds() / 3600

    diff_resolucao_h = diff_resolucao_h[
        tem_resolucao & (diff_resolucao_h >= 0)
    ]

    resolucao_h = float(diff_resolucao_h.mean()) if len(diff_resolucao_h) > 0 else 0.0

    prioridade_norm = df["Prioridade"].apply(normalizar_texto)
    criticos = int(prioridade_norm.str.contains("critic", na=False).sum())

    aval_norm = df["Avaliacao"].astype(str).apply(normalizar_texto)

    mask_sem_avaliacao = (
        aval_norm.isin([
            "",
            "nan",
            "none",
            "nao informado",
            "n/a",
            "na",
            "sem avaliacao"
        ])
        | aval_norm.str.contains("sem avaliacao", na=False)
    )

    sem_avaliacao = int(mask_sem_avaliacao.sum())

    return {
        "total": total,
        "empresas": empresas,
        "encerrados": encerrados,
        "pendentes": pendentes,
        "sla": float(sla),
        "retorno_1h": float(retorno_1h),
        "resolucao_h": float(resolucao_h),
        "criticos": criticos,
        "fora_sla": fora_sla,
        "sem_avaliacao": sem_avaliacao,
    }


def obter_meses_ordenados(df: pd.DataFrame) -> List[str]:
    ordem = (
        df[["MesAno", "AnoMesNum"]]
        .drop_duplicates()
        .sort_values("AnoMesNum")
    )
    return ordem["MesAno"].tolist()


def mes_anterior_disponivel(df: pd.DataFrame, mes_principal: str) -> Optional[str]:
    meses = (
        df[["MesAno", "AnoMesNum"]]
        .drop_duplicates()
        .sort_values("AnoMesNum")
    )

    if mes_principal not in meses["MesAno"].values:
        return None

    atual_num = int(meses.loc[meses["MesAno"] == mes_principal, "AnoMesNum"].iloc[0])
    anteriores = meses[meses["AnoMesNum"] < atual_num]

    if anteriores.empty:
        return None

    return anteriores.iloc[-1]["MesAno"]


def ranking_clientes_aumento(df_principal, df_comp) -> pd.DataFrame:
    atual = (
        df_principal.groupby("Empresa_Padronizada")
        .size()
        .reset_index(name="Chamados_Mes_Principal")
    )

    comp = (
        df_comp.groupby("Empresa_Padronizada")
        .size()
        .reset_index(name="Chamados_Mes_Comparado")
    )

    ranking = pd.merge(atual, comp, on="Empresa_Padronizada", how="outer").fillna(0)

    ranking["Chamados_Mes_Principal"] = ranking["Chamados_Mes_Principal"].astype(int)
    ranking["Chamados_Mes_Comparado"] = ranking["Chamados_Mes_Comparado"].astype(int)

    ranking["Diferenca"] = ranking["Chamados_Mes_Principal"] - ranking["Chamados_Mes_Comparado"]

    ranking["Variacao_%"] = np.where(
        ranking["Chamados_Mes_Comparado"] > 0,
        (ranking["Diferenca"] / ranking["Chamados_Mes_Comparado"]) * 100,
        np.nan
    )

    ranking = ranking.sort_values(
        ["Diferenca", "Variacao_%"],
        ascending=[False, False]
    )

    return ranking


# ============================================================
# GRÁFICOS
# ============================================================

def grafico_resumo_unico(kpis, mes):
    dados = pd.DataFrame({
        "Indicador": ["Chamados", "Encerrados", "Críticos", "Pendentes"],
        "Quantidade": [
            kpis["total"],
            kpis["encerrados"],
            kpis["criticos"],
            kpis["pendentes"],
        ],
    })

    fig = px.bar(
        dados,
        x="Indicador",
        y="Quantidade",
        text="Quantidade",
        title=f"Resumo Geral — {mes}",
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(height=430, showlegend=False)

    return fig


def grafico_resumo_comparacao(kpi_princ, kpi_comp, mes_princ, mes_comp):
    dados = pd.DataFrame({
        "Indicador": ["Chamados", "Encerrados", "Críticos", "Pendentes"] * 2,
        "Mês": [mes_comp] * 4 + [mes_princ] * 4,
        "Quantidade": [
            kpi_comp["total"],
            kpi_comp["encerrados"],
            kpi_comp["criticos"],
            kpi_comp["pendentes"],
            kpi_princ["total"],
            kpi_princ["encerrados"],
            kpi_princ["criticos"],
            kpi_princ["pendentes"],
        ],
    })

    fig = px.bar(
        dados,
        x="Indicador",
        y="Quantidade",
        color="Mês",
        barmode="group",
        text="Quantidade",
        title=f"Resumo Geral — {mes_princ} x {mes_comp}",
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(height=430)

    return fig


def grafico_qualidade_unico(kpis, mes):
    fig = go.Figure()

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=kpis["sla"],
        title={"text": f"SLA Cumprido — {mes}"},
        gauge={
            "axis": {"range": [0, 100]},
            "threshold": {"line": {"width": 4}, "value": 80}
        },
        domain={"x": [0, 0.45], "y": [0, 1]},
    ))

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=kpis["retorno_1h"],
        title={"text": f"1º Retorno ≤ 1h — {mes}"},
        gauge={
            "axis": {"range": [0, 100]},
            "threshold": {"line": {"width": 4}, "value": 70}
        },
        domain={"x": [0.55, 1], "y": [0, 1]},
    ))

    fig.update_layout(height=380)

    return fig


def grafico_qualidade_comparacao(kpi_princ, kpi_comp, mes_princ, mes_comp):
    dados = pd.DataFrame({
        "Indicador": ["SLA Cumprido", "1º Retorno ≤ 1h"] * 2,
        "Mês": [mes_comp, mes_comp, mes_princ, mes_princ],
        "Percentual": [
            kpi_comp["sla"],
            kpi_comp["retorno_1h"],
            kpi_princ["sla"],
            kpi_princ["retorno_1h"],
        ],
    })

    fig = px.bar(
        dados,
        x="Indicador",
        y="Percentual",
        color="Mês",
        barmode="group",
        text=dados["Percentual"].map(lambda x: f"{x:.1f}%"),
        title=f"Indicadores de Qualidade — {mes_princ} x {mes_comp}",
    )

    fig.update_traces(textposition="outside")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(height=380)

    return fig


def grafico_evolucao(df):
    mensal = (
        df.groupby(["AnoMesNum", "MesAno"])
        .size()
        .reset_index(name="Chamados")
        .sort_values("AnoMesNum")
    )

    fig = px.line(
        mensal,
        x="MesAno",
        y="Chamados",
        markers=True,
        title="Evolução Mensal de Chamados",
    )

    fig.update_layout(height=390)

    return fig


def grafico_top_barra(df, coluna, titulo, top=10):
    if df.empty or coluna not in df.columns:
        return go.Figure()

    dados = (
        df.groupby(coluna)
        .size()
        .reset_index(name="Chamados")
        .sort_values("Chamados", ascending=False)
        .head(top)
    )

    fig = px.bar(
        dados,
        x="Chamados",
        y=coluna,
        orientation="h",
        text="Chamados",
        title=titulo,
    )

    fig.update_traces(textposition="inside")

    fig.update_layout(
        height=max(420, 42 * len(dados) + 150),
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=20, r=35, t=70, b=40),
    )

    return fig


def grafico_prioridade(df, titulo):
    if df.empty:
        return go.Figure()

    dados = (
        df.groupby("Prioridade")
        .size()
        .reset_index(name="Chamados")
        .sort_values("Chamados", ascending=False)
    )

    fig = px.pie(
        dados,
        values="Chamados",
        names="Prioridade",
        title=titulo,
        hole=0.35,
    )

    fig.update_layout(height=420)

    return fig


def grafico_comparacao_categoria(df_principal, df_comp, coluna, mes_principal, mes_comparacao, titulo, top=10):
    if df_principal.empty and df_comp.empty:
        return go.Figure()

    atual = (
        df_principal.groupby(coluna)
        .size()
        .reset_index(name=mes_principal)
    )

    comparado = (
        df_comp.groupby(coluna)
        .size()
        .reset_index(name=mes_comparacao)
    )

    dados = pd.merge(comparado, atual, on=coluna, how="outer").fillna(0)

    dados[mes_principal] = dados[mes_principal].astype(int)
    dados[mes_comparacao] = dados[mes_comparacao].astype(int)

    dados["Total"] = dados[mes_principal] + dados[mes_comparacao]

    dados = (
        dados.sort_values("Total", ascending=False)
        .head(top)
        .copy()
    )

    dados["Categoria_Curta"] = dados[coluna].apply(lambda x: encurtar_texto(x, 45))

    dados_melt = dados.melt(
        id_vars=["Categoria_Curta"],
        value_vars=[mes_comparacao, mes_principal],
        var_name="Mês",
        value_name="Chamados"
    )

    fig = px.bar(
        dados_melt,
        x="Chamados",
        y="Categoria_Curta",
        color="Mês",
        barmode="group",
        orientation="h",
        text="Chamados",
        title=titulo,
    )

    fig.update_traces(textposition="outside")

    fig.update_layout(
        height=max(430, 45 * len(dados) + 160),
        yaxis={"categoryorder": "total ascending"},
        yaxis_title=coluna,
        xaxis_title="Chamados",
        legend_title_text="Mês",
        margin=dict(l=20, r=35, t=70, b=40),
    )

    return fig


def grafico_prioridade_comparacao(df_principal, df_comp, mes_principal, mes_comparacao):
    return grafico_comparacao_categoria(
        df_principal=df_principal,
        df_comp=df_comp,
        coluna="Prioridade",
        mes_principal=mes_principal,
        mes_comparacao=mes_comparacao,
        titulo=f"Chamados por Prioridade — {mes_principal} x {mes_comparacao}",
        top=10
    )


# ============================================================
# INTERFACE
# ============================================================

st.markdown(
    """
    <div class="title-box">
        <h1>Dashboard CEO — Suporte / Help Desk</h1>
        <p>Visão executiva mensal com SLA, primeiro retorno, criticidade, clientes e causas dos chamados.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# UPLOAD
# ============================================================

st.sidebar.header("📤 Upload dos Excel")

uploaded_files = st.sidebar.file_uploader(
    "Envie um ou mais arquivos Excel",
    type=["xls", "xlsx"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Faça upload de um ou mais arquivos Excel para gerar o dashboard.")
    st.stop()

lista_arquivos = [(arquivo.name, arquivo.getvalue()) for arquivo in uploaded_files]

df, arquivos_carregados, mapas_colunas = carregar_dados_excel_cache(lista_arquivos)

if df.empty:
    st.error("Nenhum dado válido foi carregado. Verifique os arquivos enviados.")
    st.stop()


# ============================================================
# INFORMAÇÕES DO DATASET
# ============================================================

st.sidebar.markdown("### ℹ️ Informações do Dataset")
st.sidebar.write(f"**Arquivos enviados:** {len(arquivos_carregados)}")

for arq in arquivos_carregados:
    st.sidebar.write(f"- `{arq}`")

st.sidebar.write(f"**Total de linhas:** {len(df)}")

with st.sidebar.expander("📋 Colunas mapeadas"):
    for arquivo, mapa in mapas_colunas.items():
        st.write(f"**{arquivo}**")
        mapa_exibicao = {
            destino: origem if origem is not None else "Não encontrada"
            for destino, origem in mapa.items()
        }
        st.json(mapa_exibicao)


# ============================================================
# FILTROS PRINCIPAIS NA TELA
# ============================================================

meses = obter_meses_ordenados(df)

st.markdown(
    '<div class="section-title">🎛️ Filtros do Dashboard</div><div class="section-line"></div>',
    unsafe_allow_html=True,
)

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    modo = st.radio(
        "Modo de visão",
        ["Único mês", "Comparação"],
        index=0,
        horizontal=True,
        key="modo_visao_principal",
    )

with col_f2:
    mes_principal = st.selectbox(
        "Mês principal",
        meses,
        index=len(meses) - 1,
        key="mes_principal_tela",
    )

mes_sugerido = mes_anterior_disponivel(df, mes_principal)

if mes_sugerido and mes_sugerido in meses:
    index_comp = meses.index(mes_sugerido)
else:
    index_comp = 0

with col_f3:
    if modo == "Comparação":
        mes_comparacao = st.selectbox(
            "Mês de comparação",
            meses,
            index=index_comp,
            key="mes_comparacao_tela",
        )
    else:
        mes_comparacao = None
        st.info("Comparação desligada")


# ============================================================
# FILTROS ADICIONAIS NA LATERAL
# ============================================================

st.sidebar.header("🎛️ Filtros adicionais")

empresas = ["Todas"] + sorted(df["Empresa_Padronizada"].dropna().unique().tolist())
setores = ["Todos"] + sorted(df["Setor"].dropna().unique().tolist())
responsaveis = ["Todos"] + sorted(df["Responsavel"].dropna().unique().tolist())
prioridades = ["Todas"] + sorted(df["Prioridade"].dropna().unique().tolist())
status_lista = ["Todos"] + sorted(df["Status"].dropna().unique().tolist())

empresa_sel = st.sidebar.selectbox("Empresa", empresas)
setor_sel = st.sidebar.selectbox("Setor", setores)
resp_sel = st.sidebar.selectbox("Responsável", responsaveis)
prioridade_sel = st.sidebar.selectbox("Prioridade", prioridades)
status_sel = st.sidebar.selectbox("Status", status_lista)


def aplicar_filtros_base(df_base: pd.DataFrame) -> pd.DataFrame:
    df_filtrado = df_base.copy()

    if empresa_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Empresa_Padronizada"] == empresa_sel]

    if setor_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Setor"] == setor_sel]

    if resp_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Responsavel"] == resp_sel]

    if prioridade_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Prioridade"] == prioridade_sel]

    if status_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Status"] == status_sel]

    return df_filtrado


df_filtrado_geral = aplicar_filtros_base(df)

df_principal = df_filtrado_geral[
    df_filtrado_geral["MesAno"].astype(str) == str(mes_principal)
].copy()

kpi_princ = calcular_kpis(df_principal)

df_comp = pd.DataFrame()
kpi_comp = None

if modo == "Comparação":
    df_comp = df_filtrado_geral[
        df_filtrado_geral["MesAno"].astype(str) == str(mes_comparacao)
    ].copy()

    kpi_comp = calcular_kpis(df_comp)

    if mes_comparacao == mes_principal:
        st.warning("O mês de comparação é igual ao mês principal. Escolha meses diferentes para comparar melhor.")


# ============================================================
# CONFERÊNCIA
# ============================================================

with st.expander("🧪 Conferência por mês"):
    conferencia = (
        df_filtrado_geral
        .groupby(["AnoMesNum", "MesAno"])
        .size()
        .reset_index(name="Linhas")
        .sort_values("AnoMesNum")
    )

    st.dataframe(conferencia[["MesAno", "Linhas"]], use_container_width=True)

    st.write("Modo selecionado:", modo)
    st.write("Mês principal selecionado:", mes_principal)
    st.write("Linhas do mês principal:", len(df_principal))

    if modo == "Comparação":
        st.write("Mês de comparação selecionado:", mes_comparacao)
        st.write("Linhas do mês de comparação:", len(df_comp))


# ============================================================
# KPIs
# ============================================================

if modo == "Único mês":
    st.markdown(
        f'<div class="section-title">📌 KPIs — {mes_principal}</div><div class="section-line"></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="section-title">📌 KPIs — {mes_principal} x {mes_comparacao}</div><div class="section-line"></div>',
        unsafe_allow_html=True,
    )

cores = [
    "linear-gradient(135deg, #667eea, #764ba2)",
    "linear-gradient(135deg, #7c3aed, #4f46e5)",
    "linear-gradient(135deg, #0f9b8e, #38ef7d)",
    "linear-gradient(135deg, #f59e0b, #fcd34d)",
    "linear-gradient(135deg, #14b8a6, #5eead4)",
    "linear-gradient(135deg, #1e3a8a, #334155)",
    "linear-gradient(135deg, #ef4444, #f97316)",
    "linear-gradient(135deg, #e11d48, #ef4444)",
]

if modo == "Único mês":
    cards = [
        ("Total de chamados", formatar_numero(kpi_princ["total"]), "Volume do mês"),
        ("Empresas atendidas", formatar_numero(kpi_princ["empresas"]), "Clientes atendidos"),
        ("Chamados encerrados", formatar_numero(kpi_princ["encerrados"]), "Finalizados"),
        ("Chamados pendentes", formatar_numero(kpi_princ["pendentes"]), "Abertos ou sem encerramento"),
        ("SLA cumprido", formatar_percentual(kpi_princ["sla"]), "Dentro do prazo"),
        ("1º retorno ≤ 1h", formatar_percentual(kpi_princ["retorno_1h"]), "Velocidade inicial"),
        ("Tempo médio resolução", formatar_horas(kpi_princ["resolucao_h"]), "Tempo médio até finalizar"),
        ("Chamados críticos", formatar_numero(kpi_princ["criticos"]), "Risco operacional"),
    ]
else:
    cards = [
        ("Total de chamados", formatar_numero(kpi_princ["total"]), texto_delta(kpi_princ["total"], kpi_comp["total"], "chamados")),
        ("Empresas atendidas", formatar_numero(kpi_princ["empresas"]), texto_delta(kpi_princ["empresas"], kpi_comp["empresas"], "empresas")),
        ("Chamados encerrados", formatar_numero(kpi_princ["encerrados"]), texto_delta(kpi_princ["encerrados"], kpi_comp["encerrados"], "encerrados")),
        ("Chamados pendentes", formatar_numero(kpi_princ["pendentes"]), texto_delta(kpi_princ["pendentes"], kpi_comp["pendentes"], "pendentes")),
        ("SLA cumprido", formatar_percentual(kpi_princ["sla"]), texto_delta(kpi_princ["sla"], kpi_comp["sla"], pp=True)),
        ("1º retorno ≤ 1h", formatar_percentual(kpi_princ["retorno_1h"]), texto_delta(kpi_princ["retorno_1h"], kpi_comp["retorno_1h"], pp=True)),
        ("Tempo médio resolução", formatar_horas(kpi_princ["resolucao_h"]), texto_delta(kpi_princ["resolucao_h"], kpi_comp["resolucao_h"], horas=True)),
        ("Chamados críticos", formatar_numero(kpi_princ["criticos"]), texto_delta(kpi_princ["criticos"], kpi_comp["criticos"], "críticos")),
    ]

for linha in range(2):
    cols = st.columns(4)

    for i in range(4):
        idx = linha * 4 + i

        with cols[i]:
            criar_card(
                cards[idx][0],
                cards[idx][1],
                cards[idx][2],
                cores[idx],
            )


# ============================================================
# RESUMO GERAL
# ============================================================

st.markdown(
    '<div class="section-title">📈 Resumo Geral</div><div class="section-line"></div>',
    unsafe_allow_html=True,
)

if modo == "Único mês":
    st.plotly_chart(
        grafico_resumo_unico(kpi_princ, mes_principal),
        use_container_width=True,
    )
else:
    st.plotly_chart(
        grafico_resumo_comparacao(kpi_princ, kpi_comp, mes_principal, mes_comparacao),
        use_container_width=True,
    )


# ============================================================
# QUALIDADE
# ============================================================

st.markdown(
    '<div class="section-title">🎯 Indicadores de Qualidade</div><div class="section-line"></div>',
    unsafe_allow_html=True,
)

if modo == "Único mês":
    st.plotly_chart(
        grafico_qualidade_unico(kpi_princ, mes_principal),
        use_container_width=True,
    )
else:
    st.plotly_chart(
        grafico_qualidade_comparacao(kpi_princ, kpi_comp, mes_principal, mes_comparacao),
        use_container_width=True,
    )


# ============================================================
# EVOLUÇÃO MENSAL
# ============================================================

st.markdown(
    '<div class="section-title">🗓️ Evolução Mensal</div><div class="section-line"></div>',
    unsafe_allow_html=True,
)

st.plotly_chart(
    grafico_evolucao(df_filtrado_geral),
    use_container_width=True,
)


# ============================================================
# OPERAÇÃO
# ============================================================

st.markdown(
    '<div class="section-title">🏢 Operação, Clientes e Motivos</div><div class="section-line"></div>',
    unsafe_allow_html=True,
)

if modo == "Único mês":
    base_visual = df_principal

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            grafico_top_barra(
                base_visual,
                "Setor",
                f"Chamados por Setor — {mes_principal}",
                top=10,
            ),
            use_container_width=True,
        )

    with col2:
        st.plotly_chart(
            grafico_prioridade(
                base_visual,
                f"Chamados por Prioridade — {mes_principal}",
            ),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)

    with col3:
        st.plotly_chart(
            grafico_top_barra(
                base_visual,
                "Empresa_Padronizada",
                f"Top Clientes — {mes_principal}",
                top=10,
            ),
            use_container_width=True,
        )

    with col4:
        st.plotly_chart(
            grafico_top_barra(
                base_visual,
                "Tipo",
                f"Top Motivos / Tipos — {mes_principal}",
                top=10,
            ),
            use_container_width=True,
        )

else:
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            grafico_comparacao_categoria(
                df_principal,
                df_comp,
                "Setor",
                mes_principal,
                mes_comparacao,
                f"Chamados por Setor — {mes_principal} x {mes_comparacao}",
                top=10,
            ),
            use_container_width=True,
        )

    with col2:
        st.plotly_chart(
            grafico_prioridade_comparacao(
                df_principal,
                df_comp,
                mes_principal,
                mes_comparacao,
            ),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)

    with col3:
        st.plotly_chart(
            grafico_comparacao_categoria(
                df_principal,
                df_comp,
                "Empresa_Padronizada",
                mes_principal,
                mes_comparacao,
                f"Top Clientes — {mes_principal} x {mes_comparacao}",
                top=10,
            ),
            use_container_width=True,
        )

    with col4:
        st.plotly_chart(
            grafico_comparacao_categoria(
                df_principal,
                df_comp,
                "Tipo",
                mes_principal,
                mes_comparacao,
                f"Top Motivos / Tipos — {mes_principal} x {mes_comparacao}",
                top=10,
            ),
            use_container_width=True,
        )


# ============================================================
# CLIENTES COM MAIOR AUMENTO
# ============================================================

if modo == "Comparação":
    st.markdown(
        '<div class="section-title">🚨 Clientes com Maior Aumento</div><div class="section-line"></div>',
        unsafe_allow_html=True,
    )

    ranking = ranking_clientes_aumento(df_principal, df_comp)
    ranking_pos = ranking[ranking["Diferenca"] > 0].copy().head(10)

    if ranking_pos.empty:
        st.info("Nenhum cliente apresentou aumento de chamados no período comparado.")
    else:
        tabela = ranking_pos.copy()

        tabela["Variação %"] = tabela["Variacao_%"].apply(
            lambda x: "-" if pd.isna(x) else f"{x:.1f}%".replace(".", ",")
        )

        tabela = tabela.rename(columns={
            "Empresa_Padronizada": "Empresa",
            "Chamados_Mes_Comparado": f"Chamados {mes_comparacao}",
            "Chamados_Mes_Principal": f"Chamados {mes_principal}",
            "Diferenca": "Aumento",
        })

        tabela = tabela[
            [
                "Empresa",
                f"Chamados {mes_comparacao}",
                f"Chamados {mes_principal}",
                "Aumento",
                "Variação %",
            ]
        ]

        st.dataframe(tabela, use_container_width=True, hide_index=True)

        grafico = ranking_pos.head(8).copy()
        grafico["Empresa_Curta"] = grafico["Empresa_Padronizada"].apply(
            lambda x: encurtar_texto(x, 42)
        )

        fig = px.bar(
            grafico,
            x="Diferenca",
            y="Empresa_Curta",
            orientation="h",
            text="Diferenca",
            title=f"Maiores aumentos de chamados — {mes_principal} x {mes_comparacao}",
        )

        fig.update_traces(texttemplate="+%{text}", textposition="outside")

        fig.update_layout(
            height=450,
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Aumento de chamados",
            yaxis_title="Cliente",
            showlegend=False,
            margin=dict(l=20, r=35, t=70, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# ALERTAS
# ============================================================

st.markdown(
    '<div class="section-title">⚠️ Alertas Executivos</div><div class="section-line"></div>',
    unsafe_allow_html=True,
)

alertas = [
    ("Chamados críticos", formatar_numero(kpi_princ["criticos"])),
    ("Pendentes", formatar_numero(kpi_princ["pendentes"])),
    ("Fora do SLA", formatar_numero(kpi_princ["fora_sla"])),
    ("Sem avaliação", formatar_numero(kpi_princ["sem_avaliacao"])),
    ("1º retorno ≤ 1h", formatar_percentual(kpi_princ["retorno_1h"])),
]

if modo == "Comparação":
    ranking = ranking_clientes_aumento(df_principal, df_comp)
    ranking_pos = ranking[ranking["Diferenca"] > 0].copy()

    if not ranking_pos.empty:
        top_cliente = ranking_pos.iloc[0]

        var_txt = "-"

        if not pd.isna(top_cliente["Variacao_%"]):
            var_txt = f"{top_cliente['Variacao_%']:.1f}%".replace(".", ",")

        alertas.append((
            "Cliente com maior aumento",
            f"{top_cliente['Empresa_Padronizada']} | +{int(top_cliente['Diferenca'])} ({var_txt})"
        ))

    cbloc = ranking[ranking["Empresa_Padronizada"] == "CBLOC"]

    if not cbloc.empty:
        cbloc_row = cbloc.iloc[0]

        if cbloc_row["Diferenca"] > 0:
            var_txt = "-"

            if not pd.isna(cbloc_row["Variacao_%"]):
                var_txt = f"{cbloc_row['Variacao_%']:.1f}%".replace(".", ",")

            alertas.append((
                "CBLOC em atenção",
                f"+{int(cbloc_row['Diferenca'])} chamados ({var_txt})"
            ))

cols = st.columns(3)

for i, (titulo, valor) in enumerate(alertas):
    with cols[i % 3]:
        st.markdown(
            f"""
            <div class="alert-box">
                <div class="small-muted">{titulo}</div>
                <div style="font-size:24px;font-weight:900;color:#0f172a;margin-top:5px;">{valor}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# AMOSTRA
# ============================================================

with st.expander("🔎 Ver amostra dos dados tratados"):
    st.dataframe(df_filtrado_geral.head(100), use_container_width=True)

st.caption("Dashboard preparado para Excel via upload e futura integração com API usando somente GET.")
