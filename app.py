import streamlit as st
import pandas as pd
import plotly.express as px
import re

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS CSS (FONTES AMPLIADAS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Pagamentos Diários - Kaffa Zig",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar fontes grandes para métricas, rótulos e títulos
st.markdown("""
<style>
    /* Métricas de topo ampliadas e destacadas */
    [data-testid="stMetricValue"] {
        font-size: 34px !important;
        font-weight: 800 !important;
        color: #38bdf8 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 17px !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
    }
    .stMarkdown h3 {
        font-size: 22px !important;
        font-weight: 700 !important;
    }
    .stSidebar label {
        font-size: 15px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# URL OFICIAL DA SUA PLANILHA PUBLICADA EM CSV
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHTcIZo4KnPLnZCWF20XbR4pRnRXYzKDEqYVQ82kYaR_dOl1MiESgbsdxHMX8ze7N13dSv6IQqAYu6/pub?gid=1963638500&single=true&output=csv"

# -----------------------------------------------------------------------------
# 2. LEITURA E TRATAMENTO AUTOMÁTICO DOS DADOS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=5)
def carregar_dados():
    sheet_url = st.secrets.get("google_sheet_url", DEFAULT_SHEET_URL)
    
    try:
        # Lê o CSV publicado diretamente sem passar por redirecionamento do Drive
        df = pd.read_csv(sheet_url)
    except Exception as e:
        st.error(f"Erro de conexão com a planilha pública: {e}")
        return pd.DataFrame()
        
    if df.empty:
        return df

    # Limpar linhas totalmente em branco
    df = df.dropna(how='all')

    # Mapeamento flexível das colunas da planilha
    col_renames = {}
    for col in df.columns:
        c_lower = str(col).strip().lower()
        if 'carimbo' in c_lower:
            col_renames[col] = 'Carimbo de data/hora'
        elif 'data' in c_lower:
            col_renames[col] = 'Data'
        elif 'categoria' in c_lower:
            col_renames[col] = 'Categoria'
        elif 'descri' in c_lower:
            col_renames[col] = 'Descrição breve'
        elif 'valor' in c_lower:
            col_renames[col] = 'Valor'
        elif 'metodo' in c_lower or 'método' in c_lower or 'pagamento' in c_lower:
            col_renames[col] = 'Método de pagamento'
        elif 'essencial' in c_lower or 'superfluo' in c_lower or 'supérfluo' in c_lower or 'grada' in c_lower:
            col_renames[col] = 'Essencial x Supérfluo'

    df = df.rename(columns=col_renames)

    # Tratamento da Coluna Data
    if 'Data' in df.columns:
        datas_str = df['Data'].astype(str).str.strip()
        df['Data_Formatada'] = pd.to_datetime(datas_str, format='%d/%m/%Y', errors='coerce')
        nat_mask = df['Data_Formatada'].isna()
        if nat_mask.any():
            df.loc[nat_mask, 'Data_Formatada'] = pd.to_datetime(df.loc[nat_mask, 'Data'], dayfirst=True, errors='coerce')

    # Tratamento da Coluna Valor (R$, $, vírgula e ponto)
    if 'Valor' in df.columns:
        def parse_valor(v):
            if pd.isna(v): return 0.0
            if isinstance(v, (int, float)): return float(v)
            v_str = re.sub(r'[^\d,.-]', '', str(v).strip())
            if not v_str: return 0.0
            if ',' in v_str and '.' in v_str:
                v_str = v_str.replace('.', '').replace(',', '.')
            elif ',' in v_str:
                v_str = v_str.replace(',', '.')
            try:
                return float(v_str)
            except:
                return 0.0

        df['Valor Numérico'] = df['Valor'].apply(parse_valor)
    else:
        df['Valor Numérico'] = 0.0

    return df

# -----------------------------------------------------------------------------
# 3. INTERFACE PRINCIPAL E PAINEL (DASHBOARD)
# -----------------------------------------------------------------------------
st.title("📊 Gestão de Pagamentos Diários")

df = carregar_dados()

if df.empty:
    st.warning("Não foi possível carregar os dados. Verifique a conexão com a planilha.")
else:
    # --- BARRA LATERAL ---
    st.sidebar.image("https://img.icons8.com/color/96/000000/google-sheets.png", width=55)
    st.sidebar.title("Kaffa Zig Gestão")

    if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Link do Google Forms
    st.sidebar.divider()
    form_url = st.secrets.get("google_form_url", "")
    if form_url:
        st.sidebar.link_button("📋 Abrir Google Forms", form_url, use_container_width=True)

    # --- FILTRO POR PERÍODO DE DATAS ---
    st.sidebar.divider()
    st.sidebar.subheader("📅 Filtro por Período")

    if 'Data_Formatada' in df.columns and df['Data_Formatada'].notna().any():
        df_valid_dates = df.dropna(subset=['Data_Formatada'])
        min_date = df_valid_dates['Data_Formatada'].min().date()
        max_date = df_valid_dates['Data_Formatada'].max().date()

        date_range = st.sidebar.date_input(
            "Selecione o intervalo",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            d_start, d_end = date_range
            mask = (df['Data_Formatada'].dt.date >= d_start) & (df['Data_Formatada'].dt.date <= d_end)
            df_filtrado = df.loc[mask]
        else:
            df_filtrado = df
    else:
        df_filtrado = df

    # --- MÉTRICAS DE TOPO ---
    total_gasto = df_filtrado['Valor Numérico'].sum()
    qtd_pagamentos = len(df_filtrado[df_filtrado['Valor Numérico'] > 0])
    media_pagamento = total_gasto / qtd_pagamentos if qtd_pagamentos > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Gasto", f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Total de Pagamentos", qtd_pagamentos)
    c3.metric("Média por Pagamento", f"R$ {media_pagamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # --- GRÁFICOS (AZUL MARCANTE E RÓTULOS EM DESTAQUE) ---
    col_g1, col_g2 = st.columns([1.5, 1])

    with col_g1:
        st.subheader("Gastos por Categoria")
        if 'Categoria' in df_filtrado.columns and not df_filtrado.empty:
            df_cat = df_filtrado.groupby('Categoria', as_index=False)['Valor Numérico'].sum()
            df_cat = df_cat.sort_values(by='Valor Numérico', ascending=False)
            
            fig_bar = px.bar(
                df_cat,
                x='Categoria',
                y='Valor Numérico',
                text='Valor Numérico',
                template="plotly_dark",
                color_discrete_sequence=['#3b82f6']  # AZUL DESTACADO
            )
            fig_bar.update_traces(
                texttemplate='R$ %{text:,.2f}',
                textposition='outside',
                textfont=dict(size=16, color='#ffffff', family='Arial Black') # FONTE GRANDE SOBRE AS BARRAS
            )
            fig_bar.update_layout(
                font=dict(size=14),
                xaxis=dict(title="", tickfont=dict(size=14, color='#f8fafc')),
                yaxis=dict(title="R$", title_font=dict(size=16), tickfont=dict(size=14)),
                height=430
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_g2:
        st.subheader("Gradação (1-Supérfluo a 5-Essencial)")
        if 'Essencial x Supérfluo' in df_filtrado.columns and not df_filtrado.empty:
            df_grad = df_filtrado.groupby('Essencial x Supérfluo', as_index=False)['Valor Numérico'].sum()
            df_grad['Essencial x Supérfluo'] = df_grad['Essencial x Supérfluo'].astype(str)
            
            fig_pie = px.pie(
                df_grad,
                names='Essencial x Supérfluo',
                values='Valor Numérico',
                hole=0.4,
                template="plotly_dark",
                color_discrete_sequence=['#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6']
            )
            fig_pie.update_traces(
                textinfo='percent+label',
                textfont=dict(size=15, color='#ffffff')
            )
            fig_pie.update_layout(
                font=dict(size=14),
                legend=dict(font=dict(size=14)),
                height=430
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # --- TABELA DE DADOS ---
    st.subheader("📋 Lançamentos do Período")
    cols_to_hide = ['Data_Formatada', 'Valor Numérico']
    cols_display = [c for c in df_filtrado.columns if c not in cols_to_hide]
    st.dataframe(df_filtrado[cols_display], use_container_width=True, hide_index=True, height=350)
