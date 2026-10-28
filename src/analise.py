"""
Cálculos do dashboard: filtros, KPIs, comparações e textos de insight.
Usa apenas pandas (sem Streamlit ou Plotly).
"""

import pandas as pd

from src.dados import ROTULOS_FAIXA_TENURE

# Dimensões usadas nas comparações de churn
DIMENSOES = {
    "Contrato": "Tipo de contrato",
    "Internet": "Tipo de internet",
    "Pagamento": "Forma de pagamento",
    "faixa_tenure": "Tempo como cliente",
}


# ---------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------

def aplicar_filtros(df, contratos, internets, pagamentos, situacoes, tenure_min, tenure_max):
    """
    Retorna apenas as linhas que atendem a todos os filtros (lógica E).
    """
    mascara = (
        df["Contrato"].isin(contratos)
        & df["Internet"].isin(internets)
        & df["Pagamento"].isin(pagamentos)
        & df["Situacao"].isin(situacoes)
        & df["tenure"].between(tenure_min, tenure_max)
    )
    return df[mascara].copy()


# ---------------------------------------------------------------
# Indicadores (cartões)
# ---------------------------------------------------------------

def calcula_kpis(df, df_base):
    """
    Calcula os indicadores do conjunto filtrado e as referências da base completa.
    """
    total = len(df)
    churn = int(df["Churn_Flag"].sum())

    taxa = churn / total if total else 0.0
    cobranca = float(df["MonthlyCharges"].mean()) if total else 0.0

    taxa_base = float(df_base["Churn_Flag"].mean())
    cobranca_base = float(df_base["MonthlyCharges"].mean())

    return {
        "total_clientes": total,
        "clientes_churn": churn,
        "taxa_churn": taxa,
        "taxa_churn_base": taxa_base,
        "dif_taxa_pp": (taxa - taxa_base) * 100,
        "cobranca_media": cobranca,
        "cobranca_media_base": cobranca_base,
        "dif_cobranca": cobranca - cobranca_base,
        "pct_da_base": total / len(df_base) if len(df_base) else 0.0,
        "total_base": len(df_base),
    }


# ---------------------------------------------------------------
# Comparações por grupo
# ---------------------------------------------------------------

def resumo_churn(df, coluna, taxa_referencia, ordenar_por_taxa=True):
    """
    Retorna, por grupo: clientes, cancelaram, taxa_churn e diferença em p.p.
    """
    resumo = (
        df.groupby(coluna, observed=True)
        .agg(
            clientes=("customerID", "count"),
            cancelaram=("Churn_Flag", "sum"),
            taxa_churn=("Churn_Flag", "mean"),
        )
    )
    resumo = resumo.sort_values("taxa_churn", ascending=False) if ordenar_por_taxa else resumo.sort_index()
    resumo["dif_vs_geral_pp"] = (resumo["taxa_churn"] - taxa_referencia) * 100

    if resumo["clientes"].sum() != len(df):
        raise ValueError(f"A coluna '{coluna}' tem valores nulos: os grupos não somam o total.")
    return resumo


def ranking_segmentos(df, taxa_referencia, min_clientes=100, top=8):
    """
    Lista os grupos com maior taxa de churn em todas as dimensões.
    Apenas grupos com pelo menos min_clientes entram no ranking.
    """
    partes = []
    for coluna, rotulo in DIMENSOES.items():
        r = resumo_churn(df, coluna, taxa_referencia, ordenar_por_taxa=False).reset_index()
        r = r.rename(columns={coluna: "Grupo"})
        r["Grupo"] = r["Grupo"].astype(str)
        r.insert(0, "Dimensão", rotulo)
        partes.append(r)

    todos = pd.concat(partes, ignore_index=True)
    todos = todos[todos["clientes"] >= min_clientes]
    todos = todos.sort_values("taxa_churn", ascending=False).head(top)

    return pd.DataFrame({
        "Dimensão": todos["Dimensão"],
        "Grupo": todos["Grupo"],
        "Clientes": todos["clientes"],
        "Cancelaram": todos["cancelaram"],
        "Taxa de churn (%)": todos["taxa_churn"] * 100,
        "Dif. vs base (p.p.)": todos["dif_vs_geral_pp"],
    }).reset_index(drop=True)


