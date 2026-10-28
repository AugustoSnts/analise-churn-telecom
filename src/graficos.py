"""
Gráficos do dashboard (Plotly) com tema escuro e paleta própria.

Paleta:
    ROXO     → permaneceu / churn abaixo ou na média
    LARANJA  → cancelou / churn acima da média
"""

import numpy as np
import plotly.express as px

# ---------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------
ROXO = "#8B5CF6"
ROXO_CLARO = "#C4B5FD"
LARANJA = "#FB923C"
TEXTO = "#E5E7EB"
GRADE = "#2B3040"
FUNDO_CARD = "#171A23"
BORDA = "#2F3446"

ROTULO_ACIMA = "Acima da média geral"
ROTULO_ABAIXO = "Abaixo ou na média geral"

CORES_POSICAO = {ROTULO_ACIMA: LARANJA, ROTULO_ABAIXO: ROXO}
CORES_SITUACAO = {"Cancelou": LARANJA, "Permaneceu": ROXO}


def _aplica_tema(fig, titulo, altura=380):
    """Aplica o visual escuro padrão a qualquer figura."""
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=titulo, x=0.0, xanchor="left", font=dict(size=16, color=TEXTO)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXTO, size=13),
        height=altura,
        margin=dict(l=10, r=10, t=90, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
    )
    fig.update_xaxes(gridcolor=GRADE, zerolinecolor=GRADE)
    fig.update_yaxes(gridcolor=GRADE, zerolinecolor=GRADE)
    return fig


def grafico_taxa_por_grupo(resumo, coluna, titulo, taxa_ref, rotulo=None, horizontal=False):
    """
    Barras da taxa de churn por grupo, coloridas pela posição em relação à média geral.
    """
    dados = resumo.reset_index()
    dados[coluna] = dados[coluna].astype(str)

    dados["Posição"] = np.where(dados["taxa_churn"] > taxa_ref, ROTULO_ACIMA, ROTULO_ABAIXO)

    ordem = dados[coluna].tolist()

    argumentos = dict(
        data_frame=dados,
        color="Posição",
        color_discrete_map=CORES_POSICAO,
        category_orders={coluna: ordem},
        text_auto=".1%",
        hover_data={"clientes": ":,", "cancelaram": ":,", "taxa_churn": ":.1%", "Posição": False},
        labels={"taxa_churn": "Taxa de churn", coluna: rotulo or coluna,
                "clientes": "Clientes", "cancelaram": "Cancelaram"},
    )

    limite = max(float(dados["taxa_churn"].max()), taxa_ref) * 1.25
    anotacao = dict(
        line_dash="dash", line_color=ROXO_CLARO, annotation_text=f"Média geral: {taxa_ref:.1%}",
        annotation_font_color=ROXO_CLARO, annotation_position="top right",
    )

    if horizontal:
        fig = px.bar(x="taxa_churn", y=coluna, orientation="h", **argumentos)
        fig.add_vline(x=taxa_ref, **anotacao)
        fig.update_xaxes(range=[0, limite], tickformat=".0%")
        fig.update_yaxes(autorange="reversed")
        altura = 90 + 55 * len(dados)
    else:
        fig = px.bar(x=coluna, y="taxa_churn", **argumentos)
        fig.add_hline(y=taxa_ref, **anotacao)
        fig.update_yaxes(range=[0, limite], tickformat=".0%")
        altura = 380

    fig.update_traces(textposition="outside", cliponaxis=False, textfont_color=TEXTO, marker_line_width=0)
    return _aplica_tema(fig, titulo, altura)


def grafico_boxplot_tenure(df):
    """Boxplot do tempo como cliente: cancelou x permaneceu."""
    fig = px.box(
        df, x="Situacao", y="tenure", color="Situacao",
        color_discrete_map=CORES_SITUACAO,
        category_orders={"Situacao": ["Cancelou", "Permaneceu"]},
        labels={"Situacao": "Situação", "tenure": "Meses como cliente"},
    )
    fig.update_layout(showlegend=False)
    return _aplica_tema(fig, "Tempo como cliente: quem cancelou x quem permaneceu")


def grafico_histograma_cobranca(df):
    """Distribuição da cobrança mensal comparando os dois grupos."""
    fig = px.histogram(
        df, x="MonthlyCharges", color="Situacao",
        color_discrete_map=CORES_SITUACAO,
        category_orders={"Situacao": ["Cancelou", "Permaneceu"]},
        barmode="overlay",
        opacity=0.65,
        histnorm="percent",
        nbins=30,
        labels={"MonthlyCharges": "Cobrança mensal", "Situacao": "Situação"},
    )
    fig.update_yaxes(title_text="% dos clientes do grupo")
    return _aplica_tema(fig, "Distribuição da cobrança mensal")