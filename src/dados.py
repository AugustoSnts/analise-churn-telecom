"""
Carga e limpeza da base Telco Customer Churn.
As mesmas regras de limpeza do notebook (eda.ipynb) ficam reunidas aqui.
"""

import pandas as pd

# ---------------------------------------------------------------
# Constantes da base
# ---------------------------------------------------------------

COLUNAS_OBRIGATORIAS = [
    "customerID", "SeniorCitizen", "tenure", "Contract", "InternetService",
    "PaymentMethod", "MonthlyCharges", "TotalCharges", "Churn",
]

# Tradução dos valores para exibição no dashboard
MAPA_CONTRATO = {"Month-to-month": "Mensal", "One year": "1 ano", "Two year": "2 anos"}
MAPA_INTERNET = {"DSL": "DSL", "Fiber optic": "Fibra óptica", "No": "Sem internet"}
MAPA_PAGAMENTO = {
    "Electronic check": "Cheque eletrônico",
    "Mailed check": "Cheque pelo correio",
    "Bank transfer (automatic)": "Transferência (automática)",
    "Credit card (automatic)": "Cartão de crédito (automático)",
}
MAPA_SITUACAO = {"Yes": "Cancelou", "No": "Permaneceu"}

ORDEM_CONTRATO = list(MAPA_CONTRATO.values())
ORDEM_INTERNET = list(MAPA_INTERNET.values())
ORDEM_PAGAMENTO = list(MAPA_PAGAMENTO.values())
ORDEM_SITUACAO = list(MAPA_SITUACAO.values())

# Faixas de tempo como cliente
LIMITES_FAIXA_TENURE = [-1, 12, 24, 48, 72]
ROTULOS_FAIXA_TENURE = ["0-12 meses", "13-24 meses", "25-48 meses", "49-72 meses"]


# ---------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------

def _traduz(df, coluna_origem, coluna_destino, mapa):
    """Cria coluna_destino traduzindo coluna_origem com o dicionário mapa."""
    traduzido = df[coluna_origem].map(mapa)

    if traduzido.isna().any():
        inesperados = sorted(df.loc[traduzido.isna(), coluna_origem].astype(str).unique().tolist())
        raise ValueError(f"Valores inesperados em '{coluna_origem}': {inesperados}")

    df[coluna_destino] = traduzido


# ---------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------

def carregar_dados(origem):
    """
    Lê o CSV, valida, limpa e retorna um DataFrame pronto para análise.

    Colunas derivadas criadas:
      - Churn_Flag
      - Situacao, Contrato, Internet, Pagamento (em português)
      - faixa_tenure
    """
    df_bruto = pd.read_csv(origem)

    # Validação de estrutura
    faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in df_bruto.columns]
    if faltantes:
        raise ValueError(
            f"O arquivo não parece ser a base Telco Customer Churn. Colunas ausentes: {faltantes}"
        )

    df = df_bruto.copy()

    # Remove espaços em colunas de texto
    for coluna in df.select_dtypes(exclude="number").columns:
        df[coluna] = df[coluna].str.strip()

    # TotalCharges: texto → número
    vazios_antes = int((df["TotalCharges"] == "").sum() + df["TotalCharges"].isna().sum())
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    nulos_depois = int(df["TotalCharges"].isna().sum())

    if vazios_antes != nulos_depois:
        raise ValueError("TotalCharges contém valores inválidos além dos espaços em branco.")

    ausentes = df["TotalCharges"].isna()
    if (df.loc[ausentes, "tenure"] != 0).any():
        raise ValueError("Há TotalCharges ausente em cliente com tenure > 0; revise a limpeza.")
    df["TotalCharges"] = df["TotalCharges"].fillna(0)

    # Churn_Flag
    valores_churn = set(df["Churn"].unique())
    if valores_churn != {"Yes", "No"}:
        raise ValueError(f"Valores inesperados em Churn: {sorted(valores_churn)}")
    df["Churn_Flag"] = df["Churn"].map({"Yes": 1, "No": 0}).astype(int)

    # Integridade
    if not df["customerID"].is_unique:
        raise ValueError("customerID repetido: a base tem clientes duplicados.")

    # Colunas de exibição em português
    _traduz(df, "Churn", "Situacao", MAPA_SITUACAO)
    _traduz(df, "Contract", "Contrato", MAPA_CONTRATO)
    _traduz(df, "InternetService", "Internet", MAPA_INTERNET)
    _traduz(df, "PaymentMethod", "Pagamento", MAPA_PAGAMENTO)

    # Faixas de tenure
    df["faixa_tenure"] = pd.cut(df["tenure"], bins=LIMITES_FAIXA_TENURE, labels=ROTULOS_FAIXA_TENURE)
    if df["faixa_tenure"].isna().any():
        raise ValueError("Há clientes com tenure fora das faixas definidas; revise os limites.")

    return df