def perfil_por_situacao(df):
    """
    Compara o perfil de quem cancelou com o de quem permaneceu.
    """
    colunas = {}

    for situacao, g in df.groupby("Situacao"):
        colunas[situacao] = {
            "Clientes": f"{len(g):,}",
            "Tempo médio como cliente (meses)": f"{g['tenure'].mean():.1f}",
            "Tempo mediano (meses)": f"{g['tenure'].median():.0f}",
            "Cobrança mensal média": f"{g['MonthlyCharges'].mean():.2f}",
            "Cobrança mensal mediana": f"{g['MonthlyCharges'].median():.2f}",
            "% com contrato mensal": f"{(g['Contrato'] == 'Mensal').mean() * 100:.1f}%",
            "% com fibra óptica": f"{(g['Internet'] == 'Fibra óptica').mean() * 100:.1f}%",
            "% com cheque eletrônico": f"{(g['Pagamento'] == 'Cheque eletrônico').mean() * 100:.1f}%",
        }

    tabela = pd.DataFrame(colunas)
    ordem = [c for c in ["Cancelou", "Permaneceu"] if c in tabela.columns]
    return tabela[ordem]


# ---------------------------------------------------------------
# Insights
# ---------------------------------------------------------------

def _taxa_e_tamanho(df, mascara):
    """Retorna taxa de churn e tamanho do grupo definido pela máscara."""
    grupo = df[mascara]
    n = len(grupo)
    taxa = float(grupo["Churn_Flag"].mean()) if n else float("nan")
    return taxa, n


