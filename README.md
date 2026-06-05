# Dashboard CEO — Suporte / Help Desk

Dashboard executivo em Streamlit para análise mensal de chamados/help desk.

## Funcionalidades

- Upload de um ou mais arquivos Excel pela tela.
- Não usa arquivos antigos da pasta.
- Aceita `.xls` e `.xlsx`.
- Modo **Único mês** e modo **Comparação**.
- KPIs executivos, gráficos operacionais, clientes com maior aumento e alertas executivos.
- Padronização automática da empresa CBLOC/ACBLOC para `CBLOC`.
- Preparado para futura API usando somente GET.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se o comando `streamlit` não funcionar:

```bash
python -m streamlit run app.py
```

## Como publicar no Streamlit Cloud

1. Crie um repositório no GitHub.
2. Envie os arquivos `app.py`, `requirements.txt`, `README.md` e `.gitignore`.
3. Acesse o Streamlit Cloud.
4. Conecte o repositório.
5. Main file path: `app.py`.
6. Clique em Deploy.
