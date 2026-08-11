import streamlit as st
import pandas as pd
import plotly.express as px
import re
import gspread

# ==========================================
# 1. Configuração da Página e Estilo
# ==========================================
st.set_page_config(
    page_title="Gestão de Pagamentos Diários",
    page_icon="💰",
    layout="wide"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #1E88E5;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #212529;
    }
    .metric-label {
        font-size: 14px;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Funções de Conexão e Tratamento de Dados
# ==========================================
def format_brl(val):
    """Formata valores numéricos para o padrão de moeda brasileiro (R$)."""
    try:
        if pd.isna(val) or val is None:
            return "R$ 0,00"
        return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def clean_currency_to_float(series):
    """Converte valores em texto (com R$, pontos e vírgulas) para float."""
    def convert_val(v):
        if pd.isna(v):
            return 0.0
        s = str(v).strip()
        s = re.sub(r'[^\d,.-]', '', s)
        if not s:
            return 0.0
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return 0.0

    return series.apply(convert_val)

@st.cache_resource
def get_gspread_client():
    """Autentica no Google Sheets usando o TOML salvo nas Secrets do Streamlit."""
    try:
        # Busca as credenciais sob a chave [gcp_service_account]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            creds_dict = dict(st.secrets)

        # Trata quebras de linha na chave privada
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        return gspread.service_account_from_dict(creds_dict)
    except Exception as e:
        st.sidebar.error(f"Erro na autenticação dos Secrets: {e}")
        return None

@st.cache_data(ttl=10)
def load_data(url_or_path):
    """Carrega o CSV da planilha do Google Sheets."""
    url = url_or_path.strip()
    if "/edit" in url:
        url = url.split("/edit")[0] + "/export?format=csv"
    elif "docs.google.com" in url and not url.endswith("format=csv"):
        url = url + "/export?format=csv"

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

# ==========================================
# 3. Sidebar - Configurações, Formulário e Filtros
# ==========================================
st.sidebar.title("⚙️ Gestão de Pagamentos")

# Busca o link padrão salvo em st.secrets (default_sheet_url)
DEFAULT_URL = st.secrets.get("default_sheet_url", "")

sheet_url_input = st.sidebar.text_input(
    "Link público do Google Sheets:",
    value=DEFAULT_URL,
    help="O link padrão é carregado automaticamente das Secrets. Altere caso queira conectar outra planilha."
)

if not sheet_url_input:
    st.info("💡 **Para começar:** Cole o link público da sua planilha do Google Sheets no campo do menu lateral.")
    st.stop()

try:
    df_raw = load_data(sheet_url_input)
except Exception as err:
    st.error(f"Erro ao carregar a planilha. Verifique as permissões de acesso. Detalhes: {err}")
    st.stop()

df = df_raw.copy()

# Mapeamento Dinâmico de Colunas
col_valor = next((c for c in df.columns if "valor" in c.lower()), None)
col_cat = next((c for c in df.columns if "categoria" in c.lower() and "sub" not in c.lower()), None)
col_essencial = next((c for c in df.columns if "essencial" in c.lower() or "supérfluo" in c.lower()), None)
col_data = next((c for c in df.columns if "data" in c.lower() or "carimbo" in c.lower()), None)

# Processa colunas principais
if col_valor:
    df["Valor_Num"] = clean_currency_to_float(df[col_valor])
else:
    df["Valor_Num"] = 0.0

if col_data:
    df["Data_Parsed"] = pd.to_datetime(df[col_data], errors="coerce")

# --- NOVO REGISTRO (FORMULÁRIO NA SIDEBAR) ---
st.sidebar.markdown("---")
st.sidebar.subheader("➕ Novo Registro")

categorias_base = ["Alimentação", "Moradia", "Transporte", "Saúde", "Educação", "Lazer", "Serviços", "Outros"]

if col_cat and not df[col_cat].isna().all():
    cats_planilha = [str(x).strip() for x in df[col_cat].unique() if pd.notna(x) and str(x).strip() != ""]
    lista_categorias = list(dict.fromkeys(categorias_base + cats_planilha))
else:
    lista_categorias = categorias_base

with st.sidebar.form(key="form_novo_registro", clear_on_submit=True):
    nova_data = st.date_input("Data do Pagamento")
    nova_cat = st.selectbox("Categoria", lista_categorias)
    nova_desc = st.text_input("Descrição breve")
    novo_valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
    novo_metodo = st.selectbox("Método de pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Outro"])
    novo_essencial = st.selectbox("Essencial x Supérfluo (1 a 5)", [1, 2, 3, 4, 5], index=2, 
                                  help="1: Muito Supérfluo | 5: Muito Essencial")

    btn_salvar = st.form_submit_button("💾 Salvar Registro")