def gera_insights(df_base):
    """
    Gera insights no formato: evidência, interpretação, ação, avaliação, fonte e ressalva.
    Só inclui o insight se o padrão for observado nos dados.
    """
    insights = []

    # Contrato mensal x 2 anos
    taxa_m, n_m = _taxa_e_tamanho(df_base, df_base["Contrato"] == "Mensal")
    taxa_2, n_2 = _taxa_e_tamanho(df_base, df_base["Contrato"] == "2 anos")
    if n_m and n_2 and taxa_m > taxa_2:
        insights.append({
            "titulo": "Contrato mensal concentra mais cancelamentos",
            "evidencia": (
                f"Clientes com contrato mensal apresentam taxa de churn de {taxa_m:.1%} "
                f"({n_m:,} clientes), contra {taxa_2:.1%} nos contratos de 2 anos ({n_2:,} clientes)."
            ),
            "interpretacao": (
                "O contrato mensal está associado a maior churn. Os dados não mostram o motivo: "
                "pode refletir o perfil do cliente, o preço ou apenas a facilidade de sair."
            ),
            "acao": "Testar uma oferta de migração para contrato anual entre clientes do contrato mensal.",
            "avaliacao": (
                "Acompanhar a taxa de churn do grupo que recebeu a oferta e de um grupo comparável "
                "que não recebeu, ao longo de alguns meses."
            ),
            "fonte": "Aba Visão geral, gráfico 'Taxa de churn por tipo de contrato'.",
            "ressalva": (
                "Associação observada. No cruzamento do notebook, a diferença entre contrato mensal "
                "e de 2 anos continua dentro de cada tipo de internet, mas fatores não medidos "
                "(como o motivo do cancelamento) podem influenciar."
            ),
        })

    # Fibra óptica x DSL
    taxa_f, n_f = _taxa_e_tamanho(df_base, df_base["Internet"] == "Fibra óptica")
    taxa_d, n_d = _taxa_e_tamanho(df_base, df_base["Internet"] == "DSL")
    if n_f and n_d and taxa_f > taxa_d:
        cobr_f = df_base.loc[df_base["Internet"] == "Fibra óptica", "MonthlyCharges"].mean()
        cobr_d = df_base.loc[df_base["Internet"] == "DSL", "MonthlyCharges"].mean()
        insights.append({
            "titulo": "Clientes de fibra óptica apresentam taxa de churn maior que os de DSL",
            "evidencia": (
                f"A taxa de churn é de {taxa_f:.1%} na fibra óptica ({n_f:,} clientes) e de "
                f"{taxa_d:.1%} no DSL ({n_d:,} clientes). A cobrança mensal média é de "
                f"{cobr_f:.2f} na fibra e de {cobr_d:.2f} no DSL."
            ),
            "interpretacao": (
                "A fibra está associada a maior churn, mas também a cobrança mais alta; os dados "
                "não separam o efeito do serviço do efeito do preço ou do tipo de contrato."
            ),
            "acao": (
                "Investigar a experiência desses clientes (qualidade, suporte, preço percebido) "
                "por pesquisa de satisfação ou entrevistas."
            ),
            "avaliacao": "Comparar satisfação e churn dos clientes de fibra antes e depois de qualquer melhoria.",
            "fonte": "Aba Visão geral, gráfico 'Taxa de churn por tipo de internet'.",
            "ressalva": (
                "No cruzamento do notebook, a fibra tem churn maior dentro de cada tipo de contrato, "
                "mas pode estar ligada a uma cobrança maior e a outros fatores. Sem o motivo do "
                "cancelamento, não dá para atribuir a diferença ao serviço."
            ),
        })

    # Primeiros meses x clientes antigos
    primeira, ultima = ROTULOS_FAIXA_TENURE[0], ROTULOS_FAIXA_TENURE[-1]
    taxa_p, n_p = _taxa_e_tamanho(df_base, df_base["faixa_tenure"] == primeira)
    taxa_u, n_u = _taxa_e_tamanho(df_base, df_base["faixa_tenure"] == ultima)
    if n_p and n_u and taxa_p > taxa_u:
        insights.append({
            "titulo": "O cancelamento se concentra no início do relacionamento",
            "evidencia": (
                f"Na faixa de {primeira} a taxa de churn é de {taxa_p:.1%} ({n_p:,} clientes), "
                f"contra {taxa_u:.1%} na faixa de {ultima} ({n_u:,} clientes)."
            ),
            "interpretacao": (
                "Clientes mais novos cancelam mais. Os dados não explicam por quê: mostram apenas "
                "que o cancelamento está associado ao início do relacionamento."
            ),
            "acao": (
                "Avaliar ações de acompanhamento no primeiro ano (boas-vindas, contato proativo, "
                "suporte inicial), começando pelos clientes novos de contrato mensal."
            ),
            "avaliacao": "Medir a taxa de churn dos novos clientes que receberam a ação contra um grupo comparável.",
            "fonte": "Aba Perfil de quem cancela, gráfico 'Taxa de churn por tempo como cliente'.",
            "ressalva": (
                "As faixas de tempo foram escolhidas por mim. No cruzamento do notebook, a queda do "
                "churn com o tempo aparece no contrato mensal, mas não nos contratos de 1 ano, e "
                "quase todos os clientes de 0-12 meses têm contrato mensal. A base é um retrato de "
                "um momento, não mostra a trajetória de cada cliente."
            ),
        })

    # Cheque eletrônico x demais formas
    eletronico = df_base["Pagamento"] == "Cheque eletrônico"
    taxa_e, n_e = _taxa_e_tamanho(df_base, eletronico)
    taxa_o, n_o = _taxa_e_tamanho(df_base, ~eletronico)
    if n_e and n_o and taxa_e > taxa_o:
        insights.append({
            "titulo": "Pagamento por cheque eletrônico aparece associado a mais churn",
            "evidencia": (
                f"A taxa de churn é de {taxa_e:.1%} entre clientes que pagam por cheque eletrônico "
                f"({n_e:,} clientes), contra {taxa_o:.1%} nas demais formas de pagamento ({n_o:,} clientes)."
            ),
            "interpretacao": (
                "A associação existe, mas a forma de pagamento pode estar apenas acompanhando outro "
                "fator (como o tipo de contrato). É um ponto para investigar, não uma conclusão."
            ),
            "acao": "Investigar se há atrito no pagamento e testar incentivos ao pagamento automático.",
            "avaliacao": "Comparar o churn de quem migrou para pagamento automático com o de um grupo comparável.",
            "fonte": "Aba Visão geral, gráfico 'Taxa de churn por forma de pagamento'.",
            "ressalva": (
                "No cruzamento do notebook, o cheque eletrônico continua com churn maior dentro de "
                "cada tipo de contrato, mas a diferença é menor que na base toda; ele é mais comum "
                "entre os contratos mensais."
            ),
        })

    return insights