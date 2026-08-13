import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
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
# 2. CONEXÃO COM GOOGLE SHEETS
# -----------------------------------------------------------------------------
@st.cache_resource
def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Converte o AttrDict do Streamlit em um dicionário nativo do Python
    service_account_info = dict(st.secrets["gcp_service_account"])
    
    # Tratamento automático para quebras de linha na chave privada RSA
    if "private_key" in service_account_info:
        service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
    
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Abre a planilha pela URL configurada nos secrets
    sheet = client.open_by_url(st.secrets["google_sheet_url"]).sheet1
    return sheet

@st.cache_data(ttl=10)  # Recarrega o cache a cada 10 segundos
def carregar_dados():
    sheet = get_google_sheet()
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)
    
    if not df.empty:
        # Converter a coluna Data para o formato datetime do Pandas para o filtro
        df['Data_Formatada'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        
        # Tratar a coluna Valor para converter qualquer texto em número puro
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

sheet = get_google_sheet()
df = carregar_dados()

# --- FORMULÁRIO DE INSERÇÃO CORRIGIDO ---
with st.sidebar.expander("➕ Inserir Novo Lançamento"):
    with st.form("novo_lancamento_form", clear_on_submit=True):
        f_data = st.date_input("Data do Pagamento")
        f_categoria = st.selectbox(
            "Categoria", 
            ["Alimentação", "Beleza", "Casa", "Doação", "Lazer", "Outros", "Presentes", "Saúde", "Transporte"]
        )
        f_descricao = st.text_input("Descrição breve")
        
        # Recebe o valor como número float puro (sem "R$")
        f_valor = st.number_input("Valor", min_value=0.01, format="%0.2f")
        
        # Opções idênticas ao Google Forms para manter o padrão
        f_metodo = st.selectbox(
            "Método de pagamento", 
            ["Cartão crédito", "Cartão débito", "Pix", "Dinheiro"]
        ) 
        f_gradacao = st.slider("Gradação (1 - Supérfluo a 5 - Essencial)", 1, 5, 3)
        
        submit = st.form_submit_button("Salvar no Sheets")
        
        if submit:
            # Prepara os dados para inserção na planilha
            nova_linha = [
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"), # Carimbo de data/hora
                f_data.strftime("%d/%m/%Y"),                  # Data real do pagamento
                f_categoria,                                  # Categoria
                f_descricao,                                  # Descrição breve
                f_valor,                                      # Número float puro
                f_metodo,                                     # Método de pagamento
                f_gradacao                                    # Essencial x Supérfluo
            ]
            
            # USER_ENTERED força o Google Sheets a aplicar a formatação automática de moeda
            sheet.append_row(nova_linha, value_input_option="USER_ENTERED")
            st.success("Lançamento inserido com sucesso!")
            st.cache_data.clear() # Força a atualização do cache
            st.rerun()           # Recarrega a aplicação

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
    
    # Aplica o filtro pela coluna de Data
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
