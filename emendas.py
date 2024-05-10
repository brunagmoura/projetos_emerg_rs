import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
import warnings
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
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Monitor das emendas individuais repassadas ao RS", page_icon="📑",
                   layout="wide", initial_sidebar_state="collapsed")

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

Emendas_RS_cod = load_data(arquivo="Emendas_RS_cod.csv",
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
    f"A consulta aos valores das emendas individuais é atualizado diariamente. A última consulta foi em 10/05/2024",
    icon="🤖")
