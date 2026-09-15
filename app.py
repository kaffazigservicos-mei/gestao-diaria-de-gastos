--- app.py (原始)


+++ app.py (修改后)
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

st.set_page_config(page_title="Gestão Diária de Gastos", page_icon="💰", layout="wide")

st.title("💰 Gestão Diária de Gastos")
st.markdown("Controle suas despesas por categoria")

# --- Categorias e cores ---
CATEGORIAS = [
    "Alimentação", "Transporte", "Moradia", "Saúde",
    "Educação", "Lazer", "Vestuário", "Outros"
]

CORES = [
    "#ef4444", "#f97316", "#eab308", "#22c55e",
    "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899"
]

cor_por_categoria = dict(zip(CATEGORIAS, CORES))

# --- Dados iniciais ---
if "gastos" not in st.session_state:
    st.session_state.gastos = pd.DataFrame([
        {"Descrição": "Supermercado", "Valor": 350.00, "Categoria": "Alimentação", "Data": "2025-01-15"},
        {"Descrição": "Combustível", "Valor": 200.00, "Categoria": "Transporte", "Data": "2025-01-15"},
        {"Descrição": "Aluguel", "Valor": 1500.00, "Categoria": "Moradia", "Data": "2025-01-14"},
        {"Descrição": "Farmácia", "Valor": 85.00, "Categoria": "Saúde", "Data": "2025-01-14"},
        {"Descrição": "Curso online", "Valor": 120.00, "Categoria": "Educação", "Data": "2025-01-13"},
        {"Descrição": "Cinema", "Valor": 60.00, "Categoria": "Lazer", "Data": "2025-01-13"},
        {"Descrição": "Restaurante", "Valor": 95.00, "Categoria": "Alimentação", "Data": "2025-01-12"},
        {"Descrição": "Ônibus", "Valor": 45.00, "Categoria": "Transporte", "Data": "2025-01-12"},
        {"Descrição": "Roupas", "Valor": 250.00, "Categoria": "Vestuário", "Data": "2025-01-11"},
        {"Descrição": "Conta de luz", "Valor": 180.00, "Categoria": "Moradia", "Data": "2025-01-10"},
    ])

# --- Cards de resumo ---
col1, col2, col3 = st.columns(3)
total = st.session_state.gastos["Valor"].sum()
col1.metric("Total de Gastos", f"R$ {total:,.2f}")
col2.metric("Quantidade de Registros", len(st.session_state.gastos))
col3.metric("Categorias Utilizadas", st.session_state.gastos["Categoria"].nunique())

st.markdown("---")

# --- Formulário e Gráfico lado a lado ---
col_form, col_grafico = st.columns(2)

# --- Formulário ---
with col_form:
    st.subheader("➕ Adicionar Gasto")
    with st.form("form_gasto", clear_on_submit=True):
        descricao = st.text_input("Descrição", placeholder="Ex: Supermercado, Uber, etc.")
        col_v, col_d = st.columns(2)
        with col_v:
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
        with col_d:
            data = st.date_input("Data", value=date.today())
        categoria = st.selectbox("Categoria", CATEGORIAS)
        submitted = st.form_submit_button("Adicionar Gasto", use_container_width=True)

        if submitted and descricao and valor > 0:
            novo = pd.DataFrame([{
                "Descrição": descricao,
                "Valor": valor,
                "Categoria": categoria,
                "Data": data.strftime("%Y-%m-%d"),
            }])
            st.session_state.gastos = pd.concat([novo, st.session_state.gastos], ignore_index=True)
            st.success("Gasto adicionado com sucesso!")
            st.rerun()

# --- Gráfico de Pizza ---
with col_grafico:
    st.subheader("📊 Gastos por Categoria")

    dados_categoria = (
        st.session_state.gastos
        .groupby("Categoria")["Valor"]
        .sum()
        .reset_index()
    )

    if not dados_categoria.empty:
        # Monta listas de cores na mesma ordem dos dados
        cores_grafico = [cor_por_categoria.get(cat, "#999999") for cat in dados_categoria["Categoria"]]

        # Monta os textos da legenda: "Nome da Categoria"
        labels_legenda = dados_categoria["Categoria"].tolist()

        fig = go.Figure(data=[go.Pie(
            labels=labels_legenda,
            values=dados_categoria["Valor"],
            hole=0.4,
            marker=dict(colors=cores_grafico),
            # SEM números no gráfico — apenas a cor da fatia
            textinfo="none",
            # Legenda mostra o NOME da categoria (não números)
            textposition="inside",
            insidetextorientation="radial",
        )])

        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=13),
            ),
            margin=dict(t=20, b=80, l=20, r=20),
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

        # Tabela resumo por categoria
        dados_categoria["Percentual"] = (dados_categoria["Valor"] / total * 100).round(1)
        dados_categoria = dados_categoria.sort_values("Valor", ascending=False)

        st.markdown("##### Resumo por Categoria")
        for _, row in dados_categoria.iterrows():
            cor = cor_por_categoria.get(row["Categoria"], "#999")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                f'<span style="width:12px;height:12px;border-radius:50%;background:{cor};display:inline-block;"></span>'
                f'<b>{row["Categoria"]}</b> — '
                f'R$ {row["Valor"]:,.2f} ({row["Percentual"]}%)'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

# --- Lista de Gastos ---
st.subheader("📋 Lista de Gastos")

df_exibicao = st.session_state.gastos.copy()
df_exibicao["Data"] = pd.to_datetime(df_exibicao["Data"]).dt.strftime("%d/%m/%Y")
df_exibicao["Valor"] = df_exibicao["Valor"].apply(lambda x: f"R$ {x:,.2f}")

st.dataframe(
    df_exibicao,
    use_container_width=True,
    hide_index=True,
)

# --- Botão para remover ---
col_rm1, col_rm2 = st.columns([3, 1])
with col_rm2:
    if st.button("🗑️ Limpar Todos os Gastos", use_container_width=True):
        st.session_state.gastos = pd.DataFrame(columns=["Descrição", "Valor", "Categoria", "Data"])
        st.rerun()
