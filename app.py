import re
import unicodedata
from io import BytesIO
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Dashboard CEO — Suporte / Help Desk",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
.title-box {background: linear-gradient(135deg,#111827,#1f2937); padding: 25px 30px; border-radius: 18px; color: white; margin-bottom: 18px;}
.title-box h1 {margin:0; font-size:32px;}
.title-box p {margin-top:8px; color:#d1d5db; font-size:16px;}
.kpi-card {padding:20px; border-radius:18px; color:white; min-height:142px; box-shadow:0 10px 25px rgba(15,23,42,.16);}
.kpi-title {font-size:12px; font-weight:800; letter-spacing:.7px; text-transform:uppercase; opacity:.92;}
.kpi-value {font-size:34px; font-weight:900; margin-top:10px; line-height:1.1;}
.kpi-subtitle {font-size:13px; opacity:.95; margin-top:9px; line-height:1.35;}
.section-title {font-size:24px; font-weight:900; color:#0f172a; margin-top:28px; margin-bottom:8px;}
.section-line {width:185px; height:4px; border-radius:99px; background:#64748b; margin-bottom:18px;}
.alert-box {border:1px solid #e5e7eb; border-radius:16px; padding:18px; background:#fff; box-shadow:0 6px 16px rgba(15,23,42,.06); min-height:95px;}
.small-muted {color:#64748b; font-size:13px;}
</style>
""", unsafe_allow_html=True)


def normalizar_texto(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return texto.lower()


def limpar_coluna(coluna: str) -> str:
    col = normalizar_texto(coluna)
    col = col.replace("º", "").replace("°", "")
    col = re.sub(r"[^a-z0-9 ]", " ", col)
    return re.sub(r"\s+", " ", col).strip()


def fmt_num(v):
    if v is None or pd.isna(v):
        return "-"
    return f"{int(round(v)):,}".replace(",", ".")


def fmt_pct(v):
    if v is None or pd.isna(v):
        return "-"
    return f"{v:.1f}%".replace(".", ",")


def fmt_h(v):
    if v is None or pd.isna(v):
        return "-"
    return f"{v:.1f}h".replace(".", ",")


def delta_texto(atual, comp, tipo="num"):
    if comp is None or pd.isna(comp):
        return "Sem comparação"
    diff = atual - comp
    if tipo == "pp":
        return f"Comparado: {fmt_pct(comp)} | {diff:+.1f} p.p.".replace(".", ",")
    if tipo == "h":
        return f"Comparado: {fmt_h(comp)} | {diff:+.1f}h".replace(".", ",")
    if comp != 0:
        var = diff / comp * 100
        return f"Comparado: {fmt_num(comp)} | {diff:+.0f} ({var:+.1f}%)".replace(".", ",")
    return f"Comparado: {fmt_num(comp)} | {diff:+.0f}".replace(".", ",")


def card(titulo, valor, subtitulo, cor):
    st.markdown(f"""
    <div class="kpi-card" style="background:{cor};">
        <div class="kpi-title">{titulo}</div>
        <div class="kpi-value">{valor}</div>
        <div class="kpi-subtitle">{subtitulo}</div>
    </div>
    """, unsafe_allow_html=True)


CANDIDATOS = {
    "id": ["solicitacao", "solicitacao codigo", "codigo", "protocolo", "ticket", "id", "numero chamado", "chamado"],
    "empresa": ["empresa", "cliente", "razao social", "nome empresa", "nome do cliente"],
    "abertura": ["abertura", "data abertura", "data de abertura", "criado em", "data criacao", "inicio"],
    "retorno": ["1 retorno", "primeiro retorno", "data primeiro retorno", "primeira resposta", "1 resposta"],
    "vencimento": ["vencimento", "data vencimento", "data de vencimento", "sla vencimento", "prazo"],
    "encerramento": ["encerramento", "data encerramento", "data de encerramento", "finalizado em", "fechado em", "conclusao"],
    "status": ["status", "estado"],
    "prioridade": ["prioridade", "criticidade", "urgencia"],
    "setor": ["setor de atendimento", "setor atendimento", "setor", "area", "departamento", "fila"],
    "responsavel": ["responsavel", "atendente", "tecnico", "agente", "operador"],
    "tipo": ["tipo", "tipo chamado", "tipo de chamado"],
    "item": ["item", "item chamado", "servico", "produto"],
    "categoria": ["categoria"],
    "situacao": ["situacao", "situação"],
    "assunto": ["assunto", "titulo", "descricao", "resumo"],
    "avaliacao": ["avaliacao", "avaliação", "nota", "satisfacao", "satisfação"],
    "horas": ["horas consumidas", "horas", "tempo consumido", "tempo gasto"],
}

PADRAO = {
    "id": "ID_Chamado",
    "empresa": "Empresa",
    "abertura": "Abertura",
    "retorno": "Primeiro_Retorno",
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
    "horas": "Horas_Consumidas",
}

MESES_PT = {
    "janeiro": 1, "jan": 1, "fevereiro": 2, "fev": 2, "marco": 3, "março": 3, "mar": 3,
    "abril": 4, "abr": 4, "maio": 5, "mai": 5, "junho": 6, "jun": 6, "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8, "setembro": 9, "set": 9, "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11, "dezembro": 12, "dez": 12,
}
MESES_NOME = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}


def achar_coluna(df, candidatos):
    limpas = {c: limpar_coluna(c) for c in df.columns}
    cands = [limpar_coluna(c) for c in candidatos]
    for original, limpa in limpas.items():
        if limpa in cands:
            return original
    for original, limpa in limpas.items():
        for cand in cands:
            if cand and (cand in limpa or limpa in cand):
                return original
    return None


def mapear_colunas(df):
    mapa = {k: achar_coluna(df, v) for k, v in CANDIDATOS.items()}
    return mapa


def mes_do_nome(nome) -> Tuple[Optional[int], Optional[int]]:
    nome_norm = normalizar_texto(nome)
    ano_match = re.search(r"(20\d{2})", nome_norm)
    ano = int(ano_match.group(1)) if ano_match else None
    mes = None
    for nome_mes, num in MESES_PT.items():
        if nome_mes in nome_norm:
            mes = num
            break
    if mes and not ano:
        ano = 2026
    return mes, ano


def padronizar_empresa(v):
    if pd.isna(v) or str(v).strip() == "":
        return "Não informado"
    original = re.sub(r"\s+", " ", str(v).strip())
    upper = normalizar_texto(original).upper()
    if "CBLOC" in upper or "ACBLOC" in upper:
        return "CBLOC"
    return original.title()


def preparar_df(df, nome_arquivo):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    mapa = mapear_colunas(df)
    ren = {origem: PADRAO[k] for k, origem in mapa.items() if origem is not None and origem in df.columns}
    df = df.rename(columns=ren)
    for col in PADRAO.values():
        if col not in df.columns:
            df[col] = np.nan
    df["Arquivo_Origem"] = nome_arquivo
    for col in ["Abertura", "Primeiro_Retorno", "Vencimento", "Encerramento"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    if df["Abertura"].notna().any():
        df["Ano"] = df["Abertura"].dt.year
        df["Mes"] = df["Abertura"].dt.month
    else:
        mes, ano = mes_do_nome(nome_arquivo)
        df["Ano"] = ano
        df["Mes"] = mes
    mes_nome, ano_nome = mes_do_nome(nome_arquivo)
    if mes_nome and ano_nome:
        df["Mes"] = df["Mes"].fillna(mes_nome)
        df["Ano"] = df["Ano"].fillna(ano_nome)
    df["Ano"] = df["Ano"].fillna(2026).astype(int)
    df["Mes"] = df["Mes"].fillna(1).astype(int)
    df["AnoMesNum"] = df["Ano"] * 100 + df["Mes"]
    df["MesAno"] = df["Mes"].map(MESES_NOME) + "/" + df["Ano"].astype(str)
    df["Empresa_Padronizada"] = df["Empresa"].apply(padronizar_empresa)
    for col in ["Status", "Prioridade", "Setor", "Responsavel", "Tipo", "Item", "Categoria", "Situacao", "Assunto", "Avaliacao"]:
        df[col] = df[col].fillna("Não informado").astype(str).str.strip().replace({"": "Não informado"})
    return df, mapa


def carregar_dados_excel(uploaded_files):
    dfs = []
    arquivos = []
    mapas = {}
    for up in uploaded_files:
        nome = up.name
        arquivos.append(nome)
        try:
            data = up.read()
            bio = BytesIO(data)
            engine = "xlrd" if nome.lower().endswith(".xls") else "openpyxl"
            bruto = pd.read_excel(bio, engine=engine)
            tratado, mapa = preparar_df(bruto, nome)
            dfs.append(tratado)
            mapas[nome] = mapa
        except Exception as e:
            st.error(f"Erro ao ler {nome}: {e}")
    if not dfs:
        return pd.DataFrame(), arquivos, mapas
    return pd.concat(dfs, ignore_index=True).dropna(how="all"), arquivos, mapas


def carregar_dados_api(data_inicio: str, data_fim: str):
    """Preparado para uso futuro. Usar apenas GET: /chamados?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD"""
    import requests
    return pd.DataFrame()


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
        return {"total": 0, "empresas": 0, "encerrados": 0, "pendentes": 0, "sla": 0.0, "retorno_1h": 0.0, "resolucao_h": 0.0, "criticos": 0, "fora_sla": 0, "sem_avaliacao": 0}
    total = total_chamados(df)
    empresas = int(df["Empresa_Padronizada"].replace("Não informado", np.nan).dropna().nunique())
    status = df["Status"].apply(normalizar_texto)
    encerrados_mask = df["Encerramento"].notna() | status.str.contains("encerr|finaliz|fechad|conclu", na=False)
    encerrados = int(encerrados_mask.sum())
    pendentes = max(int(total - encerrados), 0)
    base_sla = int(df["Vencimento"].notna().sum())
    dentro_sla = int((df["Vencimento"].notna() & df["Encerramento"].notna() & (df["Encerramento"] <= df["Vencimento"])).sum())
    sla = dentro_sla / base_sla * 100 if base_sla else 0.0
    hoje = pd.Timestamp.today()
    fora_sla = int(((df["Vencimento"].notna() & df["Encerramento"].notna() & (df["Encerramento"] > df["Vencimento"])) | (df["Vencimento"].notna() & df["Encerramento"].isna() & (df["Vencimento"] < hoje))).sum())
    tem_ret = df["Abertura"].notna() & df["Primeiro_Retorno"].notna()
    ret_min = (df["Primeiro_Retorno"] - df["Abertura"]).dt.total_seconds() / 60
    retorno_1h = int((tem_ret & (ret_min >= 0) & (ret_min <= 60)).sum()) / int(tem_ret.sum()) * 100 if int(tem_ret.sum()) else 0.0
    tem_res = df["Abertura"].notna() & df["Encerramento"].notna()
    res_h = (df["Encerramento"] - df["Abertura"]).dt.total_seconds() / 3600
    res_h = res_h[tem_res & (res_h >= 0)]
    resolucao_h = float(res_h.mean()) if len(res_h) else 0.0
    criticos = int(df["Prioridade"].apply(normalizar_texto).str.contains("critic", na=False).sum())
    aval_norm = df["Avaliacao"].astype(str).apply(normalizar_texto)
    sem_avaliacao = int((aval_norm.isin(["", "nan", "none", "nao informado", "n/a", "na", "sem avaliacao"]) | aval_norm.str.contains("sem avaliacao", na=False)).sum())
    return {"total": total, "empresas": empresas, "encerrados": encerrados, "pendentes": pendentes, "sla": float(sla), "retorno_1h": float(retorno_1h), "resolucao_h": float(resolucao_h), "criticos": criticos, "fora_sla": fora_sla, "sem_avaliacao": sem_avaliacao}


def meses_ordenados(df):
    return df[["MesAno", "AnoMesNum"]].drop_duplicates().sort_values("AnoMesNum")["MesAno"].tolist()


def mes_anterior(df, mes_principal):
    tab = df[["MesAno", "AnoMesNum"]].drop_duplicates().sort_values("AnoMesNum")
    if mes_principal not in tab["MesAno"].values:
        return None
    atual = int(tab.loc[tab["MesAno"] == mes_principal, "AnoMesNum"].iloc[0])
    ants = tab[tab["AnoMesNum"] < atual]
    return None if ants.empty else ants.iloc[-1]["MesAno"]


def filtrar_mes(df, mes):
    return df[df["MesAno"] == mes].copy()


def ranking_aumento(df_principal, df_comp):
    atual = df_principal.groupby("Empresa_Padronizada").size().reset_index(name="Chamados_Mes_Principal")
    comp = df_comp.groupby("Empresa_Padronizada").size().reset_index(name="Chamados_Mes_Comparado")
    r = pd.merge(atual, comp, on="Empresa_Padronizada", how="outer").fillna(0)
    r["Chamados_Mes_Principal"] = r["Chamados_Mes_Principal"].astype(int)
    r["Chamados_Mes_Comparado"] = r["Chamados_Mes_Comparado"].astype(int)
    r["Diferenca"] = r["Chamados_Mes_Principal"] - r["Chamados_Mes_Comparado"]
    r["Variacao_%"] = np.where(r["Chamados_Mes_Comparado"] > 0, r["Diferenca"] / r["Chamados_Mes_Comparado"] * 100, np.nan)
    return r.sort_values(["Diferenca", "Variacao_%"], ascending=[False, False])


def grafico_resumo_unico(kpis, mes):
    data = pd.DataFrame({"Indicador": ["Chamados", "Encerrados", "Críticos", "Pendentes"], "Quantidade": [kpis["total"], kpis["encerrados"], kpis["criticos"], kpis["pendentes"]]})
    fig = px.bar(data, x="Indicador", y="Quantidade", text="Quantidade", title=f"Resumo Geral — {mes}")
    fig.update_traces(textposition="outside")
    fig.update_layout(height=430, showlegend=False)
    return fig


def grafico_resumo_comp(kp, kc, mp, mc):
    data = pd.DataFrame({"Indicador": ["Chamados", "Encerrados", "Críticos", "Pendentes"] * 2, "Mês": [mc] * 4 + [mp] * 4, "Quantidade": [kc["total"], kc["encerrados"], kc["criticos"], kc["pendentes"], kp["total"], kp["encerrados"], kp["criticos"], kp["pendentes"]]})
    fig = px.bar(data, x="Indicador", y="Quantidade", color="Mês", barmode="group", text="Quantidade", title=f"Resumo Geral — {mp} x {mc}")
    fig.update_traces(textposition="outside")
    fig.update_layout(height=430)
    return fig


def grafico_qualidade_unico(kpis, mes):
    fig = go.Figure()
    fig.add_trace(go.Indicator(mode="gauge+number", value=kpis["sla"], title={"text": f"SLA Cumprido — {mes}"}, gauge={"axis": {"range": [0, 100]}, "threshold": {"line": {"width": 4}, "value": 80}}, domain={"x": [0, .45], "y": [0, 1]}))
    fig.add_trace(go.Indicator(mode="gauge+number", value=kpis["retorno_1h"], title={"text": f"1º Retorno ≤ 1h — {mes}"}, gauge={"axis": {"range": [0, 100]}, "threshold": {"line": {"width": 4}, "value": 70}}, domain={"x": [.55, 1], "y": [0, 1]}))
    fig.update_layout(height=380)
    return fig


def grafico_qualidade_comp(kp, kc, mp, mc):
    data = pd.DataFrame({"Indicador": ["SLA Cumprido", "1º Retorno ≤ 1h"] * 2, "Mês": [mc, mc, mp, mp], "Percentual": [kc["sla"], kc["retorno_1h"], kp["sla"], kp["retorno_1h"]]})
    fig = px.bar(data, x="Indicador", y="Percentual", color="Mês", barmode="group", text=data["Percentual"].map(lambda x: f"{x:.1f}%"), title=f"Indicadores de Qualidade — {mp} x {mc}")
    fig.update_traces(textposition="outside")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(height=380)
    return fig


def top_barra(df, coluna, titulo, top=10):
    dados = df.groupby(coluna).size().reset_index(name="Chamados").sort_values("Chamados", ascending=False).head(top)
    fig = px.bar(dados, x="Chamados", y=coluna, orientation="h", text="Chamados", title=titulo)
    fig.update_layout(height=420, yaxis={"categoryorder": "total ascending"})
    return fig


def grafico_prioridade(df, titulo):
    dados = df.groupby("Prioridade").size().reset_index(name="Chamados").sort_values("Chamados", ascending=False)
    fig = px.pie(dados, values="Chamados", names="Prioridade", title=titulo, hole=.35)
    fig.update_layout(height=420)
    return fig


st.markdown("""
<div class="title-box">
<h1>Dashboard CEO — Suporte / Help Desk</h1>
<p>Visão executiva mensal com SLA, primeiro retorno, criticidade, clientes e causas dos chamados.</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("📤 Upload dos Excel")
uploaded_files = st.sidebar.file_uploader("Envie um ou mais arquivos Excel", type=["xls", "xlsx"], accept_multiple_files=True)
if not uploaded_files:
    st.info("Faça upload de um ou mais arquivos Excel para gerar o dashboard.")
    st.stop()

df, arquivos, mapas = carregar_dados_excel(uploaded_files)
if df.empty:
    st.error("Nenhum dado válido foi carregado. Verifique os arquivos enviados.")
    st.stop()

st.sidebar.markdown("### ℹ️ Informações do Dataset")
st.sidebar.write(f"**Arquivos enviados:** {len(arquivos)}")
for arq in arquivos:
    st.sidebar.write(f"- `{arq}`")
st.sidebar.write(f"**Total de linhas:** {len(df)}")
with st.sidebar.expander("📋 Colunas mapeadas"):
    for arquivo, mapa in mapas.items():
        st.write(f"**{arquivo}**")
        st.json({k: (v if v is not None else "Não encontrada") for k, v in mapa.items()})

meses = meses_ordenados(df)
st.sidebar.header("🎛️ Filtros")
modo = st.sidebar.radio("Modo de visão", ["Único mês", "Comparação"], index=0)
mes_principal = st.sidebar.selectbox("Mês principal", meses, index=len(meses)-1)
sug = mes_anterior(df, mes_principal)
idx_comp = meses.index(sug) if sug in meses else 0
mes_comp = None
if modo == "Comparação":
    mes_comp = st.sidebar.selectbox("Mês de comparação", meses, index=idx_comp)

empresa = st.sidebar.selectbox("Empresa", ["Todas"] + sorted(df["Empresa_Padronizada"].dropna().unique().tolist()))
setor = st.sidebar.selectbox("Setor", ["Todos"] + sorted(df["Setor"].dropna().unique().tolist()))
resp = st.sidebar.selectbox("Responsável", ["Todos"] + sorted(df["Responsavel"].dropna().unique().tolist()))
prior = st.sidebar.selectbox("Prioridade", ["Todas"] + sorted(df["Prioridade"].dropna().unique().tolist()))
stat = st.sidebar.selectbox("Status", ["Todos"] + sorted(df["Status"].dropna().unique().tolist()))

dff = df.copy()
if empresa != "Todas": dff = dff[dff["Empresa_Padronizada"] == empresa]
if setor != "Todos": dff = dff[dff["Setor"] == setor]
if resp != "Todos": dff = dff[dff["Responsavel"] == resp]
if prior != "Todas": dff = dff[dff["Prioridade"] == prior]
if stat != "Todos": dff = dff[dff["Status"] == stat]

df_principal = filtrar_mes(dff, mes_principal)
kp = calcular_kpis(df_principal)
df_comp = pd.DataFrame()
kc = None
if modo == "Comparação":
    df_comp = filtrar_mes(dff, mes_comp)
    kc = calcular_kpis(df_comp)
    if mes_comp == mes_principal:
        st.warning("O mês de comparação é igual ao mês principal. Escolha meses diferentes para comparar melhor.")

st.markdown(f'<div class="section-title">📌 KPIs — {mes_principal if modo == "Único mês" else mes_principal + " x " + mes_comp}</div><div class="section-line"></div>', unsafe_allow_html=True)
cores = ["linear-gradient(135deg,#667eea,#764ba2)", "linear-gradient(135deg,#7c3aed,#4f46e5)", "linear-gradient(135deg,#0f9b8e,#38ef7d)", "linear-gradient(135deg,#f59e0b,#fcd34d)", "linear-gradient(135deg,#14b8a6,#5eead4)", "linear-gradient(135deg,#1e3a8a,#334155)", "linear-gradient(135deg,#ef4444,#f97316)", "linear-gradient(135deg,#e11d48,#ef4444)"]
if modo == "Único mês":
    cards = [("Total de chamados", fmt_num(kp["total"]), "Volume do mês"), ("Empresas atendidas", fmt_num(kp["empresas"]), "Clientes atendidos"), ("Chamados encerrados", fmt_num(kp["encerrados"]), "Finalizados"), ("Chamados pendentes", fmt_num(kp["pendentes"]), "Abertos ou sem encerramento"), ("SLA cumprido", fmt_pct(kp["sla"]), "Dentro do prazo"), ("1º retorno ≤ 1h", fmt_pct(kp["retorno_1h"]), "Velocidade inicial"), ("Tempo médio resolução", fmt_h(kp["resolucao_h"]), "Tempo médio até finalizar"), ("Chamados críticos", fmt_num(kp["criticos"]), "Risco operacional")]
else:
    cards = [("Total de chamados", fmt_num(kp["total"]), delta_texto(kp["total"], kc["total"])), ("Empresas atendidas", fmt_num(kp["empresas"]), delta_texto(kp["empresas"], kc["empresas"])), ("Chamados encerrados", fmt_num(kp["encerrados"]), delta_texto(kp["encerrados"], kc["encerrados"])), ("Chamados pendentes", fmt_num(kp["pendentes"]), delta_texto(kp["pendentes"], kc["pendentes"])), ("SLA cumprido", fmt_pct(kp["sla"]), delta_texto(kp["sla"], kc["sla"], "pp")), ("1º retorno ≤ 1h", fmt_pct(kp["retorno_1h"]), delta_texto(kp["retorno_1h"], kc["retorno_1h"], "pp")), ("Tempo médio resolução", fmt_h(kp["resolucao_h"]), delta_texto(kp["resolucao_h"], kc["resolucao_h"], "h")), ("Chamados críticos", fmt_num(kp["criticos"]), delta_texto(kp["criticos"], kc["criticos"]))]
for linha in range(2):
    cols = st.columns(4)
    for i in range(4):
        idx = linha*4+i
        with cols[i]:
            card(cards[idx][0], cards[idx][1], cards[idx][2], cores[idx])

st.markdown('<div class="section-title">📈 Resumo Geral</div><div class="section-line"></div>', unsafe_allow_html=True)
st.plotly_chart(grafico_resumo_unico(kp, mes_principal) if modo == "Único mês" else grafico_resumo_comp(kp, kc, mes_principal, mes_comp), use_container_width=True)

st.markdown('<div class="section-title">🎯 Indicadores de Qualidade</div><div class="section-line"></div>', unsafe_allow_html=True)
st.plotly_chart(grafico_qualidade_unico(kp, mes_principal) if modo == "Único mês" else grafico_qualidade_comp(kp, kc, mes_principal, mes_comp), use_container_width=True)

st.markdown('<div class="section-title">🗓️ Evolução Mensal</div><div class="section-line"></div>', unsafe_allow_html=True)
mensal = dff.groupby(["AnoMesNum", "MesAno"]).size().reset_index(name="Chamados").sort_values("AnoMesNum")
st.plotly_chart(px.line(mensal, x="MesAno", y="Chamados", markers=True, title="Evolução Mensal de Chamados"), use_container_width=True)

st.markdown('<div class="section-title">🏢 Operação, Clientes e Motivos</div><div class="section-line"></div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(top_barra(df_principal, "Setor", f"Chamados por Setor — {mes_principal}"), use_container_width=True)
with col2:
    st.plotly_chart(grafico_prioridade(df_principal, f"Chamados por Prioridade — {mes_principal}"), use_container_width=True)
col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(top_barra(df_principal, "Empresa_Padronizada", f"Top Clientes — {mes_principal}"), use_container_width=True)
with col4:
    st.plotly_chart(top_barra(df_principal, "Tipo", f"Top Motivos / Tipos — {mes_principal}"), use_container_width=True)

if modo == "Comparação":
    st.markdown('<div class="section-title">🚨 Clientes com Maior Aumento</div><div class="section-line"></div>', unsafe_allow_html=True)
    rank = ranking_aumento(df_principal, df_comp)
    rank_pos = rank[rank["Diferenca"] > 0].copy().head(15)
    if rank_pos.empty:
        st.info("Nenhum cliente apresentou aumento de chamados no período comparado.")
    else:
        exibir = rank_pos.rename(columns={"Empresa_Padronizada": "Empresa", "Chamados_Mes_Comparado": f"Chamados {mes_comp}", "Chamados_Mes_Principal": f"Chamados {mes_principal}", "Diferenca": "Diferença", "Variacao_%": "Variação %"})
        exibir["Variação %"] = exibir["Variação %"].round(1)
        st.dataframe(exibir, use_container_width=True)
        fig = px.bar(rank_pos.head(10), x="Diferenca", y="Empresa_Padronizada", orientation="h", text="Diferenca", title=f"Top clientes com maior aumento — {mes_principal} x {mes_comp}")
        fig.update_layout(height=430, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<div class="section-title">⚠️ Alertas Executivos</div><div class="section-line"></div>', unsafe_allow_html=True)
alertas = [("Chamados críticos", fmt_num(kp["criticos"])), ("Pendentes", fmt_num(kp["pendentes"])), ("Fora do SLA", fmt_num(kp["fora_sla"])), ("Sem avaliação", fmt_num(kp["sem_avaliacao"])), ("1º retorno ≤ 1h", fmt_pct(kp["retorno_1h"]))]
if modo == "Comparação":
    rank = ranking_aumento(df_principal, df_comp)
    pos = rank[rank["Diferenca"] > 0]
    if not pos.empty:
        top = pos.iloc[0]
        var = "-" if pd.isna(top["Variacao_%"]) else f"{top['Variacao_%']:.1f}%".replace(".", ",")
        alertas.append(("Cliente com maior aumento", f"{top['Empresa_Padronizada']} | +{int(top['Diferenca'])} ({var})"))
    cbloc = rank[rank["Empresa_Padronizada"] == "CBLOC"]
    if not cbloc.empty and cbloc.iloc[0]["Diferenca"] > 0:
        row = cbloc.iloc[0]
        var = "-" if pd.isna(row["Variacao_%"]) else f"{row['Variacao_%']:.1f}%".replace(".", ",")
        alertas.append(("CBLOC em atenção", f"+{int(row['Diferenca'])} chamados ({var})"))
cols = st.columns(3)
for i, (t, v) in enumerate(alertas):
    with cols[i % 3]:
        st.markdown(f'<div class="alert-box"><div class="small-muted">{t}</div><div style="font-size:24px;font-weight:900;color:#0f172a;margin-top:5px;">{v}</div></div>', unsafe_allow_html=True)

with st.expander("🔎 Ver amostra dos dados tratados"):
    st.dataframe(dff.head(100), use_container_width=True)

st.caption("Dashboard preparado para Excel via upload e futura integração com API usando somente GET.")
