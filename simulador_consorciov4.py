import streamlit as st
import pandas as pd
import numpy as np
import locale

# Configurar locale para formato brasileiro
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

st.set_page_config(page_title="Simulador de Consórcio", layout="wide")

# --- Logo da empresa ---
st.image(
    "https://pequodinvestimentos.com/wp-content/uploads/2023/10/Pequod-Investimentos-Agente-XP-branco.svg",
    width=250
)

# --- CSS personalizado ---
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-size: 20px;
        }
        .stNumberInput > div > div > input {
            text-align: right;
        }
    </style>
""", unsafe_allow_html=True)

# --- Título ---
st.title("📟 Simulador de Consórcio")

# --- Entradas do usuário ---
col1, col2 = st.columns(2)

with col1:
    valor_credito = st.number_input("Valor do crédito (R$)", min_value=0.0, step=1000.0, format="%.2f")
    taxa_adm = st.number_input("Taxa de administração (%)", min_value=0.0, step=0.1, format="%.2f") / 100
    seguro_prestamista = st.number_input("Seguro prestamista (%)", min_value=0.0, step=0.0001, format="%.4f") / 100
    fundo_reserva = st.number_input("Fundo de reserva (%)", min_value=0.0, step=0.1, format="%.2f") / 100
    tipo_estrategia = st.selectbox("Tipo de estratégia", ["Tradicional", "Alavancagem"])

with col2:
    prazo_meses = st.number_input("Prazo total (meses)", min_value=1, step=1)
    prazo_contemplacao = st.number_input("Prazo de contemplação (meses)", min_value=0, max_value=prazo_meses, step=1)
    tipo_consorcio = st.selectbox("Tipo de consórcio", ["Imóvel", "Veículo"])

# Lance será definido após cálculo do saldo devedor
lance_proprio = st.number_input("Lance com recursos próprios (R$)", min_value=0.0, step=100.0, format="%.2f")

# --- Inputs extras para Alavancagem ---
if tipo_estrategia == "Alavancagem":
    tipo_investimento = st.selectbox("Tipo de investimento", ["Prefixado", "Inflação", "Pós-fixado (% CDI)"])
    if tipo_investimento in ["Prefixado", "Inflação"]:
        taxa_juros = st.number_input("Taxa de juros anual (%)", min_value=0.0, step=0.1, format="%.2f") / 100
    else:
        perc_cdi = st.number_input("% do CDI", min_value=0.0, step=1.0, format="%.2f") / 100
        cdi_estimado = st.number_input("CDI estimado ao ano (%)", min_value=0.0, step=0.1, format="%.2f") / 100

# --- Botão de Simulação ---
if st.button("Simular"):
    # ----- Cálculo das parcelas -----
    taxa_periodo = taxa_adm + fundo_reserva + seguro_prestamista
    prazo_anos = prazo_meses / 12
    indice_medio = 0.065 if tipo_consorcio == "Imóvel" else 0.045
    nome_indice = "INCC" if tipo_consorcio == "Imóvel" else "IPCA"

    total_pagar = valor_credito * (1 + taxa_periodo)
    parcela_cheia = total_pagar / prazo_meses
    amortizacao_contemplacao = parcela_cheia * prazo_contemplacao
    saldo_devedor = total_pagar - amortizacao_contemplacao
    parcelas_restantes = prazo_meses - prazo_contemplacao
    parcela_apos_contemplacao = saldo_devedor / parcelas_restantes if parcelas_restantes > 0 else 0.0

    # Corrigir saldo devedor pelo índice no momento da contemplação
    anos_corrigidos = prazo_contemplacao // 12
    saldo_devedor_corrigido = saldo_devedor * ((1 + indice_medio) ** anos_corrigidos)

    # --- Validação do lance ---
    if lance_proprio > saldo_devedor_corrigido:
        st.error(f"O lance com recursos próprios (R$ {lance_proprio:,.2f}) não pode ser maior que o saldo devedor na contemplação (R$ {saldo_devedor_corrigido:,.2f})")
        st.stop()

    saldo_devedor_pos_lance = saldo_devedor_corrigido - lance_proprio
    parcela_apos_contemplacao = saldo_devedor_pos_lance / parcelas_restantes if parcelas_restantes > 0 else 0.0

    # ----- Detalhamento das parcelas -----
    parcelas = []
    valor_total_parcelas = 0.0

    for i in range(1, prazo_meses + 1):
        valor_parcela = parcela_cheia if i <= prazo_contemplacao else parcela_apos_contemplacao
        anos_passados = (i - 1) // 12
        correcao = valor_parcela * (indice_medio * anos_passados) if anos_passados > 0 else 0.0
        total = valor_parcela + correcao
        parcelas.append({
            "Número da parcela": i,
            "Valor da parcela (R$)": valor_parcela,
            "Correção monetária (R$)": correcao,
            "Total (R$)": total
        })
        valor_total_parcelas += total

    df_parcelas = pd.DataFrame(parcelas).round(2)

    # ----- Valores auxiliares -----
    valor_credito_corrigido = valor_credito * ((1 + indice_medio) ** anos_corrigidos)
    fundo_reserva_reais = valor_credito * fundo_reserva
    custo_total = valor_total_parcelas + lance_proprio - fundo_reserva_reais
    custo_real = custo_total - valor_credito_corrigido

    # ----- Análise de Alavancagem -----
    if tipo_estrategia == "Alavancagem":
        valor_investido = valor_credito_corrigido - lance_proprio
        meses_invest = prazo_meses - prazo_contemplacao

        if tipo_investimento == "Pós-fixado (% CDI)":
            taxa_bruta_aa = perc_cdi * cdi_estimado
        elif tipo_investimento == "Inflação":
            taxa_bruta_aa = taxa_juros + 0.045
        else:
            taxa_bruta_aa = taxa_juros

        taxa_mensal = (1 + taxa_bruta_aa) ** (1/12) - 1
        montante_bruto = valor_investido * (1 + taxa_mensal) ** meses_invest
        rendimento_bruto = montante_bruto - valor_investido

        if meses_invest <= 6:
            ir = 0.225
        elif meses_invest <= 12:
            ir = 0.20
        elif meses_invest <= 24:
            ir = 0.175
        else:
            ir = 0.15

        imposto = rendimento_bruto * ir
        rendimento_liquido = rendimento_bruto - imposto
        montante_liquido = montante_bruto - imposto
        resultado_liquido = montante_liquido - custo_real

    # ----- Exibição dos Resultados -----
    st.subheader("📊 Resultado da Simulação")

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### 🔢 Dados Gerais")
        st.write(f"**Prazo em anos:** {prazo_anos:.2f}")
        st.write(f"**Índice de correção:** {nome_indice} ({indice_medio*100:.2f}% a.a.)")
        st.write(f"**1ª Parcela:** R$ {df_parcelas.loc[0, 'Total (R$)']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        if prazo_contemplacao < prazo_meses:
            st.write(f"**Parcela após contemplação:** R$ {df_parcelas.loc[prazo_contemplacao, 'Total (R$)']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"**Total pago:** R$ {custo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"**Crédito corrigido na contemplação:** R$ {valor_credito_corrigido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"**Custo real:** R$ {custo_real:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    with colB:
        if tipo_estrategia == "Alavancagem":
            st.markdown("### 🚀 Análise de Alavancagem")
            st.write(f"**Prazo do investimento:** {meses_invest} meses")
            if tipo_investimento == "Inflação":
                st.write(f"**Índice de correção:** IPCA (4,50% a.a)")
            st.write(f"**Valor investido:** R$ {valor_investido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.write(f"**Rendimento bruto:** R$ {rendimento_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.write(f"**Imposto de renda:** R$ {imposto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.write(f"**Montante líquido:** R$ {montante_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            if resultado_liquido >= 0:
                st.success(f"**Resultado da alavancagem:** R$ {resultado_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                st.error(f"**Resultado da alavancagem:** R$ {resultado_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # ----- Tabela de Parcelas -----
    st.subheader("📋 Detalhamento das Parcelas")
    for col in ["Valor da parcela (R$)", "Correção monetária (R$)", "Total (R$)"]:
        df_parcelas[col] = df_parcelas[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.dataframe(df_parcelas, use_container_width=True, hide_index=True)
