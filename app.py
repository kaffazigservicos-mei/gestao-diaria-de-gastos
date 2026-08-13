import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Pagamentos Diários - Kaffa Zig",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Link padrão da sua planilha
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1NJ4sLPZ1VHxmpSOyqMw7cXfIJBl9yaVVok1QQofHs1Q/edit?usp=sharing"

# -----------------------------------------------------------------------------
# 2. FUNÇÃO DE SALVAMENTO VIA GSPREAD (SE HOUVER SECRETS CONFIGURADO)
# -----------------------------------------------------------------------------
def salvar_via_gspread(dados_dict):
    try:
        if "gcp_service_account" not in st.secrets:
            return False, "Para salvar direto pelo app, configure a chave de Service Account nos Secrets ou utilize o formulário do Google."
            
        info = dict(st.secrets["gcp_service_account"])
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        sheet_url = st.secrets.get("google_sheet_url", DEFAULT_SHEET_URL)
        sheet = client.open_by_url(sheet_url).sheet1
        
        # Colunas: Carimbo, Data, Categoria, Descrição, Valor, Método, Essencial x Supérfluo
        linha = [
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            dados_dict['data'],
            dados_dict['categoria'],
            dados_dict['descricao'],
            dados_dict['valor'],
            dados_dict['metodo'],
            dados_dict['gradacao']
        ]
        
        sheet.append_row(linha, value_input_option="USER_ENTERED")
        return True, "Lançamento registrado com sucesso na planilha!"
    except Exception as e:
        return False, f"Aviso de escrita: {e}"

# -----------------------------------------------------------------------------
# 3. LEITURA E TRATAMENTO DOS DADOS DA PLANILHA
# -----------------------------------------------------------------------------
def obter_csv_url(sheet_url):
    pattern = r"/d/([a-zA-Z0-9-_]+)"
    match = re.search(pattern, sheet_url)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return sheet_url

@st.cache_data(ttl=5)
def carregar_dados():
    sheet_url = st.secrets.get("google_sheet_url", DEFAULT_SHEET_URL)
    csv_url = obter_csv_url(sheet_url)
    
    try:
        df = pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"Erro ao acessar a planilha pública: {e}")
        return pd.DataFrame()
        
    if df.empty:
        return df

    # Remove linhas completamente nulas
    df = df.dropna(how='all')

    # Mapeamento flexível dos cabeçalhos da sua planilha
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

    # Tratamento da Coluna Valor (R$, $, vírgulas e pontos)
    if 'Valor' in df.columns:
        def parse_valor(v):
            if pd.isna(v):
                return 0.0
            if isinstance(v, (int, float)):
                return float(v)
            v_str = re.sub(r'[^\d,.-]', '', str(v).strip())
            if not v_str:
                return 0.0
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
# 4. PAINEL PRINCIPAL E INTERFACE
# -----------------------------------------------------------------------------
st.title("📊 Gestão de Pagamentos Diários")

df = carregar_dados()

if df.empty:
    st.warning("A planilha não possui dados registrados no momento.")
else:
    # --- BARRA LATERAL ---
    st.sidebar.image("https://img.icons8.com/color/96/000000/google-sheets.png", width=50)
    st.sidebar.title("Kaffa Zig Gestão")

    if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- NOVO LANÇAMENTO NO PRÓPRIO APP ---
    st.sidebar.divider()
    with st.sidebar.expander("➕ Inserir Lançamento no App"):
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

            if st.form_submit_button("Salvar Registro"):
                reg = {
                    'data': f_data.strftime("%d/%m/%Y"),
                    'categoria': f_categoria,
                    'descricao': f_descricao,
                    'valor': f_valor,
                    'metodo': f_metodo,
                    'gradacao': f_gradacao
                }
                ok, msg = salvar_via_gspread(reg)
                if ok:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info(msg)

    # Link do Google Forms (opcional)
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

    # --- MÉTRICAS ---
    total_gasto = df_filtrado['Valor Numérico'].sum()
    qtd_pagamentos = len(df_filtrado[df_filtrado['Valor Numérico'] > 0])
    media_pagamento = total_gasto / qtd_pagamentos if qtd_pagamentos > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Gasto", f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Total de Pagamentos", qtd_pagamentos)
    c3.metric("Média por Pagamento", f"R$ {media_pagamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # --- GRÁFICOS ---
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
                color_discrete_sequence=['#3b82f6']  # AZUL
            )
            fig_bar.update_traces(texttemplate='R$ %{text:.2f}', textposition='outside')
            fig_bar.update_layout(yaxis_title="R$", xaxis_title="")
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
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # --- TABELA DE EXIBIÇÃO ---
    st.subheader("📋 Lançamentos do Período")
    cols_to_hide = ['Data_Formatada', 'Valor Numérico']
    cols_display = [c for c in df_filtrado.columns if c not in cols_to_hide]
    st.dataframe(df_filtrado[cols_display], use_container_width=True, hide_index=True)
