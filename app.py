import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Pagamentos Diários",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. CONEXÃO NATIVA VIA ST.CONNECTION (ISENTA DE ERROS DE CHAVE MANUAL)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def carregar_dados():
    # Lê os dados da planilha usando o conector nativo do Streamlit
    df = conn.read(ttl=10)
    
    if not df.empty:
        # Remover linhas totalmente vazias
        df = df.dropna(how='all')
        
        # Converter a coluna Data para o formato datetime
        if 'Data' in df.columns:
            df['Data_Formatada'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        
        # Tratar a coluna Valor para converter qualquer texto em número puro
        if 'Valor' in df.columns:
            if df['Valor'].dtype == object:
                df['Valor Numérico'] = df['Valor'].astype(str).str.replace('R$', '', regex=False)
                df['Valor Numérico'] = df['Valor Numérico'].str.replace('$', '', regex=False)
                df['Valor Numérico'] = df['Valor Numérico'].str.replace('.', '', regex=False)
                df['Valor Numérico'] = df['Valor Numérico'].str.replace(',', '.', regex=False)
                df['Valor Numérico'] = pd.to_numeric(df['Valor Numérico'], errors='coerce')
            else:
                df['Valor Numérico'] = pd.to_numeric(df['Valor'], errors='coerce')
            
    return df

# -----------------------------------------------------------------------------
# 3. INTERFACE LATERAL (FILTROS E NOVO LANÇAMENTO)
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/000000/google-sheets.png", width=60)
st.sidebar.title("Opções")

df = carregar_dados()

# --- FORMULÁRIO DE INSERÇÃO ---
with st.sidebar.expander("➕ Inserir Novo Lançamento"):
    with st.form("novo_lancamento_form", clear_on_submit=True):
        f_data = st.date_input("Data do Pagamento")
        f_categoria = st.selectbox(
            "Categoria", 
            ["Alimentação", "Beleza", "Casa", "Doação", "Lazer", "Outros", "Presentes", "Saúde", "Transporte"]
        )
        f_descricao = st.text_input("Descrição breve")
        f_valor = st.number_input("Valor", min_value=0.01, format="%0.2f")
        f_metodo = st.selectbox(
            "Método de pagamento", 
            ["Cartão crédito", "Cartão débito", "Pix", "Dinheiro"]
        ) 
        f_gradacao = st.slider("Gradação (1 - Supérfluo a 5 - Essencial)", 1, 5, 3)
        
        submit = st.form_submit_button("Salvar na Planilha")
        
        if submit:
            novo_dado = pd.DataFrame([{
                "Carimbo de data/hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Data": f_data.strftime("%d/%m/%Y"),
                "Categoria": f_categoria,
                "Descrição breve": f_descricao,
                "Valor": f_valor,
                "Método de pagamento": f_metodo,
                "Essencial x Supérfluo": f_gradacao
            }])
            
            # Anexa o novo DataFrame diretamente na planilha usando o conector nativo
            df_atual = conn.read()
            df_atualizado = pd.concat([df_atual, novo_dado], ignore_index=True)
            conn.update(data=df_atualizado)
            
            st.success("Lançamento inserido com sucesso!")
            st.cache_data.clear()
            st.rerun()

# --- FILTRO DE DATAS ---
st.sidebar.divider()
if not df.empty and 'Data_Formatada' in df.columns and not df['Data_Formatada'].dropna().empty:
    min_date = df['Data_Formatada'].min().date()
    max_date = df['Data_Formatada'].max().date()
    
    st.sidebar.subheader("📅 Filtro de Datas")
    data_inicio, data_fim = st.sidebar.date_input(
        "Selecione o período",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    if isinstance(data_inicio, type(min_date)) and isinstance(data_fim, type(max_date)):
        mask = (df['Data_Formatada'].dt.date >= data_inicio) & (df['Data_Formatada'].dt.date <= data_fim)
        df_filtrado = df.loc[mask]
    else:
        df_filtrado = df
else:
    df_filtrado = df

# -----------------------------------------------------------------------------
# 4. PAINEL PRINCIPAL (DASHBOARD)
# -----------------------------------------------------------------------------
st.title("📊 Gestão de Pagamentos Diários")

if not df_filtrado.empty and 'Valor Numérico' in df_filtrado.columns:
    
    # --- MÉTRICAS DE TOPO ---
    total_gasto = df_filtrado['Valor Numérico'].sum()
    total_pagamentos = len(df_filtrado)
    media_pagamento = df_filtrado['Valor Numérico'].mean() if total_pagamentos > 0 else 0.0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Total Gasto", 
            value=f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    with col2:
        st.metric(label="Total de Pagamentos", value=total_pagamentos)
    with col3:
        st.metric(
            label="Média por Pagamento", 
            value=f"R$ {media_pagamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
    st.markdown("---")
    
    # --- GRÁFICOS ---
    col_chart1, col_chart2 = st.columns([1.5, 1])
    
    with col_chart1:
        st.subheader("Gastos por Categoria")
        if 'Categoria' in df_filtrado.columns:
            df_cat = df_filtrado.groupby('Categoria')['Valor Numérico'].sum().reset_index()
            fig_bar = px.bar(
                df_cat, 
                x='Categoria', 
                y='Valor Numérico', 
                text_auto='.2s', 
                template="plotly_dark", 
                color_discrete_sequence=['#3b82f6']
            )
            fig_bar.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_chart2:
        st.subheader("Gradação: Supérfluo (1) a Essencial (5)")
        col_grad = 'Essencial x Supérfluo' if 'Essencial x Supérfluo' in df_filtrado.columns else None
        
        if col_grad:
            df_filtrado_grad = df_filtrado.rename(columns={col_grad: 'Grau de Necessidade'})
            fig_pie = px.pie(
                df_filtrado_grad, 
                names='Grau de Necessidade', 
                values='Valor Numérico', 
                hole=0.4, 
                template="plotly_dark", 
                color_discrete_sequence=['#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6']
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    
    # --- TABELA DE DADOS ---
    st.subheader("📋 Lançamentos do Período")
    colunas_visiveis = [col for col in df_filtrado.columns if col not in ['Data_Formatada', 'Valor Numérico']]
    st.dataframe(df_filtrado[colunas_visiveis], use_container_width=True, hide_index=True)

else:
    st.info("Nenhum dado encontrado para o período selecionado ou a planilha está vazia.")
