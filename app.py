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

VERSAO_APP = "COMPACTO v2.0"

st.set_page_config(
    page_title="Dashboard CEO Compacto — Suporte",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# CSS — PAINEL COMPACTO
# ============================================================

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 0.8rem;
            padding-bottom: 1.2rem;
            max-width: 1500px;
        }

        .top-header {
            background: linear-gradient(135deg, #0f172a, #1e3a8a);
            color: white;
            padding: 10px 16px;
            border-radius: 10px;
            margin-bottom: 8px;
        }

        .top-header h1 {
            margin: 0;
            font-size: 21px;
            font-weight: 900;
        }

        .top-header p {
            margin: 3px 0 0 0;
            font-size: 11px;
            color: #dbeafe;
        }

        .version-badge {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            background: #facc15;
            color: #111827;
            font-size: 11px;
            font-weight: 900;
            margin-left: 8px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 950;
            color: #020617;
            margin-top: 10px;
            margin-bottom: 4px;
        }

        .section-line {
            width: 115px;
            height: 3px;
            border-radius: 999px;
            background: #1e3a8a;
            margin-bottom: 8px;
        }

        .kpi-card {
            padding: 12px 13px;
            border-radius: 12px;
            color: #ffffff;
            min-height: 96px;
            box-shadow: 0px 7px 16px rgba(15, 23, 42, 0.18);
            margin-bottom: 8px;
            border: 1px solid rgba(255,255,255,0.18);
        }

        .kpi-title {
            font-size: 10.5px;
            font-weight: 950;
            letter-spacing: .5px;
            text-transform: uppercase;
            opacity: 1;
            color: #ffffff;
            text-shadow: 0 1px 3px rgba(0,0,0,0.45);
        }

        .kpi-value {
            font-size: 28px;
            font-weight: 950;
            margin-top: 5px;
            line-height: 1.05;
            color: #ffffff;
            text-shadow: 0 2px 5px rgba(0,0,0,0.45);
        }

        .kpi-subtitle {
            font-size: 11.5px;
            font-weight: 800;
            opacity: 1;
            color: #ffffff;
            margin-top: 6px;
            line-height: 1.25;
            text-shadow: 0 1px 3px rgba(0,0,0,0.45);
        }

        .mini-alert {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 10px 11px;
            background: #ffffff;
            box-shadow: 0px 5px 11px rgba(15, 23, 42, 0.05);
            min-height: 66px;
            margin-bottom: 8px;
        }

        .mini-label {
            color: #334155;
            font-size: 11px;
            font-weight: 800;
            margin-bottom: 4px;
        }

        .mini-value {
            color: #020617;
            font-size: 17px;
            font-weight: 950;
            line-height: 1.22;
        }

        .filter-box {
            padding: 8px 10px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            background: #f8fafc;
            margin-bottom: 8px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 12px;
        }

        .stSelectbox label, .stRadio label {
            font-size: 12px !important;
            font-weight: 800 !important;
        }

        /* reduz espaços verticais do Streamlit */
        div[data-testid="stVerticalBlock"] {
            gap: 0.55rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FUNÇÕES DE TEXTO / FORMATAÇÃO
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


def fmt_num(valor, casas=0):
    if valor is None or pd.isna(valor):
        return "-"
    if casas == 0:
        return f"{int(round(valor)):,}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(valor, casas=1):
    if valor is None or pd.isna(valor):
        return "-"
    return f"{valor:.{casas}f}%".replace(".", ",")


def fmt_horas(valor, casas=1):
    if valor is None or pd.isna(valor):
        return "-"
    return f"{valor:.{casas}f}h".replace(".", ",")


def encurtar(texto, limite=34):
    texto = str(texto)
    if len(texto) <= limite:
        return texto
    return texto[:limite - 3] + "..."


def subtitulo_delta(atual, comp, sufixo="", pp=False, horas=False):
    if comp is None or pd.isna(comp):
        return "Sem comparação"

    diff = atual - comp

    if pp:
        return f"{fmt_pct(comp)} | {diff:+.1f} p.p.".replace(".", ",")

    if horas:
        return f"{fmt_horas(comp)} | {diff:+.1f}h".replace(".", ",")

    if comp != 0:
        var = (diff / comp) * 100
        return f"{fmt_num(comp)} | {diff:+.0f} {sufixo} ({var:+.1f}%)".replace(".", ",")

    return f"{fmt_num(comp)} | {diff:+.0f} {sufixo}".replace(".", ",")


def card(titulo, valor, subtitulo, cor):
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


def alerta(titulo, valor):
    st.markdown(
        f"""
        <div class="mini-alert">
            <div class="mini-label">{titulo}</div>
            <div class="mini-value">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def plot_config():
    return {"displayModeBar": False, "responsive": True}


# ============================================================
# MAPEAMENTO DE COLUNAS
# ============================================================

CANDIDATOS = {
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
        "data criacao", "data de criacao", "inicio", "início"
    ],
    "primeiro_retorno": [
        "1 retorno", "primeiro retorno", "data primeiro retorno",
        "primeira resposta", "1 resposta", "data 1 retorno"
    ],
    "vencimento": [
        "vencimento", "data vencimento", "data de vencimento", "sla vencimento",
        "prazo", "data prazo"
    ],
    "encerramento": [
        "encerramento", "data encerramento", "data de encerramento",
        "finalizado em", "fechado em", "conclusao", "conclusão", "data conclusao"
    ],
    "status": ["status", "estado"],
    "prioridade": ["prioridade", "criticidade", "urgencia", "urgência"],
    "setor": ["setor de atendimento", "setor atendimento", "setor", "area", "área", "departamento", "fila"],
    "responsavel": ["responsavel", "responsável", "atendente", "tecnico", "técnico", "agente", "operador"],
    "tipo": ["tipo", "tipo chamado", "tipo de chamado"],
    "item": ["item", "item chamado", "item de chamado", "servico", "serviço", "produto"],
    "categoria": ["categoria", "categoria chamado", "categoria de chamado"],
    "situacao": ["situacao", "situação"],
    "assunto": ["assunto", "titulo", "título", "descricao", "descrição", "resumo"],
    "avaliacao": ["avaliacao", "avaliação", "nota", "satisfacao", "satisfação"],
    "horas_consumidas": ["horas consumidas", "horas", "tempo consumido", "tempo gasto", "horas gastas"],
}


PADRAO = {
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


def mapear_colunas(df):
    colunas_originais = list(df.columns)
    limpas = {col: limpar_nome_coluna(col) for col in colunas_originais}
    mapa = {}

    for destino, candidatos in CANDIDATOS.items():
        candidatos_limpos = [limpar_nome_coluna(c) for c in candidatos]
        encontrado = None

        for col_original, col_limpa in limpas.items():
            if col_limpa in candidatos_limpos:
                encontrado = col_original
                break

        if encontrado is None:
            for col_original, col_limpa in limpas.items():
                for cand in candidatos_limpos:
                    if cand and (cand in col_limpa or col_limpa in cand):
                        encontrado = col_original
                        break
                if encontrado:
                    break

        mapa[destino] = encontrado

    return mapa


def renomear_padrao(df, mapa):
    renomear = {}

    for destino, origem in mapa.items():
        if origem is not None and origem in df.columns:
            renomear[origem] = PADRAO[destino]

    df = df.rename(columns=renomear)

    for col in PADRAO.values():
        if col not in df.columns:
            df[col] = np.nan

    return df


# ============================================================
# TRATAMENTO DE DATAS / MESES
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
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def extrair_mes_nome_arquivo(nome):
    nome_norm = normalizar_texto(nome)
    ano_match = re.search(r"(20\d{2})", nome_norm)
    ano = int(ano_match.group(1)) if ano_match else None

    mes = None
    for nome_mes, numero in MESES_PT.items():
        if nome_mes in nome_norm:
            mes = numero
            break

    if mes and not ano:
        ano = 2026

    return mes, ano


def to_datetime_safe(serie):
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def padronizar_empresa(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return "Não informado"

    texto_original = str(valor).strip()
    texto_limpo = normalizar_texto(texto_original).upper()

    if "CBLOC" in texto_limpo or "ACBLOC" in texto_limpo:
        return "CBLOC"

    return re.sub(r"\s+", " ", texto_original).title()


def preparar_dataframe(df, nome_arquivo):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    mapa = mapear_colunas(df)
    df = renomear_padrao(df, mapa)
    df["Arquivo_Origem"] = nome_arquivo

    for col in ["Abertura", "Primeiro_Retorno", "Vencimento", "Encerramento"]:
        df[col] = to_datetime_safe(df[col])

    mes_arq, ano_arq = extrair_mes_nome_arquivo(nome_arquivo)

    if df["Abertura"].notna().any():
        df["Ano"] = df["Abertura"].dt.year
        df["Mes"] = df["Abertura"].dt.month
    else:
        df["Ano"] = ano_arq
        df["Mes"] = mes_arq

    if mes_arq and ano_arq:
        df["Mes"] = df["Mes"].fillna(mes_arq)
        df["Ano"] = df["Ano"].fillna(ano_arq)

    df["Ano"] = df["Ano"].fillna(2026).astype(int)
    df["Mes"] = df["Mes"].fillna(1).astype(int)

    df["AnoMesNum"] = df["Ano"] * 100 + df["Mes"]
    df["MesAno"] = df["Mes"].map(MESES_NOME) + "/" + df["Ano"].astype(str)
    df["Empresa_Padronizada"] = df["Empresa"].apply(padronizar_empresa)

    for col in ["Status", "Prioridade", "Setor", "Responsavel", "Tipo", "Item", "Categoria", "Situacao", "Assunto", "Avaliacao"]:
        df[col] = df[col].fillna("Não informado").astype(str).str.strip()
        df[col] = df[col].replace({"": "Não informado"})

    return df, mapa


@st.cache_data(show_spinner=False)
def carregar_dados_excel(lista_arquivos: List[Tuple[str, bytes]]):
    dfs = []
    nomes = []
    mapas = {}

    for nome, conteudo in lista_arquivos:
        nomes.append(nome)

        try:
            bio = BytesIO(conteudo)
            if nome.lower().endswith(".xls"):
                df = pd.read_excel(bio, engine="xlrd")
            else:
                df = pd.read_excel(bio, engine="openpyxl")

            df, mapa = preparar_dataframe(df, nome)
            dfs.append(df)
            mapas[nome] = mapa

        except Exception as e:
            st.error(f"Erro ao ler o arquivo {nome}: {e}")

    if not dfs:
        return pd.DataFrame(), nomes, mapas

    final = pd.concat(dfs, ignore_index=True).dropna(how="all")
    return final, nomes, mapas


def carregar_dados_api(data_inicio: str, data_fim: str):
    """
    Preparado para uso futuro via API, usando somente GET.
    Exemplo: GET /chamados?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD
    """
    return pd.DataFrame()


# ============================================================
# KPIs
# ============================================================

def total_chamados(df):
    if df.empty:
        return 0

    if "ID_Chamado" in df.columns and df["ID_Chamado"].notna().any():
        ids = df["ID_Chamado"].astype(str).str.strip()
        ids = ids[~ids.isin(["", "nan", "None", "Não informado"])]
        if len(ids) > 0:
            return int(ids.nunique())

    return int(len(df))


def calcular_kpis(df):
    if df.empty:
        return {
            "total": 0, "empresas": 0, "encerrados": 0, "pendentes": 0,
            "sla": 0.0, "retorno_1h": 0.0, "resolucao_h": 0.0,
            "criticos": 0, "fora_sla": 0, "sem_avaliacao": 0
        }

    total = total_chamados(df)
    empresas = int(df["Empresa_Padronizada"].replace("Não informado", np.nan).dropna().nunique())

    status_norm = df["Status"].apply(normalizar_texto)
    encerrado_status = status_norm.str.contains("encerr|finaliz|fechad|conclu", na=False, regex=True)
    encerrado_data = df["Encerramento"].notna()
    encerrados_mask = encerrado_data | encerrado_status

    encerrados = int(encerrados_mask.sum())
    pendentes = int(total - encerrados)
    if pendentes < 0:
        pendentes = int((~encerrados_mask).sum())

    tem_venc = df["Vencimento"].notna()
    tem_sla = df["Vencimento"].notna() & df["Encerramento"].notna()
    dentro_sla = int((tem_sla & (df["Encerramento"] <= df["Vencimento"])).sum())
    base_sla = int(tem_venc.sum())
    sla = (dentro_sla / base_sla) * 100 if base_sla > 0 else 0.0

    hoje = pd.Timestamp.today()
    fora_sla = int(
        (
            (df["Vencimento"].notna() & df["Encerramento"].notna() & (df["Encerramento"] > df["Vencimento"]))
            |
            (df["Vencimento"].notna() & df["Encerramento"].isna() & (df["Vencimento"] < hoje))
        ).sum()
    )

    tem_retorno = df["Abertura"].notna() & df["Primeiro_Retorno"].notna()
    diff_retorno_min = (df["Primeiro_Retorno"] - df["Abertura"]).dt.total_seconds() / 60
    retorno_1h_count = int((tem_retorno & (diff_retorno_min <= 60) & (diff_retorno_min >= 0)).sum())
    base_retorno = int(tem_retorno.sum())
    retorno_1h = (retorno_1h_count / base_retorno) * 100 if base_retorno > 0 else 0.0

    tem_resolucao = df["Abertura"].notna() & df["Encerramento"].notna()
    diff_res_h = (df["Encerramento"] - df["Abertura"]).dt.total_seconds() / 3600
    diff_res_h = diff_res_h[tem_resolucao & (diff_res_h >= 0)]
    resolucao_h = float(diff_res_h.mean()) if len(diff_res_h) > 0 else 0.0

    prioridade_norm = df["Prioridade"].apply(normalizar_texto)
    criticos = int(prioridade_norm.str.contains("critic", na=False).sum())

    aval_norm = df["Avaliacao"].astype(str).apply(normalizar_texto)
    sem_avaliacao = int(
        (
            aval_norm.isin(["", "nan", "none", "nao informado", "n/a", "na", "sem avaliacao"])
            | aval_norm.str.contains("sem avaliacao", na=False)
        ).sum()
    )

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


def meses_ordenados(df):
    return (
        df[["MesAno", "AnoMesNum"]]
        .drop_duplicates()
        .sort_values("AnoMesNum")["MesAno"]
        .tolist()
    )


def mes_anterior(df, mes_principal):
    meses = df[["MesAno", "AnoMesNum"]].drop_duplicates().sort_values("AnoMesNum")
    if mes_principal not in meses["MesAno"].values:
        return None

    atual = int(meses.loc[meses["MesAno"] == mes_principal, "AnoMesNum"].iloc[0])
    anteriores = meses[meses["AnoMesNum"] < atual]
    if anteriores.empty:
        return None

    return anteriores.iloc[-1]["MesAno"]


def ranking_clientes_aumento(df_principal, df_comp):
    atual = df_principal.groupby("Empresa_Padronizada").size().reset_index(name="Chamados_Mes_Principal")
    comp = df_comp.groupby("Empresa_Padronizada").size().reset_index(name="Chamados_Mes_Comparado")

    ranking = pd.merge(atual, comp, on="Empresa_Padronizada", how="outer").fillna(0)
    ranking["Chamados_Mes_Principal"] = ranking["Chamados_Mes_Principal"].astype(int)
    ranking["Chamados_Mes_Comparado"] = ranking["Chamados_Mes_Comparado"].astype(int)
    ranking["Diferenca"] = ranking["Chamados_Mes_Principal"] - ranking["Chamados_Mes_Comparado"]
    ranking["Variacao_%"] = np.where(
        ranking["Chamados_Mes_Comparado"] > 0,
        (ranking["Diferenca"] / ranking["Chamados_Mes_Comparado"]) * 100,
        np.nan
    )

    return ranking.sort_values(["Diferenca", "Variacao_%"], ascending=[False, False])


# ============================================================
# GRÁFICOS COMPACTOS
# ============================================================

def layout_compacto(fig, altura=245):
    fig.update_layout(
        height=altura,
        margin=dict(l=8, r=10, t=38, b=20),
        font=dict(size=10, color="#020617"),
        title_font=dict(size=13, color="#020617"),
        legend=dict(font=dict(size=9, color="#020617")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            tickfont=dict(size=10, color="#020617"),
            title_font=dict(size=11, color="#020617"),
            gridcolor="#dbe3ef",
            zerolinecolor="#cbd5e1",
        ),
        yaxis=dict(
            tickfont=dict(size=10, color="#020617"),
            title_font=dict(size=11, color="#020617"),
            gridcolor="#dbe3ef",
            zerolinecolor="#cbd5e1",
        ),
    )
    return fig


def grafico_resumo(kpis, mes):
    dados = pd.DataFrame({
        "Indicador": ["Chamados", "Encerrados", "Críticos", "Pendentes"],
        "Quantidade": [kpis["total"], kpis["encerrados"], kpis["criticos"], kpis["pendentes"]],
    })
    fig = px.bar(dados, x="Indicador", y="Quantidade", text="Quantidade", title=f"Resumo — {mes}")
    fig.update_traces(textposition="outside", textfont=dict(color="#020617", size=11))
    fig.update_layout(showlegend=False)
    return layout_compacto(fig, 230)


def grafico_resumo_comp(k1, k0, m1, m0):
    dados = pd.DataFrame({
        "Indicador": ["Chamados", "Encerrados", "Críticos", "Pendentes"] * 2,
        "Mês": [m0] * 4 + [m1] * 4,
        "Quantidade": [
            k0["total"], k0["encerrados"], k0["criticos"], k0["pendentes"],
            k1["total"], k1["encerrados"], k1["criticos"], k1["pendentes"],
        ],
    })
    fig = px.bar(dados, x="Indicador", y="Quantidade", color="Mês", barmode="group", text="Quantidade", title=f"Resumo — {m1} x {m0}")
    fig.update_traces(textposition="outside", textfont=dict(color="#020617", size=11))
    return layout_compacto(fig, 230)


def grafico_qualidade(kpis, mes):
    dados = pd.DataFrame({
        "Indicador": ["SLA", "1º retorno"],
        "Percentual": [kpis["sla"], kpis["retorno_1h"]],
    })
    fig = px.bar(dados, x="Indicador", y="Percentual", text=dados["Percentual"].map(lambda x: f"{x:.1f}%"), title=f"Qualidade — {mes}")
    fig.update_traces(textposition="outside", textfont=dict(color="#020617", size=11))
    fig.update_yaxes(range=[0, 100])
    return layout_compacto(fig, 215)


def grafico_qualidade_comp(k1, k0, m1, m0):
    dados = pd.DataFrame({
        "Indicador": ["SLA", "1º retorno"] * 2,
        "Mês": [m0, m0, m1, m1],
        "Percentual": [k0["sla"], k0["retorno_1h"], k1["sla"], k1["retorno_1h"]],
    })
    fig = px.bar(dados, x="Indicador", y="Percentual", color="Mês", barmode="group", text=dados["Percentual"].map(lambda x: f"{x:.1f}%"), title=f"Qualidade — {m1} x {m0}")
    fig.update_traces(textposition="outside", textfont=dict(color="#020617", size=11))
    fig.update_yaxes(range=[0, 100])
    return layout_compacto(fig, 215)


def grafico_evolucao(df):
    mensal = df.groupby(["AnoMesNum", "MesAno"]).size().reset_index(name="Chamados").sort_values("AnoMesNum")
    fig = px.line(mensal, x="MesAno", y="Chamados", markers=True, title="Evolução mensal")
    return layout_compacto(fig, 235)


def grafico_top(df, coluna, titulo, top=5, altura=240):
    if df.empty or coluna not in df.columns:
        return go.Figure()

    dados = df.groupby(coluna).size().reset_index(name="Chamados").sort_values("Chamados", ascending=False).head(top)
    dados["Categoria"] = dados[coluna].apply(lambda x: encurtar(x, 31))

    fig = px.bar(dados, x="Chamados", y="Categoria", orientation="h", text="Chamados", title=titulo)
    fig.update_traces(textposition="inside", textfont=dict(color="#ffffff", size=11))
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, yaxis_title="", xaxis_title="Chamados", showlegend=False)
    return layout_compacto(fig, altura)


def grafico_prioridade(df, titulo):
    if df.empty:
        return go.Figure()

    dados = df.groupby("Prioridade").size().reset_index(name="Chamados").sort_values("Chamados", ascending=False)
    fig = px.pie(dados, values="Chamados", names="Prioridade", title=titulo, hole=0.45)
    fig.update_traces(textfont=dict(color="#020617", size=11))
    return layout_compacto(fig, 235)


def grafico_comp_categoria(df_principal, df_comp, coluna, mes_principal, mes_comparacao, titulo, top=5, altura=250):
    atual = df_principal.groupby(coluna).size().reset_index(name=mes_principal)
    comp = df_comp.groupby(coluna).size().reset_index(name=mes_comparacao)

    dados = pd.merge(comp, atual, on=coluna, how="outer").fillna(0)
    dados[mes_principal] = dados[mes_principal].astype(int)
    dados[mes_comparacao] = dados[mes_comparacao].astype(int)
    dados["Total"] = dados[mes_principal] + dados[mes_comparacao]
    dados = dados.sort_values("Total", ascending=False).head(top).copy()
    dados["Categoria"] = dados[coluna].apply(lambda x: encurtar(x, 31))

    melt = dados.melt(
        id_vars=["Categoria"],
        value_vars=[mes_comparacao, mes_principal],
        var_name="Mês",
        value_name="Chamados"
    )

    fig = px.bar(melt, x="Chamados", y="Categoria", color="Mês", barmode="group", orientation="h", text="Chamados", title=titulo)
    fig.update_traces(textposition="outside", textfont=dict(color="#020617", size=11))
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, yaxis_title="", xaxis_title="Chamados", legend_title_text="")
    return layout_compacto(fig, altura)


def tabela_aumentos(df_principal, df_comp, mes_principal, mes_comparacao, n=6):
    ranking = ranking_clientes_aumento(df_principal, df_comp)
    pos = ranking[ranking["Diferenca"] > 0].copy().head(n)

    if pos.empty:
        return pd.DataFrame(), ranking

    tabela = pos.copy()
    tabela["Variação"] = tabela.apply(
        lambda row: f"Sem chamados em {mes_comparacao}"
        if row["Chamados_Mes_Comparado"] == 0 and row["Chamados_Mes_Principal"] > 0
        else f"{row['Variacao_%']:.1f}%".replace(".", ",")
        if not pd.isna(row["Variacao_%"])
        else "Sem base",
        axis=1
    )

    tabela = tabela.rename(columns={
        "Empresa_Padronizada": "Empresa",
        "Chamados_Mes_Comparado": mes_comparacao,
        "Chamados_Mes_Principal": mes_principal,
        "Diferenca": "Aumento",
    })

    return tabela[["Empresa", mes_comparacao, mes_principal, "Aumento", "Variação"]], ranking


# ============================================================
# INTERFACE
# ============================================================

st.markdown(
    f"""
    <div class="top-header">
        <h1>📊 Dashboard CEO — Suporte / Help Desk</h1>
        <p>Chamados, SLA, primeiro retorno, clientes críticos e evolução mensal.</p>
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
df, arquivos_carregados, mapas_colunas = carregar_dados_excel(lista_arquivos)

if df.empty:
    st.error("Nenhum dado válido foi carregado. Verifique os arquivos enviados.")
    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("### ℹ️ Dataset")
st.sidebar.write(f"**Arquivos enviados:** {len(arquivos_carregados)}")
for arq in arquivos_carregados:
    st.sidebar.write(f"- `{arq}`")
st.sidebar.write(f"**Total de linhas:** {len(df)}")

with st.sidebar.expander("📋 Colunas mapeadas"):
    for arquivo, mapa in mapas_colunas.items():
        st.write(f"**{arquivo}**")
        st.json({destino: origem if origem is not None else "Não encontrada" for destino, origem in mapa.items()})


# ============================================================
# FILTROS PRINCIPAIS
# ============================================================

meses = meses_ordenados(df)

f1, f2, f3, f4, f5 = st.columns([1.15, 1.2, 1.2, 1.55, 1.35])

with f1:
    modo = st.radio("Modo", ["Único mês", "Comparação"], index=0, horizontal=True)

with f2:
    mes_principal = st.selectbox("Mês principal", meses, index=len(meses) - 1)

sug = mes_anterior(df, mes_principal)
index_comp = meses.index(sug) if sug in meses else 0

with f3:
    if modo == "Comparação":
        mes_comparacao = st.selectbox("Comparar com", meses, index=index_comp)
    else:
        mes_comparacao = None
        st.info("Sem comparação")

empresas = ["Todas"] + sorted(df["Empresa_Padronizada"].dropna().unique().tolist())
setores = ["Todos"] + sorted(df["Setor"].dropna().unique().tolist())

with f4:
    empresa_sel = st.selectbox("Empresa", empresas)

with f5:
    setor_sel = st.selectbox("Setor", setores)


st.sidebar.header("🎛️ Filtros adicionais")

responsaveis = ["Todos"] + sorted(df["Responsavel"].dropna().unique().tolist())
prioridades = ["Todas"] + sorted(df["Prioridade"].dropna().unique().tolist())
status_lista = ["Todos"] + sorted(df["Status"].dropna().unique().tolist())

resp_sel = st.sidebar.selectbox("Responsável", responsaveis)
prioridade_sel = st.sidebar.selectbox("Prioridade", prioridades)
status_sel = st.sidebar.selectbox("Status", status_lista)


def aplicar_filtros(df_base):
    df_f = df_base.copy()

    if empresa_sel != "Todas":
        df_f = df_f[df_f["Empresa_Padronizada"] == empresa_sel]
    if setor_sel != "Todos":
        df_f = df_f[df_f["Setor"] == setor_sel]
    if resp_sel != "Todos":
        df_f = df_f[df_f["Responsavel"] == resp_sel]
    if prioridade_sel != "Todas":
        df_f = df_f[df_f["Prioridade"] == prioridade_sel]
    if status_sel != "Todos":
        df_f = df_f[df_f["Status"] == status_sel]

    return df_f


df_base = aplicar_filtros(df)

df_principal = df_base[df_base["MesAno"].astype(str) == str(mes_principal)].copy()
kpi_princ = calcular_kpis(df_principal)

df_comp = pd.DataFrame()
kpi_comp = None

if modo == "Comparação":
    df_comp = df_base[df_base["MesAno"].astype(str) == str(mes_comparacao)].copy()
    kpi_comp = calcular_kpis(df_comp)
    if mes_comparacao == mes_principal:
        st.warning("O mês de comparação é igual ao mês principal. Escolha meses diferentes.")


# ============================================================
# KPIs
# ============================================================

titulo_kpi = f"📌 KPIs — {mes_principal}" if modo == "Único mês" else f"📌 KPIs — {mes_principal} x {mes_comparacao}"
st.markdown(f'<div class="section-title">{titulo_kpi}</div><div class="section-line"></div>', unsafe_allow_html=True)

cores = [
    "linear-gradient(135deg, #1d4ed8, #6d28d9)",
    "linear-gradient(135deg, #6d28d9, #4338ca)",
    "linear-gradient(135deg, #047857, #10b981)",
    "linear-gradient(135deg, #b45309, #f59e0b)",
    "linear-gradient(135deg, #0f766e, #14b8a6)",
    "linear-gradient(135deg, #172554, #1e293b)",
    "linear-gradient(135deg, #dc2626, #ea580c)",
    "linear-gradient(135deg, #be123c, #dc2626)",
]

if modo == "Único mês":
    cards = [
        ("Chamados", fmt_num(kpi_princ["total"]), "Volume do mês"),
        ("Empresas", fmt_num(kpi_princ["empresas"]), "Clientes atendidos"),
        ("Encerrados", fmt_num(kpi_princ["encerrados"]), "Finalizados"),
        ("Pendentes", fmt_num(kpi_princ["pendentes"]), "Abertos/sem fim"),
        ("SLA", fmt_pct(kpi_princ["sla"]), "Dentro do prazo"),
        ("1º retorno", fmt_pct(kpi_princ["retorno_1h"]), "Até 1 hora"),
        ("Resolução", fmt_horas(kpi_princ["resolucao_h"]), "Tempo médio"),
        ("Críticos", fmt_num(kpi_princ["criticos"]), "Risco operacional"),
    ]
else:
    cards = [
        ("Chamados", fmt_num(kpi_princ["total"]), subtitulo_delta(kpi_princ["total"], kpi_comp["total"], "chamados")),
        ("Empresas", fmt_num(kpi_princ["empresas"]), subtitulo_delta(kpi_princ["empresas"], kpi_comp["empresas"], "empresas")),
        ("Encerrados", fmt_num(kpi_princ["encerrados"]), subtitulo_delta(kpi_princ["encerrados"], kpi_comp["encerrados"], "encerrados")),
        ("Pendentes", fmt_num(kpi_princ["pendentes"]), subtitulo_delta(kpi_princ["pendentes"], kpi_comp["pendentes"], "pendentes")),
        ("SLA", fmt_pct(kpi_princ["sla"]), subtitulo_delta(kpi_princ["sla"], kpi_comp["sla"], pp=True)),
        ("1º retorno", fmt_pct(kpi_princ["retorno_1h"]), subtitulo_delta(kpi_princ["retorno_1h"], kpi_comp["retorno_1h"], pp=True)),
        ("Resolução", fmt_horas(kpi_princ["resolucao_h"]), subtitulo_delta(kpi_princ["resolucao_h"], kpi_comp["resolucao_h"], horas=True)),
        ("Críticos", fmt_num(kpi_princ["criticos"]), subtitulo_delta(kpi_princ["criticos"], kpi_comp["criticos"], "críticos")),
    ]

row1 = st.columns(4)
for i in range(4):
    with row1[i]:
        card(cards[i][0], cards[i][1], cards[i][2], cores[i])

row2 = st.columns(4)
for i in range(4, 8):
    with row2[i - 4]:
        card(cards[i][0], cards[i][1], cards[i][2], cores[i])


# ============================================================
# PAINEL EXECUTIVO COMPACTO
# ============================================================

st.markdown('<div class="section-title">📊 Painel Executivo Compacto</div><div class="section-line"></div>', unsafe_allow_html=True)

col_esq, col_meio, col_dir = st.columns([1.15, 1.45, 1.15])

with col_esq:
    if modo == "Único mês":
        st.plotly_chart(grafico_resumo(kpi_princ, mes_principal), use_container_width=True, config=plot_config())
        st.plotly_chart(grafico_qualidade(kpi_princ, mes_principal), use_container_width=True, config=plot_config())
    else:
        st.plotly_chart(grafico_resumo_comp(kpi_princ, kpi_comp, mes_principal, mes_comparacao), use_container_width=True, config=plot_config())
        st.plotly_chart(grafico_qualidade_comp(kpi_princ, kpi_comp, mes_principal, mes_comparacao), use_container_width=True, config=plot_config())

with col_meio:
    st.plotly_chart(grafico_evolucao(df_base), use_container_width=True, config=plot_config())

    if modo == "Comparação":
        tabela_inc, ranking_total = tabela_aumentos(df_principal, df_comp, mes_principal, mes_comparacao, n=6)
        st.markdown("**🚨 Clientes com maior aumento**")
        if tabela_inc.empty:
            st.info("Nenhum cliente apresentou aumento de chamados.")
            ranking_total = pd.DataFrame()
        else:
            st.dataframe(tabela_inc, use_container_width=True, hide_index=True, height=240)
    else:
        st.plotly_chart(
            grafico_top(df_principal, "Empresa_Padronizada", f"Top 5 clientes — {mes_principal}", top=5, altura=240),
            use_container_width=True,
            config=plot_config(),
        )

with col_dir:
    if modo == "Único mês":
        st.plotly_chart(grafico_prioridade(df_principal, f"Prioridade — {mes_principal}"), use_container_width=True, config=plot_config())
    else:
        st.plotly_chart(
            grafico_comp_categoria(df_principal, df_comp, "Prioridade", mes_principal, mes_comparacao, f"Prioridade — {mes_principal} x {mes_comparacao}", top=5, altura=235),
            use_container_width=True,
            config=plot_config(),
        )

    st.markdown("**⚠️ Alertas executivos**")
    alerta("Críticos", fmt_num(kpi_princ["criticos"]))
    alerta("Pendentes", fmt_num(kpi_princ["pendentes"]))
    alerta("Fora do SLA", fmt_num(kpi_princ["fora_sla"]))
    alerta("1º retorno ≤ 1h", fmt_pct(kpi_princ["retorno_1h"]))


# ============================================================
# OPERAÇÃO COMPACTA
# ============================================================

st.markdown('<div class="section-title">🏢 Operação, clientes e motivos</div><div class="section-line"></div>', unsafe_allow_html=True)

op1, op2, op3 = st.columns(3)

if modo == "Único mês":
    with op1:
        st.plotly_chart(grafico_top(df_principal, "Setor", f"Top setores — {mes_principal}", top=5, altura=260), use_container_width=True, config=plot_config())
    with op2:
        st.plotly_chart(grafico_top(df_principal, "Tipo", f"Top motivos/tipos — {mes_principal}", top=5, altura=260), use_container_width=True, config=plot_config())
    with op3:
        st.plotly_chart(grafico_top(df_principal, "Empresa_Padronizada", f"Top clientes — {mes_principal}", top=5, altura=260), use_container_width=True, config=plot_config())

else:
    with op1:
        st.plotly_chart(
            grafico_comp_categoria(df_principal, df_comp, "Setor", mes_principal, mes_comparacao, f"Setores — {mes_principal} x {mes_comparacao}", top=5, altura=265),
            use_container_width=True,
            config=plot_config(),
        )
    with op2:
        st.plotly_chart(
            grafico_comp_categoria(df_principal, df_comp, "Tipo", mes_principal, mes_comparacao, f"Motivos/tipos — {mes_principal} x {mes_comparacao}", top=5, altura=265),
            use_container_width=True,
            config=plot_config(),
        )
    with op3:
        st.plotly_chart(
            grafico_comp_categoria(df_principal, df_comp, "Empresa_Padronizada", mes_principal, mes_comparacao, f"Clientes — {mes_principal} x {mes_comparacao}", top=5, altura=265),
            use_container_width=True,
            config=plot_config(),
        )


# ============================================================
# LEITURA COMPARATIVA
# ============================================================

if modo == "Comparação":
    st.markdown('<div class="section-title">🔎 Leitura comparativa</div><div class="section-line"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    ranking = ranking_clientes_aumento(df_principal, df_comp)
    ranking_pos = ranking[ranking["Diferenca"] > 0].copy()

    with c1:
        if not ranking_pos.empty:
            top_cli = ranking_pos.iloc[0]
            if top_cli["Chamados_Mes_Comparado"] == 0:
                var_txt = f"sem %: {mes_comparacao} teve 0 chamados"
            elif not pd.isna(top_cli["Variacao_%"]):
                var_txt = f"{top_cli['Variacao_%']:.1f}%".replace(".", ",")
            else:
                var_txt = "sem base"

            alerta(
                f"Maior aumento vs {mes_comparacao}",
                f"{top_cli['Empresa_Padronizada']}<br>"
                f"{mes_comparacao}: {int(top_cli['Chamados_Mes_Comparado'])} | "
                f"{mes_principal}: {int(top_cli['Chamados_Mes_Principal'])}<br>"
                f"+{int(top_cli['Diferenca'])} chamados ({var_txt})"
            )
        else:
            alerta("Maior aumento", "Sem aumento relevante")

    with c2:
        cbloc = ranking[ranking["Empresa_Padronizada"] == "CBLOC"]
        if not cbloc.empty:
            cbloc_row = cbloc.iloc[0]
            if cbloc_row["Diferenca"] > 0:
                if cbloc_row["Chamados_Mes_Comparado"] == 0:
                    var_txt = f"sem %: {mes_comparacao} teve 0 chamados"
                elif not pd.isna(cbloc_row["Variacao_%"]):
                    var_txt = f"{cbloc_row['Variacao_%']:.1f}%".replace(".", ",")
                else:
                    var_txt = "sem base"

                alerta(
                    f"CBLOC vs {mes_comparacao}",
                    f"{mes_comparacao}: {int(cbloc_row['Chamados_Mes_Comparado'])} | "
                    f"{mes_principal}: {int(cbloc_row['Chamados_Mes_Principal'])}<br>"
                    f"+{int(cbloc_row['Diferenca'])} chamados ({var_txt})"
                )
            else:
                alerta("CBLOC", "Sem aumento no período")
        else:
            alerta("CBLOC", "Não apareceu no período")

    with c3:
        delta_sla = kpi_princ["sla"] - kpi_comp["sla"]
        delta_ret = kpi_princ["retorno_1h"] - kpi_comp["retorno_1h"]
        alerta(
            "Qualidade vs mês comparado",
            f"SLA: {delta_sla:+.1f} p.p.<br>1º retorno: {delta_ret:+.1f} p.p.".replace(".", ",")
        )


# ============================================================
# CONFERÊNCIA
# ============================================================

with st.expander("🧪 Conferência por mês"):
    conf = df_base.groupby(["AnoMesNum", "MesAno"]).size().reset_index(name="Linhas").sort_values("AnoMesNum")
    st.dataframe(conf[["MesAno", "Linhas"]], use_container_width=True)
    st.write("Modo selecionado:", modo)
    st.write("Mês principal:", mes_principal)
    st.write("Linhas do mês principal:", len(df_principal))

    if modo == "Comparação":
        st.write("Mês de comparação:", mes_comparacao)
        st.write("Linhas do mês de comparação:", len(df_comp))

with st.expander("🔎 Ver amostra dos dados tratados"):
    st.dataframe(df_base.head(100), use_container_width=True)

st.caption("Dashboard preparado para Excel via upload e futura integração com API usando somente GET.")
