import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
import warnings
#import datetime
import calendar
import json
import requests
from dash import Dash, dcc, html, Input, Output
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime as dt, timedelta

warnings.filterwarnings('ignore')

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Monitor projetos de Lei apresentadas no Congresso Nacional", page_icon="📑",
                   layout="wide", initial_sidebar_state="collapsed")

st.subheader("Emergência no Rio Grande do Sul em pauta no Congresso Nacional")

st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 1.3em;margin-bottom: 20px;'>Proposições legislativas que se referem à catástrofe climática no Rio Grande do Sul</div>",
    unsafe_allow_html=True)

st.markdown("""
<div style='text-align: left; color: #666666; font-size: 1em; background-color: #f0f0f0; padding: 10px; border-radius: 5px;margin-bottom: 20px;'>
    💡&nbsp;&nbsp;&nbsp;A busca utiliza a base de dados da Câmara dos Deputados e se refere aos projetos de lei e medidas provisórias que tenham como palavras-chave termos relacionados à catástrofe climática no Rio Grande do Sul. Os resultados são atualizados em tempo real.
</div>
""", unsafe_allow_html=True)


# API Camara dos deputados

@st.cache_data(ttl=3600)
def fetch_projetos(data_inicio, data_fim, palavras_chave):
    url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    params = {
        "dataApresentacaoInicio": data_inicio,
        "dataApresentacaoFim": data_fim,
        "ordenarPor": "id",
        "itens": 100,
        "pagina": 1,
        "keywords": palavras_chave,
        "ano": 2024
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

@st.cache_data(ttl=3600)
def fetch_detalhes(id_proposicao, token):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        dados = response.json()['dados']
        status_proposicao = dados.get('statusProposicao', {})
        return {
            'dataHora': status_proposicao.get('dataHora', 'Sem data'),
            'descricaoTramitacao': status_proposicao.get('descricaoTramitacao', 'Sem tramitação'),
            'descricaoSituacao': status_proposicao.get('descricaoSituacao', 'Sem situação')
        }
    else:
        print(f"Erro ao obter os detalhes da proposição {id_proposicao}: {response.status_code}")
        return {}

@st.cache_data(ttl=3600)
def fetch_autor(id_proposicao, token):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/autores"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        dados = response.json()['dados']
        if dados:
            nome_autor = dados[0].get('nome', 'Sem nome do autor')
            return {'autor': nome_autor}
        else:
            return {'autor': 'Sem autores'}
    else:
        print(f"Erro ao obter os autores da proposição {id_proposicao}: {response.status_code}")
        return {'autor': 'Erro ao obter dados'}

def create_dataframe(projetos, token):
    if not projetos:
        print("Nenhum projeto foi carregado da API.")
        return pd.DataFrame()  # Retorna um DataFrame vazio se não houver projetos

    for proposicao in projetos:
        id_proposicao = proposicao.get('id')
        if id_proposicao:
            detalhes = fetch_detalhes(id_proposicao, token)
            proposicao.update(detalhes)
            autor = fetch_autor(id_proposicao, token)
            proposicao.update(autor)

    colunas = ['siglaTipo', 'numero', 'ano', 'autor', 'ementa', 'dataHora',
               'descricaoTramitacao', 'descricaoSituacao']
    df = pd.DataFrame(projetos, columns=colunas)


    if df.empty:
        print("DataFrame está vazio após limpar NaNs.")
        return df

    df['dataHora'] = pd.to_datetime(df['dataHora'], errors='coerce')
    df = df.sort_values(by='dataHora', ascending=False)

    df['ano'] = df['ano'].astype(int)  # Converte ano para int
    df['numero'] = df['numero'].astype(int)  # Converte número para int

    df.columns = ["Tipo", "Número", "Ano", "Autor", "Ementa", "Data e Hora",
                  "Tramitação", "Situação"]
    return df


token = "seu_token_de_acesso_aqui"
data_inicio = dt(2024, 5, 5).strftime("%Y-%m-%d")
data_fim = dt.now().strftime("%Y-%m-%d")
palavras_chave = [
    "Rio Grande do Sul"
]

projetos = fetch_projetos(data_inicio, data_fim, palavras_chave)

df = create_dataframe(projetos, token)


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Inicializar os estados dos filtros apenas uma vez
    if 'filter_initialized' not in st.session_state:
        st.session_state.filter_tipo = df['Tipo'].unique().tolist()
        st.session_state.filter_situacao = df['Situação'].unique().tolist()
        #st.session_state.filter_autor = df['Autor'].unique().tolist()
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

        # Filtro para a Situação
        selected_situacao = st.multiselect(
            "Situação",
            df['Situação'].unique(),
            default=st.session_state.filter_situacao
        )

        # Filtro para o Autor
        #selected_autor = st.multiselect(
        #    "Autor",
        #    df['Autor'].unique(),
        #    default=st.session_state.filter_situacao
        #)

    # Aplicar filtros
    if selected_tipo != st.session_state.filter_tipo:
        df = df[df['Tipo'].isin(selected_tipo)]
        st.session_state.filter_tipo = selected_tipo

    if selected_situacao != st.session_state.filter_situacao:
        df = df[df['Situação'].isin(selected_situacao)]
        st.session_state.filter_situacao = selected_situacao

    #if selected_autor != st.session_state.filter_autor:
    #    df = df[df['Autor'].isin(selected_autor)]
    #    st.session_state.filter_autor = selected_autor

    return df

filtered_df = filter_dataframe(df)

def formatar_numero(valor):
    return f"{valor}"

dados_formatados = filtered_df.style.format({'Número': formatar_numero,
                                             'Ano': formatar_numero})

st.dataframe(dados_formatados, use_container_width=True, hide_index=True, height=500)

total_propostas = len(df)

st.write(f"Até o momento foram apresentadas {total_propostas} propostas legislativas sobre a tragédia climática no Rio Grande do Sul.")
# Última atualização

# Exibe no Streamlit
st.warning(
    f"Esse site é atualizado automaticamente de acordo com a consulta à Câmara dos Deputados. A última atualização foi em {dt.now().strftime('%d/%m/%Y %H:%M:%S')}.",
    icon="🤖")

