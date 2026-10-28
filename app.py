# =====================================================================
# Dashboard de Análise de Churn de Clientes — Streamlit
# Etapa 5 do projeto
#
# Como rodar (na pasta raiz do projeto):
#     streamlit run app.py
#
# Organização do código:
#   Bloco 1  : importações e configuração da página
#   Bloco 2  : estilo (CSS)
#   Bloco 3  : carga dos dados
#   Bloco 4  : sidebar e filtros
#   Bloco 5  : cartões de indicadores (KPIs)
#   Bloco 6  : página 1 — Visão geral
#   Bloco 7  : página 2 — Perfil de quem cancela
#   Bloco 8  : página 3 — Recomendações
#   Bloco 9  : página 4 — Dados e exportação
#   Bloco 10 : função principal
#
# Cálculos em src/analise.py | Gráficos em src/graficos.py
# =====================================================================


# --- Bloco 1: Importações e configuração da página ---

from pathlib import Path

import streamlit as st

from src.analise import (
    aplicar_filtros,
    calcula_kpis,
    gera_insights,
    perfil_por_situacao,
    ranking_segmentos,
    resumo_churn,
)
from src.dados import (
    ORDEM_CONTRATO,
    ORDEM_INTERNET,
    ORDEM_PAGAMENTO,
    ORDEM_SITUACAO,
    carregar_dados,
)
from src.graficos import (
    BORDA,
    FUNDO_CARD,
    LARANJA,
    ROXO,
    ROXO_CLARO,
    grafico_boxplot_tenure,
    grafico_histograma_cobranca,
    grafico_taxa_por_grupo,
)

