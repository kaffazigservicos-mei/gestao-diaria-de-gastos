# 📊 App de Gestão de Pagamentos Diários

Aplicativo web interativo desenvolvido para centralizar, visualizar e gerenciar lançamentos financeiros diários. A solução resolve problemas clássicos de inversão de formatação monetária no padrão brasileiro (**R$ 1.234,56**) e permite a distribuição pública **100% gratuita e ilimitada** para usuários e seguidores nas redes sociais.

---

## 🎯 Objetivo do Aplicativo

Permitir que usuários e seguidores possam **consultar indicadores**, **analisar gráficos interativos** e **inserir novos lançamentos financeiros** de forma simples e responsiva. 

O sistema possui alimentação híbrida, aceitando entradas tanto via **Google Forms** quanto direto na **interface do aplicativo web**, mantendo a planilha do Google Sheets como banco de dados centralizado e sincronizado.

---

## 🏗️ Por que a escolha do Streamlit?

A decisão de adotar o **Streamlit (via Streamlit Community Cloud)** em detrimento de plataformas no-code tradicionais baseia-se em três pilares:

1. **Tratamento do Padrão BRL (R$):** Construtores internacionais frequentemente falham na conversão do padrão brasileiro de moeda (uso de vírgula para decimais e ponto para milhares). No Python, a higienização do texto para o tipo numérico é feita na camada de backend de forma precisa.
2. **Distribuição Gratuita Ilimitada:** Plataformas no-code impõem limites rígidos de usuários ativos ou acessos mensais em planos gratuitos. O Streamlit Community Cloud permite acessos ilimitados sem custo.
3. **Persistência e Usabilidade Avançada:** Permite pré-configurar a URL da planilha do usuário nas variáveis de ambiente (*Secrets*), eliminando a necessidade de redigitar o link a cada acesso, ao mesmo tempo que mantém a flexibilidade para o usuário conectar outra planilha se desejar.

---

## 📋 Requisitos para Funcionamento

### 1. Google Forms & Estrutura da Planilha
O formulário de entrada (e a planilha do Google Sheets vinculada) deve conter as seguintes colunas no cabeçalho:
* `Carimbo de data/hora` (ou `Data`)
* `Data`
* `Categoria`
* `Descrição breve`
* `Valor`
* `Método de pagamento`
* `Essencial x Supérfluo` (Escala numérica de 1 a 5)

---

## 🔑 Detalhamento: Criação da API e Conta de Serviço no Google Cloud

Para que o aplicativo possa **gravar novos registros** na planilha do Google Sheets de forma transparente (sem exigir que cada usuário faça login no Google), utilizamos uma **Conta de Serviço (Service Account)**.

### Passo a Passo Técnico

