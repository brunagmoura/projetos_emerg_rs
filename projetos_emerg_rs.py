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
now = dt.now(timezone)
import xml.etree.ElementTree as ET

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
data_fim = now.strftime("%Y-%m-%d")
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

st.write(f"Até o momento foram apresentadas {total_propostas} propostas legislativas sobre a tragédia climática no Rio Grande do Sul na Câmara dos Deputados.")

st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 1.3em;margin-bottom: 20px;'>Proposições legislativas do Senado Federal que se referem à catástrofe climática no Rio Grande do Sul</div>",
    unsafe_allow_html=True)

# Senado Federal

@st.cache_data(ttl=3600)
def fetch_situacao_atual(codigo):
    url = f"https://legis.senado.leg.br/dadosabertos/materia/situacaoatual/{codigo}"
    response = requests.get(url)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        situacao_atual = root.find('.//DescricaoSituacao')
        return situacao_atual.text if situacao_atual is not None else 'Desconhecida'
    else:
        print(f"Erro ao obter situação atual para o código {codigo}: {response.status_code}")
        return 'Erro ao consultar'

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
        all_data = []
        for materia in root.findall('.//Materia'):
            data = {
                'Sigla': materia.find('Sigla').text if materia.find('Sigla') is not None else '',
                'Numero': materia.find('Numero').text if materia.find('Numero') is not None else '',
                'Ano': materia.find('Ano').text if materia.find('Ano') is not None else '',
                'Autor': materia.find('Autor').text if materia.find('Autor') is not None else '',
                'Ementa': materia.find('Ementa').text if materia.find('Ementa') is not None else '',
                'Data': materia.find('Data').text if materia.find('Data') is not None else ''
            }

            codigo_temp = materia.find('Codigo').text if materia.find('Codigo') is not None else ''
            data['SituacaoAtual'] = fetch_situacao_atual(codigo_temp)
            all_data.append(data)
        df = pd.DataFrame(all_data)
        # Ordena o DataFrame pela coluna 'Data'
        df_sorted = df.sort_values('Data', ascending=False)  # Altere para False se desejar ordem decrescente
        return df_sorted
    else:
        print("Erro ao fazer requisição para a API:", response.status_code)
        return None

df_projetos = fetch_projetos_senado(2024, "Rio Grande do Sul")

st.dataframe(df_projetos, use_container_width=True, hide_index=True, height=500)

total_propostas_senado = len(df_projetos)

st.write(f"Até o momento foram apresentadas {total_propostas_senado} propostas legislativas sobre a tragédia climática no Rio Grande do Sul no Senado Federal.")

st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 1.3em;margin-bottom: 20px;'>Distribuição das emendas individuais entre os municípios do RS</div>",
    unsafe_allow_html=True)
st.markdown("""
<div style='text-align: left; color: #666666; font-size: 1em; background-color: #f0f0f0; padding: 10px; border-radius: 5px;margin-bottom: 20px;'>
    💡&nbsp;&nbsp;&nbsp;Os dados foram coletados utilizando os seguintes filtros no Tesouro Gerencial:
    <ul>
        <li>Item informação = Despesas empenhadas (controle empenho)</li>
        <li>Resultado EOF = 6: Despesa discricionaria e decorrente de emenda individual</li>
        <li>Emissão - Ano = 2024</li>
        <li>Modalidade aplicação = 40: Transferencias a municipios, 41: Transferencias a municipios - Fundo a fundo, 42: Execução orçamentaria delegada a municipios, 45: Transferencias a municipios art.24 LC 141/12, 46: Transferencias a municipios art.25 LC 141/12</li>
        <li>Esfera orçamentária = 1: Orcamento fiscal, 2: Orcamento de seguridade social</li>
    </ul>
</div>
""", unsafe_allow_html=True)