# st.set_page_config deve ser o primeiro comando Streamlit do script
st.set_page_config(
    page_title="Análise de Churn",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Caminho do CSV relativo ao arquivo app.py
CAMINHO_CSV = Path(__file__).parent / "data" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"

# Página da base no Kaggle (usada nas instruções de upload)
URL_KAGGLE = "https://www.kaggle.com/datasets/blastchar/telco-customer-churn"

# Tamanho mínimo de grupo para o ranking de principais fatores
MIN_CLIENTES_RANKING = 100


# --- Bloco 2: Estilo (CSS) ---

def aplica_estilo():
    """Injeta CSS para cartões de KPI e etiquetas dos filtros."""
    css = f"""
    <style>
        /* Cartões de indicadores */
        .metric-card {{
            background-color: {FUNDO_CARD};
            padding: 16px 18px;
            border-radius: 10px;
            border: 1px solid {BORDA};
            border-left: 4px solid {ROXO};
            margin-bottom: 8px;
            min-height: 132px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .metric-card h3 {{
            margin: 0 0 4px 0;
            font-size: 0.92rem;
            font-weight: normal;
            color: #9CA3AF;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .metric-card h2 {{
            margin: 0;
            font-size: 1.9rem;
            font-weight: bold;
            color: #F3F4F6;
            line-height: 1.2;
        }}
        .metric-card .rodape {{
            margin: 6px 0 0 0;
            font-size: 0.82rem;
            color: #9CA3AF;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .metric-card .rodape.alto  {{ color: {LARANJA};    }}
        .metric-card .rodape.baixo {{ color: {ROXO_CLARO}; }}

        /* Etiquetas dos filtros */
        [data-baseweb="tag"] {{
            background-color: {ROXO} !important;
            color: #FFFFFF !important;
            border-radius: 4px !important;
        }}
        [data-baseweb="tag"] svg {{ color: #FFFFFF !important; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# --- Bloco 3: Carga dos dados ---

@st.cache_data(show_spinner="Carregando e validando a base...")
def carrega_dados_cache(caminho_texto):
    return carregar_dados(caminho_texto)


def mostra_instrucoes_upload():
    """
    Mostra, ANTES do campo de envio, como obter e enviar o CSV.
    No app publicado o CSV não está no repositório.
    """
    st.warning(
        "**Base de dados não encontrada.** Este aplicativo não inclui o arquivo CSV, porque a base "
        "pertence aos autores originais. Para ver o dashboard com os dados reais, siga os 3 passos:"
    )
    st.markdown(
        f"""
1. **Baixe** a base no Kaggle: [Telco Customer Churn]({URL_KAGGLE}) (clique em *Download*; o Kaggle
   pode pedir um login gratuito).
2. **Extraia** o arquivo `.zip` baixado. Dentro dele está o arquivo `{CAMINHO_CSV.name}`.
3. **Envie** esse arquivo `.csv` no campo abaixo.
"""
    )
    st.caption(
        "O arquivo é usado só na sua sessão: não é incluído no repositório nem compartilhado com outros "
        "visitantes. Rodando no seu computador? Salve o CSV em `data/` com o nome original e o app o "
        "carrega automaticamente."
    )


def carrega_base():
    """
    Retorna o DataFrame limpo.
    Se o CSV não estiver em data/, mostra as instruções e solicita o upload do arquivo.
    """
    if CAMINHO_CSV.exists():
        try:
            return carrega_dados_cache(str(CAMINHO_CSV))
        except ValueError as erro:
            st.error(f"Os dados não passaram na validação: {erro}")
            st.stop()

    # Reutiliza o DataFrame se já foi carregado via upload nesta sessão
    if "df_upload" in st.session_state:
        return st.session_state["df_upload"]

    mostra_instrucoes_upload()
    arquivo = st.file_uploader("Envie o arquivo CSV da base", type="csv", key="uploader_csv")
    if arquivo is None:
        st.stop()

    try:
        df = carregar_dados(arquivo)
        st.session_state["df_upload"] = df
        st.rerun()
        return df
    except ValueError as erro:
        st.error(
            f"O arquivo enviado não passou na validação: {erro}\n\n"
            "Confira se é o arquivo da base *Telco Customer Churn* (o `.csv` que está dentro do `.zip`)."
        )
        st.stop()


# --- Bloco 4: Sidebar e filtros ---

def _opcoes(df, coluna, ordem):
    """Retorna as opções do filtro na ordem definida, apenas as que existem na base."""
    existentes = set(df[coluna].unique())
    return [item for item in ordem if item in existentes]


def sidebar_filtros(df):
    """
    Desenha os filtros na barra lateral e retorna o DataFrame filtrado.
    Todos os elementos da página usam esse DataFrame.
    """
    st.sidebar.markdown(
        f"""
        <div style="background:{ROXO}; padding:10px; border-radius:6px; text-align:center; margin-bottom:12px;">
            <h3 style="color:white; margin:0;">Análise de Churn</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.header("🔍 Filtros")

    contratos = st.sidebar.multiselect(
        "Tipo de contrato", _opcoes(df, "Contrato", ORDEM_CONTRATO), default=_opcoes(df, "Contrato", ORDEM_CONTRATO)
    )
    internets = st.sidebar.multiselect(
        "Tipo de internet", _opcoes(df, "Internet", ORDEM_INTERNET), default=_opcoes(df, "Internet", ORDEM_INTERNET)
    )
    pagamentos = st.sidebar.multiselect(
        "Forma de pagamento", _opcoes(df, "Pagamento", ORDEM_PAGAMENTO), default=_opcoes(df, "Pagamento", ORDEM_PAGAMENTO)
    )
    situacoes = st.sidebar.multiselect(
        "Situação do cliente", _opcoes(df, "Situacao", ORDEM_SITUACAO), default=_opcoes(df, "Situacao", ORDEM_SITUACAO)
    )

    tenure_min, tenure_max = int(df["tenure"].min()), int(df["tenure"].max())
    faixa = st.sidebar.slider("Tempo como cliente (meses)", tenure_min, tenure_max, (tenure_min, tenure_max))

    st.sidebar.caption("Os filtros valem para cartões, gráficos e tabelas (exceto a página de Recomendações).")

    st.sidebar.markdown("---")
    with st.sidebar.expander("ℹ️ Sobre os filtros", expanded=False):
        st.write(
            "Os filtros se combinam com **E**: o cliente precisa atender a todos ao mesmo tempo. "
            "Se nenhuma opção de um filtro estiver marcada, nenhum cliente é mostrado."
        )

    return aplicar_filtros(df, contratos, internets, pagamentos, situacoes, faixa[0], faixa[1])


# --- Bloco 5: Cartões de indicadores (KPIs) ---

def _card(titulo, valor, rodape, classe=""):
    """Monta o HTML de um cartão de KPI."""
    return (
        f'<div class="metric-card"><h3>{titulo}</h3><h2>{valor}</h2>'
        f'<div class="rodape {classe}">{rodape}</div></div>'
    )


def renderiza_kpis(kpis, filtro_ativo):
    """Exibe os quatro cartões de indicadores."""
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        pct = f"{kpis['pct_da_base']:.1%} da base" if filtro_ativo else "Base completa"
        st.markdown(_card("Total de clientes", f"{kpis['total_clientes']:,}", pct), unsafe_allow_html=True)

    with c2:
        rodape = (
            f"de {kpis['total_clientes']:,} no filtro atual"
            if filtro_ativo
            else "Base completa"
        )
        st.markdown(
            _card("Cancelaram", f"{kpis['clientes_churn']:,}", rodape),
            unsafe_allow_html=True,
        )

    with c3:
        dif = kpis["dif_taxa_pp"]
        if not filtro_ativo:
            rodape, classe = "Base completa", ""
        elif dif > 0.05:
            rodape, classe = f"▲ +{dif:.1f} p.p. vs base completa", "alto"
        elif dif < -0.05:
            rodape, classe = f"▼ {dif:.1f} p.p. vs base completa", "baixo"
        else:
            rodape, classe = "≈ igual à base completa", ""
        st.markdown(_card("Taxa de churn", f"{kpis['taxa_churn']:.1%}", rodape, classe), unsafe_allow_html=True)

    with c4:
        dif_c = kpis["dif_cobranca"]
        rodape = "Base completa" if not filtro_ativo else f"{'▲ +' if dif_c >= 0 else '▼ '}{dif_c:.2f} vs base completa"
        st.markdown(_card("Cobrança mensal média", f"{kpis['cobranca_media']:.2f}", rodape), unsafe_allow_html=True)

    if filtro_ativo:
        st.caption(
            f"Indicadores calculados para os **{kpis['total_clientes']:,}** clientes do filtro atual "
            f"({kpis['pct_da_base']:.1%} dos {kpis['total_base']:,} da base). "
            "Os \"vs base completa\" comparam o filtro com a base inteira."
        )
    else:
        st.caption(f"Indicadores calculados sobre a base completa ({kpis['total_base']:,} clientes).")


# --- Bloco 6: Página 1 — Visão geral ---

def pagina_visao_geral(df_filtrado, taxa_base):
    st.subheader("Onde o churn é maior ou menor que a média?")
    st.caption(
        "Barras **laranja**: taxa acima da média da base completa (linha tracejada). "
        "Barras **roxas**: abaixo ou na média. Passe o mouse para ver o tamanho de cada grupo."
    )

    col1, col2 = st.columns(2)
    with col1:
        resumo = resumo_churn(df_filtrado, "Contrato", taxa_base)
        fig = grafico_taxa_por_grupo(resumo, "Contrato", "Taxa de churn por tipo de contrato", taxa_base,
                                     rotulo="Tipo de contrato")
        st.plotly_chart(fig, width="stretch", theme=None)

    with col2:
        resumo = resumo_churn(df_filtrado, "Internet", taxa_base)
        fig = grafico_taxa_por_grupo(resumo, "Internet", "Taxa de churn por tipo de internet", taxa_base,
                                     rotulo="Tipo de internet")
        st.plotly_chart(fig, width="stretch", theme=None)

    resumo = resumo_churn(df_filtrado, "Pagamento", taxa_base)
    fig = grafico_taxa_por_grupo(resumo, "Pagamento", "Taxa de churn por forma de pagamento", taxa_base,
                                 rotulo="Forma de pagamento", horizontal=True)
    st.plotly_chart(fig, width="stretch", theme=None)

    st.subheader("Principais fatores: segmentos com maior taxa de churn")
    st.caption(
        f"Só entram grupos com pelo menos {MIN_CLIENTES_RANKING} clientes. "
        "Taxa alta indica **associação**, não causa."
    )
    ranking = ranking_segmentos(df_filtrado, taxa_base, min_clientes=MIN_CLIENTES_RANKING)
    if ranking.empty:
        st.info("Nenhum grupo atinge o tamanho mínimo com os filtros atuais.")
    else:
        st.dataframe(
            ranking,
            hide_index=True,
            width="stretch",
            column_config={
                "Taxa de churn (%)": st.column_config.ProgressColumn(
                    "Taxa de churn", format="%.1f", min_value=0, max_value=100
                ),
                "Dif. vs base (p.p.)": st.column_config.NumberColumn("Dif. vs base (p.p.)", format="%.1f"),
                "Clientes": st.column_config.NumberColumn("Clientes", format="%d"),
                "Cancelaram": st.column_config.NumberColumn("Cancelaram", format="%d"),
            },
        )


# --- Bloco 7: Página 2 — Perfil de quem cancela ---

def pagina_perfil(df_filtrado, taxa_base):
    st.subheader("Como é o cliente que cancela?")
    st.caption("Comparação entre quem cancelou e quem permaneceu, dentro do filtro atual.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Perfil comparado**")
        st.dataframe(perfil_por_situacao(df_filtrado), width="stretch")
        st.caption("Compare média e mediana: se forem diferentes, a distribuição tem cauda.")
    with col2:
        st.plotly_chart(grafico_boxplot_tenure(df_filtrado), width="stretch", theme=None)

    col3, col4 = st.columns(2)
    with col3:
        resumo = resumo_churn(df_filtrado, "faixa_tenure", taxa_base, ordenar_por_taxa=False)
        fig = grafico_taxa_por_grupo(resumo, "faixa_tenure", "Taxa de churn por tempo como cliente", taxa_base,
                                     rotulo="Tempo como cliente")
        st.plotly_chart(fig, width="stretch", theme=None)
    with col4:
        st.plotly_chart(grafico_histograma_cobranca(df_filtrado), width="stretch", theme=None)


# --- Bloco 8: Página 3 — Recomendações ---

def pagina_recomendacoes(df_base):
    st.subheader("Hipóteses de retenção")
    st.info(
        "Os números abaixo são calculados da base completa (não mudam com os filtros). "
        "As interpretações e ações são hipóteses para testar, não resultados garantidos."
    )

    insights = gera_insights(df_base)
    if not insights:
        st.warning("Nenhum dos padrões esperados foi observado nesta base, então nenhum insight foi gerado.")
        return

    for insight in insights:
        with st.container(border=True):
            st.markdown(f"#### {insight['titulo']}")
            st.markdown(f"**Evidência observada:** {insight['evidencia']}")
            st.markdown(f"**Interpretação prudente:** {insight['interpretacao']}")
            st.markdown(f"**Possível ação a testar:** {insight['acao']}")
            st.markdown(f"**Como avaliar:** {insight['avaliacao']}")
            st.markdown(f"**Ressalva:** {insight['ressalva']}")
            st.caption(f"Fonte no dashboard: {insight['fonte']}")

    st.caption(
        "Esta análise é descritiva: mostra associações e não mede o efeito de nenhuma ação. "
        "Para avaliar uma ação de retenção seria preciso acompanhar os indicadores ao longo do tempo "
        "e comparar grupos semelhantes, com e sem a ação."
    )
    

# --- Bloco 9: Página 4 — Dados e exportação ---

def pagina_dados(df_filtrado):
    st.subheader("Dados do filtro atual")
    st.dataframe(df_filtrado, width="stretch", height=420)

    csv = df_filtrado.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="💾 Baixar CSV do filtro atual",
        data=csv,
        file_name="clientes_filtrados.csv",
        mime="text/csv",
    )


