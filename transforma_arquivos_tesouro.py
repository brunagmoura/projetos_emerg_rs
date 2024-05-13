import pandas as pd

codigos_municipios = pd.read_csv('mun_codigos.csv', delimiter=';', header=0)

codigos_municipios['name_muni'] = codigos_municipios['name_muni'].replace({
    'NAOMETOQUE': 'NAO-ME-TOQUE',
    'SAO JOSE DO INHACARA': 'SAO JOSE DO INHACORA'
})

Emendas_RS = pd.read_excel('/Users/brunamoura/Downloads/Emendas_RS.xlsx', skiprows=2,names=[
    'cod_siafi_municipio', 'municipio', 'uf', 'estado', 'data_emissao', 'moviment_liquida', 'moviment_liquida_acum', 'saldo'
])

Emendas_RS_cod = pd.merge(Emendas_RS, codigos_municipios, left_on='municipio', right_on='name_muni', how='left')

Emendas_RS_cod.to_csv('Emendas_RS_cod.csv', index=False)