if btn_salvar:
    gc = get_gspread_client()
    if gc is None:
        st.sidebar.error("❌ Credenciais do Google Cloud não encontradas nos Secrets.")
    else:
        try:
            sh = gc.open_by_url(sheet_url_input)
            worksheet = sh.get_worksheet(0)
            
            carimbo = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
            data_str = nova_data.strftime("%d/%m/%Y")
            valor_formatted = f"R$ {novo_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            nova_linha = [carimbo, data_str, nova_cat, nova_desc, valor_formatted, novo_metodo, novo_essencial]
            
            worksheet.append_row(nova_linha)
            st.sidebar.success("✅ Registro adicionado à planilha com sucesso!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ Erro ao gravar na planilha: {e}")

# --- FILTROS DA SIDEBAR ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtros")

if col_data and not df["Data_Parsed"].isna().all():
    min_d = df["Data_Parsed"].min().date()
    max_d = df["Data_Parsed"].max().date()
    if min_d and max_d and min_d != max_d:
        d_range = st.sidebar.date_input("Período:", [min_d, max_d])
        if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
            df = df[(df["Data_Parsed"].dt.date >= d_range[0]) & (df["Data_Parsed"].dt.date <= d_range[1])]

if col_cat:
    cats = ["Todas"] + sorted([str(x) for x in df[col_cat].dropna().unique()])
    sel_cat = st.sidebar.selectbox("Filtrar Categoria:", cats)
    if sel_cat != "Todas":
        df = df[df[col_cat] == sel_cat]

# ==========================================
# 4. Painel Principal - Métricas
# ==========================================
st.title("📊 Gestão de Pagamentos Diários")

total_gasto = df["Valor_Num"].sum()
total_registros = len(df)
media_pagamento = total_gasto / total_registros if total_registros > 0 else 0.0

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Gasto</div>
        <div class="metric-value">{format_brl(total_gasto)}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total de Pagamentos</div>
        <div class="metric-value">{total_registros}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Média por Pagamento</div>
        <div class="metric-value">{format_brl(media_pagamento)}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. Gráficos Interativos
# ==========================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("Gastos por Categoria")
    if col_cat and not df.empty:
        df_cat = df.groupby(col_cat)["Valor_Num"].sum().reset_index()
        fig_bar = px.bar(
            df_cat,
            x=col_cat,
            y="Valor_Num",
            labels={col_cat: "Categoria", "Valor_Num": "Valor (R$)"},
            color="Valor_Num",
            color_continuous_scale="Blues"
        )
        fig_bar.update_layout(yaxis_tickprefix="R$ ", showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados suficientes para o gráfico de Categoria.")

with g2:
    st.subheader("Gradação: Supérfluo (1) a Essencial (5)")
    if col_essencial and not df.empty:
        legenda_map = {
            1: "1 - Muito Supérfluo",
            2: "2 - Supérfluo",
            3: "3 - Neutro",
            4: "4 - Essencial",
            5: "5 - Muito Essencial"
        }
        
        df_ess = df.copy()
        df_ess["Nota_Num"] = pd.to_numeric(df_ess[col_essencial], errors="coerce")
        df_ess["Legenda_Formatada"] = df_ess["Nota_Num"].map(legenda_map).fillna("Não informado")
        
        df_pie = df_ess.groupby(["Nota_Num", "Legenda_Formatada"])["Valor_Num"].sum().reset_index()
        df_pie = df_pie.sort_values("Nota_Num")
        
        fig_pie = px.pie(
            df_pie,
            names="Legenda_Formatada",
            values="Valor_Num",
            hole=0.4,
            category_orders={"Legenda_Formatada": list(legenda_map.values())},
            color_discrete_sequence=px.colors.diverging.RdYlBu
        )
        
        fig_pie.update_traces(
            textinfo="percent",
            hovertemplate="<b>%{label}</b><br>Total Gasto: R$ %{value:,.2f}<br>Proporção: %{percent}"
        )
        fig_pie.update_layout(
            legend_title_text="Grau de Necessidade",
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sem dados suficientes para o gráfico de Essencial x Supérfluo.")

# ==========================================
# 6. Tabela de Lançamentos
# ==========================================
st.subheader("📋 Lançamentos do Formulário")

df_table = df.copy()
if "Valor_Num" in df_table.columns:
    df_table["Valor (R$)"] = df_table["Valor_Num"].apply(format_brl)

cols_final = [c for c in df_table.columns if c not in ["Valor_Num", "Data_Parsed"]]

st.dataframe(
    df_table[cols_final],
    use_container_width=True,
    hide_index=True
)
