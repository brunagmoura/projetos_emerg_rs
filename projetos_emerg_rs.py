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
import pytz
timezone = pytz.timezone('America/Sao_Paulo')
import xml.etree.ElementTree as ET

now = dt.now(timezone)
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Monitor dos projetos de Lei apresentadas no Congresso Nacional", page_icon="📑",
                   layout="wide", initial_sidebar_state="collapsed")

st.subheader("Emergência climática no Rio Grande do Sul em pauta no Congresso Nacional")

st.markdown("""
<div style='text-align: left; color: #666666; font-size: 1em; background-color: #f0f0f0; padding: 10px; border-radius: 5px;margin-bottom: 20px;'>
    💡&nbsp;&nbsp;&nbsp;A busca utiliza a base de dados da Câmara dos Deputados e do Senado Federal e se refere aos projetos de lei e medidas provisórias que tenham como palavras-chave termos relacionados à catástrofe climática no Rio Grande do Sul. Os resultados são atualizados em tempo real.
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 1.3em;margin-bottom: 20px;'>Proposições legislativas da Câmara dos Deputados que se referem à catástrofe climática no Rio Grande do Sul</div>",
    unsafe_allow_html=True)

# API Câmara dos deputados

@st.cache_data(ttl=3600)
def fetch_projetos_deputados(data_inicio, palavras_chave):
    url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    params = {
        "dataApresentacaoInicio": data_inicio,
        "ordenarPor": "id",
        "itens": 100,
        "pagina": 1,
        "keywords": palavras_chave,
        "ano": 2024
    }

    projetos_deputados = []
    while True:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            dados = response.json()["dados"]
            if not dados:
                break
            projetos_deputados.extend(dados)
            params["pagina"] += 1
        else:
            print("Erro ao fazer requisição para a API:", response.status_code)
            break
    return projetos_deputados

@st.cache_data(ttl=3600)
def fetch_tramitacoes_deputados(id_proposicao):
    url_tramitacoes = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/tramitacoes"
    response_tramitacoes = requests.get(url_tramitacoes)
    if response_tramitacoes.status_code == 200:
        tramitacoes = response_tramitacoes.json()['dados']
        ultima_tramitacao = tramitacoes[-1] if tramitacoes else None
        return ultima_tramitacao['descricaoSituacao'] if ultima_tramitacao else "Sem tramitações"
    else:
        print(f"Erro ao obter as tramitações da proposição {id_proposicao}: {response_tramitacoes.status_code}")
        return "Erro na tramitação"

@st.cache_data(ttl=3600)
def fetch_detalhes_deputados(id_proposicao):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}"
    response = requests.get(url)
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
def fetch_autor_deputados(id_proposicao):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/autores"
    response = requests.get(url)
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

def create_dataframe_deputados(projetos_deputados):
    if not projetos_deputados:
        print("Nenhum projeto foi carregado da API.")
        return pd.DataFrame()  # Retorna um DataFrame vazio se não houver projetos

    for proposicao in projetos_deputados:
        id_proposicao = proposicao.get('id')
        if id_proposicao:
            detalhes = fetch_detalhes_deputados(id_proposicao)
            proposicao.update(detalhes)
            autor = fetch_autor_deputados(id_proposicao)
            proposicao.update(autor)

    colunas = ['siglaTipo', 'numero', 'ano', 'autor', 'ementa', 'dataHora',
               'descricaoTramitacao', 'descricaoSituacao']
    df_deputados = pd.DataFrame(projetos_deputados, columns=colunas)

    if df_deputados.empty:
        print("DataFrame está vazio após limpar NaNs.")
        return df_deputados

    df_deputados['dataHora'] = pd.to_datetime(df_deputados['dataHora'], errors='coerce')
    df_deputados = df_deputados.sort_values(by='dataHora', ascending=False)
    df_deputados['ano'] = df_deputados['ano'].astype(int)
    df_deputados['numero'] = df_deputados['numero'].astype(int)

    df_deputados.columns = ["Tipo", "Número", "Ano", "Autor", "Ementa", "Data e Hora",
                  "Tramitação", "Situação"]
    return df_deputados

data_inicio = dt(2024, 5, 5).strftime("%Y-%m-%d")
projetos_deputados = fetch_projetos_deputados(data_inicio, "Rio Grande do Sul")
df_deputados = create_dataframe_deputados(projetos_deputados)

def filter_dataframe_deputados(df_deputados):
    if 'filter_initialized' not in st.session_state:
        st.session_state.filter_tipo = df_deputados['Tipo'].unique().tolist()
        st.session_state.filter_situacao = df_deputados['Situação'].unique().tolist()
        st.session_state.filter_initialized = True

    modify = st.checkbox("Filtrar o resultado")

    if not modify:
        return df_deputados

    with st.container():
        # Filtro para o Tipo
        selected_tipo = st.multiselect(
            "Tipo de proposição",
            df_deputados['Tipo'].unique(),
            default=st.session_state.filter_tipo
        )

        # Filtro para a Situação
        selected_situacao = st.multiselect(
            "Situação",
            df_deputados['Situação'].unique(),
            default=st.session_state.filter_situacao
        )

    # Aplicar filtros
    if selected_tipo != st.session_state.filter_tipo:
        df_deputados = df_deputados[df_deputados['Tipo'].isin(selected_tipo)]
        st.session_state.filter_tipo = selected_tipo

    if selected_situacao != st.session_state.filter_situacao:
        df_deputados = df_deputados[df_deputados['Situação'].isin(selected_situacao)]
        st.session_state.filter_situacao = selected_situacao

    return df_deputados

filtered_df_deputados = filter_dataframe_deputados(df_deputados)

#Ano está formatado como número
def formatar_numero(valor):
    return f"{valor}"

dados_formatados_deputados = filtered_df_deputados.style.format({'Número': formatar_numero,
                                             'Ano': formatar_numero})

st.dataframe(dados_formatados_deputados, use_container_width=True, hide_index=True, height=500)

total_propostas = len(df_deputados)

st.markdown(
    f"<div style='text-align: left; color: #555555; font-size: 1em; margin-bottom: 20px;'>Até o momento foram apresentadas <strong>{total_propostas}</strong> propostas legislativas sobre a tragédia climática no Rio Grande do Sul na Câmara dos Deputados.</div>",
    unsafe_allow_html=True
)

st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 1.3em;margin-bottom: 20px;'>Proposições legislativas do Senado Federal que se referem à catástrofe climática no Rio Grande do Sul</div>",
    unsafe_allow_html=True)

# Senado Federal
@st.cache_data(ttl=3600)
def fetch_situacao_atual_senado(codigo):
    url = f"https://legis.senado.leg.br/dadosabertos/materia/situacaoatual/{codigo}"
    response = requests.get(url)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        situacao_atual = root.find('.//DescricaoSituacao')
        return situacao_atual.text if situacao_atual is not None else 'Sem situação'
    else:
        print(f"Erro ao obter situação atual para o código {codigo}: {response.status_code}")

def fetch_projetos_senado(ano, palavra_chave):
    url = "https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista"
    params = {
        "ano": ano,
        "palavraChave": palavra_chave,
        "dataInicioApresentacao": 20240505
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        todos_projetos = []
        for materia in root.findall('.//Materia'): #A consulta por json não está funcionando!!!!!!!!!!!!
            data = {
                'Tipo': materia.find('Sigla').text if materia.find('Sigla') is not None else '',
                'Número': materia.find('Numero').text if materia.find('Numero') is not None else '',
                'Ano': materia.find('Ano').text if materia.find('Ano') is not None else '',
                'Autor': materia.find('Autor').text if materia.find('Autor') is not None else '',
                'Ementa': materia.find('Ementa').text if materia.find('Ementa') is not None else '',
                'Data': materia.find('Data').text if materia.find('Data') is not None else '' #Não tem a hora
            }

            codigo_temp = materia.find('Codigo').text if materia.find('Codigo') is not None else ''
            data['Situação'] = fetch_situacao_atual_senado(codigo_temp)
            todos_projetos.append(data)
        df_senado = pd.DataFrame(todos_projetos)
        df_senado = df_senado.sort_values('Data', ascending=False)
        return df_senado
    else:
        print("Erro ao fazer requisição para a API:", response.status_code)

df_projetos_senado = fetch_projetos_senado(2024, "Rio Grande do Sul")

def filter_dataframe_senado(df_projetos_senado):
    if 'filter_initialized_senado' not in st.session_state:
        st.session_state.filter_tipo_senado = df_projetos_senado['Tipo'].unique().tolist()
        st.session_state.filter_situacao_senado = df_projetos_senado['Situação'].unique().tolist()
        st.session_state.filter_initialized_senado = True

    modify_senado = st.checkbox("Filtrar o resultado", key='modify_senado')

    if not modify_senado:
        return df_projetos_senado

    with st.container():
        # Filtro para o Tipo
        selected_tipo_senado = st.multiselect(
            "Tipo de proposição",
            df_projetos_senado['Tipo'].unique(),
            default=st.session_state.filter_tipo_senado
        )

        # Filtro para a Situação
        selected_situacao_senado = st.multiselect(
            "Situação",
            df_projetos_senado['Situação'].unique(),
            default=st.session_state.filter_situacao_senado
        )

    # Aplicar filtros
    if selected_tipo_senado != st.session_state.filter_tipo_senado:
        df_projetos_senado = df_projetos_senado[df_projetos_senado['Tipo'].isin(selected_tipo_senado)]
        st.session_state.filter_tipo_senado = selected_tipo_senado

    if selected_situacao_senado != st.session_state.filter_situacao_senado:
        df_projetos_senado = df_projetos_senado[df_projetos_senado['Situação'].isin(selected_situacao_senado)]
        st.session_state.filter_situacao_senado = selected_situacao_senado

    return df_projetos_senado

filtered_df_senado = filter_dataframe_senado(df_projetos_senado)

st.dataframe(filtered_df_senado, use_container_width=True, hide_index=True, height=500)

total_propostas_senado = len(df_projetos_senado)

st.markdown(
    f"<div style='text-align: left; color: #555555; font-size: 1em; margin-bottom: 20px;'>Até o momento foram apresentadas <strong>{total_propostas_senado}</strong> propostas legislativas sobre a tragédia climática no Rio Grande do Sul no Senado Federal.</div>",
    unsafe_allow_html=True
)
