import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

# Importações de escrita com tratamento de segurança
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS VISUAIS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Pagamentos Diários - Kaffa Zig",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Métricas do topo ampliadas e destacadas */
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

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1NJ4sLPZ1VHxmpSOyqMw7cXfIJBl9yaVVok1QQofHs1Q/edit?usp=sharing"

# -----------------------------------------------------------------------------
# 2. AUTENTICAÇÃO E TRATAMENTO DA CHAVE PEM
# -----------------------------------------------------------------------------
def sanitize_pem_key(key_str):
    """Reconstrói a chave RSA em formato PEM válido caso o cabeçalho seja perdido."""
    if not key_str or not isinstance(key_str, str):
        return key_str

    # Limpeza de caracteres de escape e aspas extras
    key_clean = key_str.replace('\\n', '\n').replace('"', '').replace("'", "").strip()

    # Se já tiver os cabeçalhos corretos, retorna ajustada
    if "-----BEGIN PRIVATE KEY-----" in key_clean and "-----END PRIVATE KEY-----" in key_clean:
        return key_clean

    # Se a string veio sem cabeçalho (Base64 puro), limpa espaços e reestrutura
    body = key_clean.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
    body = "".join(body.split())

    # Formata em blocos de 64 caracteres (padrão RFC 7468)
    lines = [body[i:i+64] for i in range(0, len(body), 64)]
    pem_body = "\n".join(lines)

    return f"-----BEGIN PRIVATE KEY-----\n{pem_body}\n-----END PRIVATE KEY-----\n"

@st.cache_resource
def get_gspread_client():
    if not HAS_GSPREAD:
        return None
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" not in st.secrets:
        return None
        
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        info["private_key"] = sanitize_pem_key(info["private_key"])
        
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def obter_aba_planilha():
    client = get_gspread_client()
    if not client:
        return None
    url = st.secrets.get("google_sheet_url", DEFAULT_SHEET_URL)
    return client.open_by_url(url).sheet1