1. **Acessar o Console:** Entre no [Google Cloud Console](https://console.cloud.google.com/) e crie um projeto (ex: `gestao-diaria-de-gastos`).
2. **Ativar as APIs necessárias:**
   * Acesse a página da [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com) e clique em **Ativar**.
   * Acesse a página da [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) e clique em **Ativar**.
3. **Criar a Conta de Serviço:**
   * Vá para a página de [Contas de Serviço no IAM](https://console.cloud.google.com/iam-admin/serviceaccounts).
   * Clique em **+ Criar Conta de Serviço** no menu superior.
   * Defina um nome (ex: `bot-streamlight`) e atribua o papel (role) de **Editor**.
4. **Gerar a Chave JSON:**
   * Na lista de contas de serviço, clique sobre o e-mail da conta criada (`bot-streamlight@...`).
   * Vá para a aba **Chaves** -> **Adicionar Chave** -> **Criar nova chave**.
   * Selecione o formato **JSON** e confirme. O arquivo `.json` com as credenciais privadas será baixado no computador.
5. **Permissão na Planilha (Obrigatório):**
   * Abra a sua planilha do Google Sheets.
   * Clique no botão **Compartilhar** no canto superior direito.
   * Copie o e-mail da conta de serviço (campo `client_email` do JSON, ex: `bot-streamlight@gestao-diaria-de-gastos.iam.gserviceaccount.com`).
   * Cole esse e-mail na janela de compartilhamento e conceda permissão de **Editor**.

---

### 🗺️ Fluxo de Integração

| Etapa | Plataforma | Ação Requerida | Resultado Esperado |
| :---: | :--- | :--- | :--- |
| **1** | **Google Cloud** | Ativar APIs (*Sheets* e *Drive*) e criar a *Service Account* | Download do arquivo `chave.json` |
| **2** | **Google Sheets** | Compartilhar planilha com o e-mail `client_email` do robô | Permissão de **Editor** concedida ao robô |
| **3** | **Streamlit Cloud** | Inserir as credenciais e a URL padrão na aba **Secrets** em TOML | App carrega pronto e grava registros |

---

## 🔐 Configuração das Secrets no Streamlit Cloud

Para garantir total segurança e **não expor a chave privada (`private_key`) publicamente no GitHub**, armazenamos as credenciais e o link da planilha no painel do Streamlit Cloud.

### 🛠️ Guia de Navegação no Painel

```text
[share.streamlit.io] 
       │
       ├──► 1. Localize o App "Gestão de Gastos"
       │
       ├──► 2. Clique em "Manage app" (canto inferior direito) 
       │       ou nos três pontinhos (⋮) no painel
       │
       ├──► 3. Clique no ícone de Engrenagem (⚙️ Settings)
       │
       └──► 4. Abra a aba "Secrets" no menu lateral esquerdo

       default_sheet_url = "[https://docs.google.com/spreadsheets/d/1NJ4sLPZ1VHxmpSOyqMw7cXfIJBl9yaVVok1QQofHs1Q/edit?usp=sharing](https://docs.google.com/spreadsheets/d/1NJ4sLPZ1VHxmpSOyqMw7cXfIJBl9yaVVok1QQofHs1Q/edit?usp=sharing)"

[gcp_service_account]
type = "service_account"
project_id = "gestao-diaria-de-gastos"
private_key_id = "eb22288f069648bcd079b76f3a57b0a6b7ad52cd"
private_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDM6kHAwwT1ANXD
...conteudo_completo_da_sua_chave_privada...
-----END PRIVATE KEY-----"""
client_email = "bot-streamlight@gestao-diaria-de-gastos.iam.gserviceaccount.com"
client_id = "102828967827973947682"
auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
client_x509_cert_url = "[https://www.googleapis.com/robot/v1/metadata/x509/bot-streamlight%40gestao-diaria-de-gastos.iam.gserviceaccount.com](https://www.googleapis.com/robot/v1/metadata/x509/bot-streamlight%40gestao-diaria-de-gastos.iam.gserviceaccount.com)"
universe_domain = "googleapis.com"

### Arquivo Completo de Secrets (Formato TOML)

O arquivo de configurações abaixo deve ser colado na íntegra na aba **Secrets** do Streamlit Cloud. Esta estrutura garante o **carregamento automático da sua planilha padrão** assim que o aplicativo é aberto, ao mesmo tempo em que mantém para o usuário a alternativa de digitar a URL de outra planilha na barra lateral se desejar.

```toml
default_sheet_url = "[https://docs.google.com/spreadsheets/d/1NJ4sLPZ1VHxmpSOyqMw7cXfIJBl9yaVVok1QQofHs1Q/edit?usp=sharing](https://docs.google.com/spreadsheets/d/1NJ4sLPZ1VHxmpSOyqMw7cXfIJBl9yaVVok1QQofHs1Q/edit?usp=sharing)"

[gcp_service_account]
type = "service_account"
project_id = "gestao-diaria-de-gastos"
private_key_id = "eb22288f069648bcd079b76f3a57b0a6b7ad52cd"
private_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDM6kHAwwT1ANXD
...conteudo_completo_da_sua_chave_privada...
-----END PRIVATE KEY-----"""
client_email = "bot-streamlight@gestao-diaria-de-gastos.iam.gserviceaccount.com"
client_id = "102828967827973947682"
auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
client_x509_cert_url = "[https://www.googleapis.com/robot/v1/metadata/x509/bot-streamlight%40gestao-diaria-de-gastos.iam.gserviceaccount.com](https://www.googleapis.com/robot/v1/metadata/x509/bot-streamlight%40gestao-diaria-de-gastos.iam.gserviceaccount.com)"
universe_domain = "googleapis.com"

```

---

## ⚠️ Pontos Sensíveis do Código (`app.py`)

A arquitetura do código Python traz soluções específicas para garantir estabilidade e usabilidade:

1. **Persistência de Usabilidade (`st.secrets.get`):** O app lê a chave `default_sheet_url` configurada nas Secrets e preenche previamente o campo da barra lateral. O usuário não precisa colar o link toda vez que entra, mas retém a liberdade de trocar o link se quiser.
2. **Tratamento Robusto de Moeda (`clean_currency_to_float`):** Utiliza Expressões Regulares (Regex) para higienizar valores em texto (removendo `R$`, espaços e convertendo vírgulas em pontos), prevenindo erros de cálculo numérico no Pandas.
3. **Autenticação Flexível (`get_gspread_client`):** A função recupera as credenciais do ambiente `st.secrets` com tratamento automático para a substituição de quebras de linha (`\n`) na `private_key`, evitando rejeições de handshake com a API do Google.
4. **Mapeamento Semântico (Escala 1 a 5):** Transforma os números digitados no formulário em legendas explicativas no gráfico de rosca (`1 - Muito Supérfluo` a `5 - Muito Essencial`), mantendo a ordenação lógica e visual.
5. **Gerenciamento de Cache (`st.cache_data` e `st.rerun`):** Define um tempo de vida (TTL) curto para a leitura e força a limpeza de cache após a inclusão de um novo lançamento, atualizando o painel de métricas instantaneamente.

---

## 🛠️ Arquivos do Repositório

* `app.py`: Código-fonte principal da aplicação em Streamlit.
* `requirements.txt`: Lista de dependências Python para o servidor (`streamlit`, `pandas`, `plotly`, `gspread`).
* `README.md`: Documentação e instruções de implantação do projeto.