# --- Bloco 10: Função principal ---

def main():
    aplica_estilo()
    df_base = carrega_base()
    df_filtrado = sidebar_filtros(df_base)

    st.title("📉 Análise de Churn de Clientes")
    st.caption(
        "Base: Telco Customer Churn (Kaggle). Análise descritiva: as diferenças mostradas são "
        "associações observadas nos dados e não provam causa e efeito."
    )

    if df_filtrado.empty:
        st.warning("⚠️ Nenhum cliente atende aos filtros selecionados. Ajuste os filtros na barra lateral.")
        st.stop()

    kpis = calcula_kpis(df_filtrado, df_base)
    filtro_ativo = len(df_filtrado) != len(df_base)
    renderiza_kpis(kpis, filtro_ativo)
    st.markdown("---")

    taxa_base = kpis["taxa_churn_base"]

    aba_geral, aba_perfil, aba_reco, aba_dados = st.tabs(
        ["📊 Visão geral", "👤 Perfil de quem cancela", "💡 Recomendações", "📄 Dados"]
    )
    with aba_geral:
        pagina_visao_geral(df_filtrado, taxa_base)
    with aba_perfil:
        pagina_perfil(df_filtrado, taxa_base)
    with aba_reco:
        pagina_recomendacoes(df_base)
    with aba_dados:
        pagina_dados(df_filtrado)

    st.markdown("---")
    with st.expander("ℹ️ Sobre este dashboard", expanded=False):
        st.markdown(
            """
            **Definições**
            - **Taxa de churn:** clientes que cancelaram ÷ total de clientes do conjunto analisado.
            - **p.p. (ponto percentual):** diferença entre duas taxas. De 20% para 35% são 15 p.p.
            - **Cobrança mensal média:** média da coluna `MonthlyCharges`.
            - **Tempo como cliente:** coluna `tenure`, em meses.

            **Fonte:** base pública *Telco Customer Churn* (Kaggle, blastchar).

            **Limitações:** análise descritiva; mostra associações, não causas.
            Grupos pequenos têm taxas menos confiáveis (por isso o ranking exige um tamanho mínimo).
            """
        )


if __name__ == "__main__":
    main()