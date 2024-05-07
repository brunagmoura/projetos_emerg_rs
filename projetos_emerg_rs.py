import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
import warnings
import datetime
import calendar
import json
import requests
from dash import Dash, dcc, html, Input, Output
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime as dt, timedelta

warnings.filterwarnings('ignore')

link = "https://sobre-monitor.readthedocs.io/en/latest/"

st.set_page_config(page_title="Monitor endividamento", page_icon=":bar_chart:", layout="wide", initial_sidebar_state="collapsed", 
                   menu_items={'About': f'Para facilitar a sua análise, todos os valores já estão deflacionados!\n\n'
        f'Quer conferir mais detalhes sobre este projeto ou entrar em contato conosco? [Clique aqui]({link})'})

st.subheader("Endividamento em pauta no Congresso Nacional")

st.markdown("<div style='text-align: center; color: #555555; font-size: 1.3em;margin-bottom: 20px;'>Proposições legislativas que se referem à endividamento com tramitação nos últimos 180 dias</div>", unsafe_allow_html=True)

st.markdown("""
<div style='text-align: left; color: #666666; font-size: 1em; background-color: #f0f0f0; padding: 10px; border-radius: 5px;margin-bottom: 20px;'>
    💡&nbsp;&nbsp;&nbsp;A busca utiliza a base de dados da Câmara dos Deputados e se refere aos projetos de lei e medidas provisórias que tenham como palavras-chave termos relacionados ao endividamento da população e das empresas brasileiras. Os resultados são atualizados em tempo real.
</div>
""", unsafe_allow_html=True)

#API Camara dos deputados

@st.cache_data(ttl=3600)
def fetch_projetos(data_inicio, data_fim, palavras_chave):
    url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    params = {
        "dataInicio": data_inicio,
        "dataFim": data_fim,
        "ordenarPor": "id",
        "itens": 100,
        "pagina": 1,
        "siglaTipo": ["PL", "PLP", "MPV"],
        "keywords": palavras_chave
    }

    projetos = []
    while True:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            dados = response.json()["dados"]
            if len(dados) == 0:
                break
            projetos.extend(dados)
            params["pagina"] += 1
        else:
            print("Erro ao fazer requisição para a API:", response.status_code)
            break
    return projetos

@st.cache_data(ttl=3600)
def fetch_tramitacoes(id_proposicao, token):
    url_tramitacoes = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/tramitacoes"
    response_tramitacoes = requests.get(url_tramitacoes, headers={"Authorization": f"Bearer {token}"})
    if response_tramitacoes.status_code == 200:
        tramitacoes = response_tramitacoes.json()['dados']
        ultima_tramitacao = tramitacoes[-1] if tramitacoes else None
        return ultima_tramitacao['descricaoSituacao'] if ultima_tramitacao else "Sem tramitações"
    else:
        print(f"Erro ao obter as tramitações da proposição {id_proposicao}: {response_tramitacoes.status_code}")
        return "Erro na tramitação"

def create_dataframe(projetos, token):
    for proposicao in projetos:
        id_proposicao = proposicao['id']
        situacao_tramitacao = fetch_tramitacoes(id_proposicao, token)
        proposicao['situacaoTramitacao'] = situacao_tramitacao

    colunas = ['siglaTipo', 'numero', 'ano', 'ementa', 'situacaoTramitacao']
    df = pd.DataFrame(projetos, columns=colunas)
    df['situacaoTramitacao'] = df['situacaoTramitacao'].astype('str')
    df['situacaoTramitacao'] = df['situacaoTramitacao'].replace(to_replace='None', value='Não informado')
    
    df['ano'] = df['ano'].astype('int')
    df['numero'] = df['numero'].astype('int')

    df.columns = ["Tipo", "Número", "Ano", "Ementa", "Situação"]
    return df

token = "seu_token_de_acesso_aqui"
data_inicio = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
data_fim = datetime.datetime.now().strftime("%Y-%m-%d")
palavras_chave = [ 
"superendividamento",
"inadimplimento das obrigações", 
"mínimo existencial",   
"repactuação de dívidas",
"taxa de juros"
"crédito ao consumidor",
"parcelamento de dívidas",
"renegociação de dívidas"
"rotativo"
"cartão de crédito",
"crédito rural",
"crédito habitacional",
"empréstimo consignado"
"capital de giro",
"crédito para investimento",
"sistemas de informação de crédito",
"ativo problemático",
"crédito a vencer"
]

projetos = fetch_projetos(data_inicio, data_fim, palavras_chave)

df = create_dataframe(projetos, token)

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Inicializar os estados dos filtros apenas uma vez
    if 'filter_initialized' not in st.session_state:
        st.session_state.filter_tipo = df['Tipo'].unique().tolist()
        st.session_state.filter_ano = (int(df['Ano'].min()), int(df['Ano'].max()))
        st.session_state.filter_situacao = df['Situação'].unique().tolist()
        st.session_state.filter_initialized = True

    modify = st.checkbox("Filtrar o resultado")

    if not modify:
        return df

    with st.container():
        # Filtro para o Tipo
        selected_tipo = st.multiselect(
            "Tipo de proposição",
            df['Tipo'].unique(),
            default=st.session_state.filter_tipo
        )

        # Filtro para o Ano
        _min, _max = int(df['Ano'].min()), int(df['Ano'].max())
        selected_ano = st.slider(
            "Ano",
            min_value=_min,
            max_value=_max,
            value=st.session_state.filter_ano,
            step=1
        )

        # Filtro para a Situação
        selected_situacao = st.multiselect(
            "Situação",
            df['Situação'].unique(),
            default=st.session_state.filter_situacao
        )

    # Aplicar filtros
    if selected_tipo != st.session_state.filter_tipo:
        df = df[df['Tipo'].isin(selected_tipo)]
        st.session_state.filter_tipo = selected_tipo

    if selected_ano != st.session_state.filter_ano:
        df = df[df['Ano'].between(*selected_ano)]
        st.session_state.filter_ano = selected_ano

    if selected_situacao != st.session_state.filter_situacao:
        df = df[df['Situação'].isin(selected_situacao)]
        st.session_state.filter_situacao = selected_situacao

    return df

filtered_df = filter_dataframe(df)

def formatar_numero(valor):
    return f"{valor}"

dados_formatados = filtered_df.style.format({'Número': formatar_numero,
                                            'Ano': formatar_numero})

st.dataframe(dados_formatados, use_container_width=True, hide_index=True, height=500)

#Última atualização

url = "https://api.github.com/repos/brunagmoura/SiteMonitorEndividamento/commits"

@st.cache_data
def get_last_commit_date(url):
    response = requests.get(url)
    last_commit = response.json()[0]
    return last_commit['commit']['committer']['date']

last_update = get_last_commit_date(url)
if last_update != "Não foi possível obter as informações":
    last_update = dt.fromisoformat(last_update[:-1]) - timedelta(hours=3)
    last_update = last_update.strftime("%d/%m/%Y %H:%M:%S")

# Exibe no Streamlit
st.warning(f"Esse site é atualizado automaticamente de acordo com a disponibilização de informações no Painel de Operações de Crédito, do Banco Central do Brasil. A última atualização foi em {last_update}.", icon = "🤖")