@st.cache_data()
def load_data(arquivo, coluna_data):
    data = pd.read_csv(arquivo, encoding="UTF-8", delimiter=',', decimal='.')
    print("Colunas disponíveis:", data.columns)
    data[coluna_data] = pd.to_datetime(data[coluna_data], format='%d/%m/%Y', errors='coerce')
    data = data.sort_values(by=coluna_data)
    data[coluna_data] = data[coluna_data].dt.strftime("%d-%m-%Y")
    return data

@st.cache_data()
def load_geojson_data():
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-43-mun.json"
    response = requests.get(url)
    return response.json()

Emendas_RS_cod = load_data(arquivo="/Users/brunamoura/projetos_rs_emerg/projeto_rs_emerg/Emendas_RS_cod.csv",
                           coluna_data="data_emissao")
geojson_data = load_geojson_data()

plot_emendas_individuais_movimentacao_liquida = px.choropleth_mapbox(Emendas_RS_cod,
                               geojson=geojson_data,
                               locations='code_muni',
                               color='moviment_liquida',
                               color_continuous_scale="YlOrRd",
                               animation_frame='data_emissao',
                               mapbox_style="carto-positron",
                               zoom=5,
                               center={"lat": -29.68, "lon": -53.80},
                               opacity=1,
                               labels={'Valor':'moviment_liquida'},
                               hover_data=["code_muni", "municipio"],
                               featureidkey="properties.id")

plot_emendas_individuais_movimentacao_liquida.update_layout(
    coloraxis_colorbar=dict(
        len=1,
        y=-0.25,
        yanchor='bottom',
        xanchor='center',
        x=0.5,
        orientation='h',
        title="Saldo acumulado das emendas individuais (2024)",
        titleside="bottom"
    ),
    margin=dict(t=0, b=0, l=0, r=0))

plot_emendas_individuais_movimentacao_saldo = px.choropleth_mapbox(Emendas_RS_cod,
                               geojson=geojson_data,
                               locations='code_muni',
                               color='saldo',
                               color_continuous_scale="YlOrRd",
                               animation_frame='data_emissao',
                               mapbox_style="carto-positron",
                               zoom=5,
                               center={"lat": -29.68, "lon": -53.80},
                               opacity=1,
                               labels={'Valor':'saldo'},
                               hover_data=["code_muni", "municipio"],
                               featureidkey="properties.id")

plot_emendas_individuais_movimentacao_saldo.update_layout(
    coloraxis_colorbar=dict(
        len=1,
        y=-0.25,
        yanchor='bottom',
        xanchor='center',
        x=0.5,
        orientation='h',
        title="Saldo acumulado das emendas individuais (2024)",
        titleside="bottom"
    ),
    margin=dict(t=0, b=0, l=0, r=0))

cols = st.columns([1, 1])  # Colunas na página
with cols[0]:
    st.markdown(
        "<div style='text-align: center; color: #888888; font-size: 0.9em;margin-bottom: 20px;margin-top: 20px;'>Emendas parlamentares individuais - movimentação líquida (R$) diária</div>",
        unsafe_allow_html=True)

    st.plotly_chart(plot_emendas_individuais_movimentacao_liquida, use_container_width=True)

with cols[1]:
    st.markdown(
        "<div style='text-align: center; color: #888888; font-size: 0.9em;margin-bottom: 20px;margin-top: 20px;'>Emendas parlamentares individuais - saldo (R$) acumulado</div>",
        unsafe_allow_html=True)
    st.plotly_chart(plot_emendas_individuais_movimentacao_saldo, use_container_width=True)

# Última atualização

# Exibe no Streamlit
st.warning(
    f"A consulta às proposições legislativas é atualizada automaticamente de acordo com a API da Câmara dos Deputados. A última atualização foi em {now.strftime('%d/%m/%Y %H:%M:%S')}. "
    f"A consulta aos valores das emendas individuais é atualizado diariamente. A última consulta foi em 08/05/2024",
    icon="🤖")