# -----------------------------------------------------------------------------
# 3. LEITURA E TRATAMENTO DOS DADOS
# -----------------------------------------------------------------------------
def obter_serie(df, col_name):
    if col_name not in df.columns:
        return None
    res = df[col_name]
    if isinstance(res, pd.DataFrame):
        return res.iloc[:, 0]
    return res

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        sheet = obter_aba_planilha()
        if not sheet:
            return pd.DataFrame()
            
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
    except Exception as e:
        st.error(f"Erro ao acessar a planilha via Service Account: {e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    df = df.dropna(how='all')

    col_map = {}
    usados = set()
    for col in df.columns:
        c_low = str(col).strip().lower()
        if 'carimbo' in c_low and 'Carimbo' not in usados:
            col_map[col] = 'Carimbo de data/hora'
            usados.add('Carimbo')
        elif 'data' in c_low and 'carimbo' not in c_low and 'Data' not in usados:
            col_map[col] = 'Data'
            usados.add('Data')
        elif 'valor' in c_low and 'Valor' not in usados:
            col_map[col] = 'Valor'
            usados.add('Valor')
        elif 'categoria' in c_low and 'Categoria' not in usados:
            col_map[col] = 'Categoria'
            usados.add('Categoria')
        elif ('metodo' in c_low or 'método' in c_low or 'pagamento' in c_low) and 'Método de pagamento' not in usados:
            col_map[col] = 'Método de pagamento'
            usados.add('Método de pagamento')
        elif ('essencial' in c_low or 'superfluo' in c_low or 'supérfluo' in c_low or 'grada' in c_low) and 'Essencial x Supérfluo' not in usados:
            col_map[col] = 'Essencial x Supérfluo'
            usados.add('Essencial x Supérfluo')

    df = df.rename(columns=col_map)

    # Tratamento da coluna Data
    serie_data = obter_serie(df, 'Data')
    if serie_data is not None:
        datas_str = serie_data.astype(str).str.strip()
        df['Data_Formatada'] = pd.to_datetime(datas_str, format='%d/%m/%Y', errors='coerce')
        mask_na = df['Data_Formatada'].isna()
        if mask_na.any():
            df.loc[mask_na, 'Data_Formatada'] = pd.to_datetime(serie_data[mask_na], dayfirst=True, errors='coerce')

    # Tratamento da coluna Valor
    serie_valor = obter_serie(df, 'Valor')
    if serie_valor is not None:
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

        df['Valor Numérico'] = serie_valor.apply(parse_valor)
    else:
        df['Valor Numérico'] = 0.0

    return df

# -----------------------------------------------------------------------------
# 4. PAINEL PRINCIPAL E INTERFACE DA BARRA LATERAL
# -----------------------------------------------------------------------------
st.title("📊 Gestão de Pagamentos Diários")

# --- BARRA LATERAL ---
st.sidebar.image("https://img.icons8.com/color/96/000000/google-sheets.png", width=55)
st.sidebar.title("Kaffa Zig Gestão")

if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ATALHO PARA ABRIR A PLANILHA
st.sidebar.divider()
sheet_link = st.secrets.get("google_sheet_url", DEFAULT_SHEET_URL)
st.sidebar.link_button("🟢 Abrir Planilha Google", sheet_link, use_container_width=True)

# FORMULÁRIO PARA INSERÇÃO DE DADOS
st.sidebar.divider()
with st.sidebar.expander("➕ Inserir Novo Lançamento", expanded=True):
    with st.form("form_novo_gasto", clear_on_submit=True):
        f_data = st.date_input("Data do Gasto")
        f_categoria = st.selectbox(
            "Categoria",
            ["Alimentação", "Beleza", "Casa", "Doação", "Lazer", "Outros", "Presentes", "Saúde", "Transporte"]
        )
        f_descricao = st.text_input("Descrição breve")
        f_valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        f_metodo = st.selectbox(
            "Método de Pagamento",
            ["Cartão crédito", "Cartão débito", "Pix", "Dinheiro"]
        )
        f_gradacao = st.slider("Gradação (1-Supérfluo a 5-Essencial)", 1, 5, 3)

        btn_salvar = st.form_submit_button("Salvar Registro", use_container_width=True)

        if btn_salvar:
            if not HAS_GSPREAD:
                st.error("Instale o gspread no requirements.txt.")
            else:
                try:
                    sheet = obter_aba_planilha()
                    if sheet:
                        nova_linha = [
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            f_data.strftime("%d/%m/%Y"),
                            f_categoria,
                            f_descricao,
                            f_valor,
                            f_metodo,
                            f_gradacao
                        ]
                        sheet.append_row(nova_linha, value_input_option="USER_ENTERED")
                        st.success("Lançamento salvo com sucesso!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Erro ao conectar à planilha.")
                except Exception as e:
                    st.error(f"Erro ao salvar registro: {e}")

# --- DASHBOARD DE DADOS ---
if not HAS_GSPREAD:
    st.warning("Atualize o arquivo `requirements.txt` no GitHub para liberar o gspread.")
else:
    df = carregar_dados()

    if not df.empty:
        # FILTRO POR PERÍODO
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

        # MÉTRICAS DE TOPO
        total_gasto = df_filtrado['Valor Numérico'].sum()
        qtd_pagamentos = len(df_filtrado[df_filtrado['Valor Numérico'] > 0])
        media_pagamento = total_gasto / qtd_pagamentos if qtd_pagamentos > 0 else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Gasto", f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c2.metric("Total de Pagamentos", qtd_pagamentos)
        c3.metric("Média por Pagamento", f"R$ {media_pagamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        st.markdown("---")

        # GRÁFICOS (AZUL MARCANTE E FONTES GRANDES)
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
                    textfont=dict(size=16, color='#ffffff', family='Arial Black')
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

        # TABELA DE DADOS
        st.subheader("📋 Lançamentos do Período")
        cols_to_hide = ['Data_Formatada', 'Valor Numérico']
        cols_display = [c for c in df_filtrado.columns if c not in cols_to_hide]
        st.dataframe(df_filtrado[cols_display], use_container_width=True, hide_index=True, height=350)
    else:
        st.info("Planilha conectada com sucesso! Insira um novo lançamento na barra lateral.")
