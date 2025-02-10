from altair import themes
import altair as alt
import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import os
import csv
import time, datetime
import serial
import serial.tools.list_ports
import threading
from streamlit_autorefresh import st_autorefresh


# Configuração básica da página
st.set_page_config(page_title="Simulador de geração hidrelétrica.",page_icon=':droplet:', layout='wide', initial_sidebar_state='auto')

    # Nome do arquivo CSV
csv_file = 'dados.csv'  # nome do arquivo CSV onde os dados serão armazenados

# Verificar se o arquivo CSV já existe; se não, criar e adicionar cabeçalho
if not os.path.isfile(csv_file):  # verifica se o arquivo CSV não existe
    with open(csv_file, 'w', newline='') as file:  # abre o arquivo CSV em modo de escrita
        writer = csv.writer(file)  # cria um objeto writer para escrever no arquivo CSV
        writer.writerow(['Tempo', 'Fluxo', 'RPM', 'Corrente', 'Tensao'])  # escreve o cabeçalho no arquivo CSV


####### Iniciar estado de sessão para os componentes da interface #######
if 'evento' not in st.session_state:
    st.session_state.evento = threading.Event()

if 'thread_started' not in st.session_state:
    st.session_state.thread_started = False

if 'valor_anterior' not in st.session_state:
    st.session_state.valor_anterior = 0

if 'comunicação' not in st.session_state:
    st.session_state.comunicação = False

if 'porta' not in st.session_state: 
    st.session_state.porta = False # Começa Aberta

if 'ser' not in st.session_state:
    st.session_state.ser = None

if 'graficos' not in st.session_state:
    st.session_state.graficos = []

if 'vazao' not in st.session_state:
    st.session_state.vazao = 0

if 'carga' not in st.session_state:
    st.session_state.carga = 0

if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

if 'last_modified' not in st.session_state:
    st.session_state.last_modified = os.path.getmtime("dados.csv")

if 'fig_parado' not in st.session_state:
    st.session_state.fig_parado = None

if 'fig' not in st.session_state:
    st.session_state.fig = None

if 'param_bomba' not in st.session_state:
    st.session_state.param_bomba = 0

# if 'param_carga' not in st.session_state:
#     st.session_state.param_carga = 0

if 'lig_del' not in st.session_state:
    st.session_state.lig_del = False

if 'set_time' not in st.session_state:
    st.session_state.set_time = None

#Acelerar processamento de dados do arquivo, evitando demora frequente sempre que recarregar a página.

@st.cache_data(ttl=1)
def ler_dados(): #Lê os dados do CSV
    try:
        # tabela = pd.read_csv("simulador_web/tela_web/data.csv")
        tabela = pd.read_csv("dados.csv")
        if tabela.empty:
            st.warning("O arquivo CSV está vazio. Aguardando dados do Arduino.")
            # Dados de exemplo (opcional)
            dados_exemplo = pd.DataFrame({
                "Tempo": [0],
                "Fluxo": [0],
                "RPM": [0],
                "Corrente": [0],
                "Tensao": [0]
            })
            return dados_exemplo
        return tabela
    except FileNotFoundError:
        st.error(f"O arquivo {'dados.csv'} não foi encontrado.")
        return pd.DataFrame()  # Retorna um DataFrame vazio
    except pd.errors.EmptyDataError:
        st.warning("O arquivo CSV está vazio ou não possui colunas legíveis.")
        # Dados de exemplo (opcional)
        dados_exemplo = pd.DataFrame({
            "Tempo": [0],
            "Fluxo": [0],
            "RPM": [0],
            "Corrente": [0],
            "Tensao": [0]
        })
        return dados_exemplo
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo CSV: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio


def limpar_graficos():
    st.session_state.graficos = []
    st.session_state.fig_parado = []
    st.session_state.fig = []


def graf_plotly(dados,eixo_x,eixo_y1,eixo_y2,Tit_eixo1,Tit_eixo2): #Função gráficos
    # Crie a figura
    fig = go.Figure()

    # Adicione a primeira linha
    fig.add_trace(go.Scatter(
        x=dados[eixo_x],
        y=dados[eixo_y1],
        mode='lines',
        name=Tit_eixo1,
        line=dict(color='green')
    ))

    # Adicione a segunda linha
    fig.add_trace(go.Scatter(
        x=dados[eixo_x],
        y=dados[eixo_y2],
        mode='lines',
        name=Tit_eixo2,
        line=dict(color='blue'),
        yaxis='y2'
    ))

    # Atualize o layout para adicionar o segundo eixo y
    fig.update_layout(
        xaxis_title=eixo_x,
        yaxis=dict(
            title=Tit_eixo1,
            titlefont=dict(color='green'),
            tickfont=dict(color='green')
        ),
        yaxis2=dict(
            title=Tit_eixo2,
            titlefont=dict(color='blue'),
            tickfont=dict(color='blue'),
            overlaying='y',
            side='right'
        ),
        legend=dict(x=0.1, y=1.1),
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(tickformat="%m-%d-%H:%M:%S"),

        # Definindo cores de fundo
        plot_bgcolor='#f0f0f0',  # Fundo do gráfico
        paper_bgcolor='#f0f0f0'  # Fundo da área ao redor do gráfico
    )
    
    return fig


def iniciar_comunicação_serial():
    if st.session_state.get('ser') is None:
        ports = serial.tools.list_ports.comports()
        available_ports = [port.device for port in ports]
        print("Portas seriais disponíveis:", available_ports)

        if available_ports:  # Verifica se há portas disponíveis
            port1 = available_ports[0]

            # Verifica se a porta está disponível
            if port1 not in available_ports or st.session_state.porta:
                st.info("A porta já está aberta ou não está disponível.")
                return

            try:
                st.session_state.ser = serial.Serial(port1, baudrate=9600, timeout=1)
                st.session_state.porta = True  # Salva o estado da porta como fechado
                st.session_state.thread_started = True # Sinal para iniciar thread
                st.info(f"Conectado à porta {port1}")

            except serial.SerialException as e:
                st.error(f"Erro ao abrir a porta {port1}: {e}")
                
                try:
                    # Cria uma nova conexão serial na segunda tentativa
                    st.session_state.ser = serial.Serial(port1, baudrate=9600, timeout=1)
                    st.session_state.porta = True
                    st.session_state.thread_started = True
                    st.info(f"Conectado à porta {port1} na segunda tentativa")

                except serial.SerialException as e2:
                    st.error(f"Erro: A porta {port1} não foi encontrada ou está em uso: {e2}")
        else:
            st.error("Não há portas seriais disponíveis.")
    else:
        st.info("A porta já está aberta e funcional.")


def parar_comunicação_serial():
     # Verifica se a conexão serial foi estabelecida
    if st.session_state.get('ser') is not None:
        try:
            st.session_state.porta = False  # Atualiza o estado da porta como aberto
            st.session_state.thread_started = False # Sinal para parar thread

            # Verifica se a porta está aberta antes de tentar fechá-la
            if st.session_state.ser.is_open:
                try:
                    st.session_state.ser.close()  # Fecha a conexão
                    st.session_state.ser = None  # Limpa a referência
                    st.info("Comunicação serial encerrada e porta fechada.")
                except Exception as e:
                    st.error(f"Erro ao fechar porta serial: {e}")
            else:
                st.info("A porta já estava fechada.")

        except Exception as e:
            st.error(f"""Porta serial não foi estabelecida corretamente: 
                     {e}""")
    else:
        st.info("Não há porta serial aberta para fechar.")


def enviar_comando():
    try:
        st.session_state.ser.write(f"{str(st.session_state.param_bomba)}\n".encode())
        st.write("Comando enviado:", str(st.session_state.param_bomba))
        st.session_state.ser.reset_input_buffer()  # Limpa o buffer de entrada
    except Exception as e:
        st.error(f"Erro ao enviar comando: {e}")


def comunicar_serial(ser, csv_file, porta, estado_thread):
    # Esta verificação impede que o código de comunicação continue caso ser seja None. Se ser for None, significa que a porta serial não foi inicializada ou que foi fechada anteriormente (por exemplo, ao chamar parar_comunicação_serial()).
    if ser is None or not ser.is_open:
        return
    
    try:
        while ser.is_open and porta and estado_thread:
            try:
                if ser.in_waiting > 0:
                    data = ser.readline().decode('utf-8', errors='ignore').strip()
                    ser.reset_input_buffer()
                    if not "CORRENTE:" in data or "VAZÃO:" not in  data or "ROTAÇÃO:" not in data or "TENSÃO:" not in data:
                        print(f"Dado inválido recebido: {data}")  # Adiciona esta linha para depuração                    
                    
                    if "CORRENTE:" in data and "VAZÃO:" in data and "ROTAÇÃO:" in data and "TENSÃO:" in data:
                        print(f"Dados salvos: {data}")
                        parts = data.split(" | ")  # Divide a linha pelos delimitadores " | "
                        if len(parts) == 4:  # Verifica se temos exatamente 4 partes
                            corrente_str = parts[0].split(":")[1].strip()
                            tensao_str = parts[1].split(":")[1].strip()
                            rpm_str = parts[2].split(":")[1].strip()
                            fluxo_str = parts[3].split(":")[1].strip()

                            try:
                                fluxo = float(fluxo_str.replace("l/min", "").strip())
                                rpm = int(rpm_str.replace("RPM", "").strip())
                                corrente = float(corrente_str.replace("A", "").strip())
                                tensao = float(tensao_str.replace("V", "").strip())

                                current_time = datetime.datetime.now()

                                # Atualizar o arquivo CSV
                                with open(csv_file, 'a', newline='') as file:
                                    writer = csv.writer(file)
                                    writer.writerow([current_time, fluxo, rpm, corrente, tensao])

                                # ser.reset_input_buffer()
                            except ValueError as ve:
                                print(f"Erro ao converter dados: {ve}")
                                ser.reset_input_buffer()
                                continue  # Ignora a linha com dados inválidos        
                            
            except Exception as e:
                print(f"Erro com a conexão serial: {e}")
                ser = None
                estado_thread = False
                porta = False

            time.sleep(1)  # Pausa entre as leituras
    except Exception as e:
        print(f"Encerrando Thread: {e}")


# Chama a thread apenas se estado for ativo - True
if st.session_state.get('thread_started', True):
    try:
        threading.Thread(
            target=comunicar_serial,
            args=(st.session_state.ser, csv_file, st.session_state.porta, st.session_state.thread_started),
            daemon=True
        ).start()
    except Exception as e:
        st.error(f"Erro ao iniciar a comunicação serial: {e}")
        st.session_state.thread_started = False
else:
    pass
    # st.sidebar.info("Thread não iniciada ou foi desativada.")


global dados

####### Variáveis de armazenamento dos dados #######
# Listas para armazenar os dados
fluxos = []  # armazena taxas de fluxo
tempos = []  # armazena o tempo
rpms = []  # armazena RPM
correntes = []  # armazena corrente (Amperes)
tensoes = [] # armazena tensão

# Adicionar CSS customizado
custom_css = """
<style>
/* Botões */
div.stButton > button {
    font-size: 35px;
    padding: 10px 50px;
    margin-bottom: 5px;
    background-color: #f0f0f0;
}

/* Estilo para aumentar os valores no number_input */
div[data-testid="stNumberInput"] input {
    font-size: 30px;
    padding: 3px 15px;
    margin-bottom: 10px
    width: 80px !important; /* Ajusta a largura conforme necessário */
    background-color: #f0f0f0; /* Cor de fundo padrão (desativado) */
    border-radius: 10px;
    border: 2px solid #;
    color: black;
}

/* Sliders */
div.stSlider > div > div > div > div > div {
    margin-top: -20px; /* Ajuste esse valor conforme necessário */
    font-size: 30px;
}

</s
"""


####### Menu lateral #######
st.sidebar.image("aplicativo/static/simbol_ifsc.jpeg", width=60)
st.sidebar.markdown("""
                <div style="font-size: 30px; font-weight: bold; color: black; margin-bottom: 10px; margin-top: -5px; background-color: #;">
                    Menu
                </div>""",    
                unsafe_allow_html=True)

# Definição das página
# pagina = st.sidebar.radio('Interface Interativa:',['Monitoramento e Análise', 'Ambiente de Simulação'], key="ID1")
pagina = 'Monitoramento e Análise'

# Espaço reservado para os dados
dados_placeholder = st.sidebar.empty()

# # Atualiza os dados a cada 1 segundo
# count = st_autorefresh(interval=5000, limit=None, key="fizzbuzzcounter")


# Verifica se o arquivo CSV foi modificado e atualiza os dados
current_modified = os.path.getmtime("dados.csv")
if current_modified != st.session_state.last_modified:
    dados = ler_dados()
    st.session_state.last_modified = current_modified
else:
    dados = ler_dados()


####### Página da interface #######

# Atualização automática dos dados a cada 5 segundos
st_autorefresh(interval=5000, limit=None, key="data_refresh")


if pagina == 'Ambiente de Simulação':
    st.info("Página em revisão e desenvolvimento")
    # dados['Tempo'] = pd.to_datetime(dados['Tempo'], errors='coerce')
    # st.markdown(f"""
    #             <div style="font-size: 40px; font-weight: bold; color: black; margin-bottom: -20px; background-color: #;">                      Simulador do kit de gerador hidrelétrica
    #             </div>""", 
    #             unsafe_allow_html=True)
    # ('---')

    # col1, col2 = st.columns(spec=[0.7, 1])
    # # Coluna 2 - Parâmetros de simulação
    # with col2:
    #     vazaomax = 30
    #     cargamax = 40
    #     st.sidebar.markdown(f"""
    #             <div style="font-size: 26px; font-weight: bold; color: green; margin-bottom: -20px; background-color: #;">                      Parâmetros
    #             </div>""", 
    #             unsafe_allow_html=True)
                    
    #     # Adiciona o CSS customizado na sidebar
    #     st.sidebar.markdown(f"""
    #             <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: -55px; background-color: #;">                      Vazão (cm³/s):
    #             </div>""", 
    #             unsafe_allow_html=True)
    #     st.sidebar.markdown(custom_css, unsafe_allow_html=True)
    #     vazao = st.sidebar.slider('-', 0, vazaomax,key='slidervazao', label_visibility='hidden')
    
    #     st.sidebar.markdown(f"""
    #             <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: -55px; background-color: #;">                      Carga (W):
    #             </div>""",
    #             unsafe_allow_html=True)
    #     st.sidebar.markdown(custom_css, unsafe_allow_html=True)
    #     carga = st.sidebar.slider('-', 0, cargamax, key='slidercarga', label_visibility='hidden')

    #     # Gráficos individuais - selecionáveis
    #     st.markdown(f"""
    #             <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: -25px; background-color: #;">                      Selecione um gráfico dos dados históricos para ver
    #             </div>""",
    #             unsafe_allow_html=True)
    #     options = st.selectbox('Selecione',options=['Corrente', 'Tensao', 'Fluxo', 'RPM'],label_visibility='hidden', key="ID2")
    #     # Criação do gráfico de Fluxo com Altair
    #     chart = alt.Chart(dados).mark_line().encode(
    #         x='Tempo',
    #         y= options,
    #         color=alt.value('green'),  # Define a cor da linha como verde
    #         tooltip=['Tempo:T', 'Fluxo:Q', 'RPM:Q']  # Adiciona informações no tooltip
    #     ).properties(
    #         title=f'{options} x Tempo',
    #         width=600,  # Largura do gráfico
    #         height=300,  # Altura do gráfico
    #         background='#f0f0f0'  # Cor de fundo do gráfico
    #     ).configure_axis(
    #         labelColor='black',  # Cor dos números (valores dos eixos)
    #         titleColor='blue'    # Cor dos títulos dos eixos
    #     ).configure_title(
    #         fontSize=20,
    #         color='black',  # Cor do título do gráfico
    #         anchor='start',  # Alinhamento do título (esquerda)
    #         font='Verdana'
    #     )
    #     # Exibir o gráfico no Streamlit
    #     st.altair_chart(chart, use_container_width=True)


    #     st.sidebar.markdown('---')


    #     # Seleção parâmetros do gráfico comparativo (barra lateral)
    #     st.sidebar.markdown(f"""
    #             <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -10px; background-color: #;">                      Comparativo entre gráficos
    #             </div>""", 
    #             unsafe_allow_html=True)
    #     st.sidebar.markdown(f"""
    #             <div style="font-size: 23px; font-weight: normal; color: black; margin-bottom: -40px; background-color: #;">                      Eixo primário:
    #             </div>""", 
    #             unsafe_allow_html=True)      
    #     eixo1 = st.sidebar.selectbox(label='-',options=['Corrente', 'Tensao', 'RPM', 'Fluxo'],index=None,placeholder="Escolha uma opção", label_visibility='hidden', key=772)

    #     st.sidebar.markdown(f"""
    #             <div style="font-size: 23px; font-weight: normal; color: black; margin-bottom: -40px; background-color: #;">                      Eixo secundário:
    #             </div>""",
    #             unsafe_allow_html=True)
    #     eixo2 = st.sidebar.selectbox(label='-',options=['Corrente', 'Tensao', 'RPM', 'Fluxo'],index=None,placeholder="Escolha uma opção", label_visibility='hidden',key='ID3')

    #     espaço_grafico = st.empty()
    #     #Inserção gráfico comparativo
    #     st.markdown("""
    #             <div style="font-size: 24px; font-weight: bold; color: black; margin-bottom: 5px; background-color: #;">
    #                 Gráfico comparativo
    #             </div>""",    
    #             unsafe_allow_html=True)
    #     if eixo1 == None or eixo2 == None:
    #         st.markdown("""
    #             <div style="font-size: 22px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
    #                 Selecionar parâmetros no menu lateral
    #             </div>""",
    #             unsafe_allow_html=True)
    #     else:
    #         st.session_state.fig = graf_plotly(dados,eixo_x='Tempo', eixo_y1=eixo1, eixo_y2=eixo2,Tit_eixo1=eixo1,Tit_eixo2=eixo2)
    #         st.plotly_chart(st.session_state.fig, use_container_width=True)


    # #Coluna 1 - Animação do kit
    # with col1:
    # # Condições para exibição da velocidade e geração nos leds
    #     if  vazao == 0: # Desligado
    #         v_turbina = 0
    #         n_led = 0
    #     elif vazao <= (0.3 * vazaomax):  # Até 30% da vazão - máx 2 leds
    #         if carga == 0:
    #             v_turbina = 1
    #             n_led = 2
    #         elif carga > (0.40 * cargamax): # Carga acima de 40%
    #             v_turbina = 5 #parado
    #             n_led = 0            
    #         else:
    #             v_turbina = 1
    #             n_led = 1
    #     elif vazao <= (0.5 * vazaomax): # Até 50% da vazão - máx 4 leds
    #         if carga <= (0.3 * cargamax):
    #             v_turbina = 3
    #             n_led = 4
    #         elif carga <= (0.6 * cargamax):
    #             v_turbina = 2
    #             n_led = 3
    #         elif carga <= (0.9 * cargamax):
    #             v_turbina = 2
    #             n_led = 2
    #         else:
    #             v_turbina = 1
    #             n_led = 1
    #     elif vazao <= (0.8 * vazaomax): # Até 80% da vazão - máx 6 leds
    #         if carga <= (0.3 * cargamax):
    #             v_turbina = 4
    #             n_led = 6
    #         elif carga <= (0.5 * cargamax):
    #             v_turbina = 3
    #             n_led = 5
    #         elif carga <= (0.7 * cargamax):
    #             v_turbina = 3
    #             n_led = 4
    #         elif carga <= (0.85 * cargamax):
    #             v_turbina = 2
    #             n_led = 3
    #         elif carga <= (0.95 * cargamax):
    #             v_turbina = 2
    #             n_led = 2               
    #         else:
    #             v_turbina = 2
    #             n_led = 2
    #     elif vazao <= (1 * vazaomax): # Até 100% da vazão - máx 8 leds
    #         if carga <= (0.3 * cargamax):
    #             v_turbina = 4
    #             n_led = 8
    #         elif carga <= (0.50 * cargamax):
    #             v_turbina = 3
    #             n_led = 7
    #         elif carga <= (0.70 * cargamax):
    #             v_turbina = 2
    #             n_led = 6
    #         elif carga <= (0.85 * cargamax):
    #             v_turbina = 2
    #             n_led = 5
    #         elif carga <= (0.95 * cargamax):
    #             v_turbina = 2
    #             n_led = 4
    #         else:
    #             v_turbina = 2
    #             n_led = 3

    #     col1, col2 = st.columns(spec=[1, 0.2])
    #     with col1:
    #         velocidade_turbina = ["simulador_web/tela_web/Imagens e videos/vel_del.gif",
    #                             "simulador_web/tela_web/Imagens e videos/vel_1.gif",
    #                             "simulador_web/tela_web/Imagens e videos/vel_2.gif",
    #                             "simulador_web/tela_web/Imagens e videos/vel_3.gif",
    #                             "simulador_web/tela_web/Imagens e videos/vel_4.gif",
    #                             "simulador_web/tela_web/Imagens e videos/vel_parado.gif"
    #                             ]
    #         st.image(velocidade_turbina[v_turbina], use_column_width=True)

    #     with col2:
    #         niveis_leds = ["simulador_web/tela_web/Imagens e videos/level6.3.gif",
    #                         "simulador_web/tela_web/Imagens e videos/level1.gif",
    #                         "simulador_web/tela_web/Imagens e videos/level2.gif",
    #                         "simulador_web/tela_web/Imagens e videos/level3.gif", 
    #                         "simulador_web/tela_web/Imagens e videos/level4.gif",
    #                         "simulador_web/tela_web/Imagens e videos/level5.gif", 
    #                         "simulador_web/tela_web/Imagens e videos/level6.gif", 
    #                         "simulador_web/tela_web/Imagens e videos/level7.gif", 
    #                         "simulador_web/tela_web/Imagens e videos/level8.gif"
    #                         ]
    #         #st.image(niveis_leds[n_led])

elif pagina == 'Monitoramento e Análise':
# Certifique-se de que a coluna 'Timestamp' está no formato datetime
    dados['Tempo'] = pd.to_datetime(dados['Tempo'], errors='coerce')

    # Filtro de datas
    data_min = dados['Tempo'].min()
    data_max = dados['Tempo'].max()

    # Widget para selecionar o intervalo de datas
    st.session_state.set_time = st.sidebar.date_input(
        "Selecione o intervalo de tempo dos dados",
        [data_min, data_max],
        min_value=data_min.date(),
        max_value=data_max.date(),
    )

    # Filtrar os dados com base no intervalo de tempo
    if len(st.session_state.set_time) == 2:
        inicio, fim = st.session_state.set_time
        inicio = pd.to_datetime(inicio)  # Converter para datetime
        fim = pd.to_datetime(fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)  # Incluir o fim do dia
        dados_filtrados = dados[(dados['Tempo'] >= pd.to_datetime(inicio)) & (dados['Tempo'] <= pd.to_datetime(fim))]
    else:
        dados_filtrados = dados


# Apresentação dos dados e análises
    coln1, coln2, coln3 = st.columns(spec=[1,0.2,1.2])

    with coln1:     # Criação dos gráficos com biblioteca Altair

        # Criação do gráfico de Tensão
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='Tensao',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Tensão x Tempo',
            width=700,  # Largura do gráfico
            height=200,  # Altura do gráfico
            background='#f0f0f0'  # Cor de fundo do gráfico
        ).configure_axis(
            labelColor='black',  # Cor dos números (valores dos eixos)
            titleColor='blue'    # Cor dos títulos dos eixos
        ).configure_title(
            fontSize=20,
            color='black',  # Cor do título do gráfico
            anchor='start',  # Alinhamento do título (esquerda)
            font='Verdana'
        )
        # Exibir o gráfico no Streamlit
        st.altair_chart(chart, use_container_width=False)


        # Criação do gráfico de Corrente
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='Corrente',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Corrente x Tempo',
            width=700,  # Largura do gráfico
            height=200,  # Altura do gráfico
            background='#f0f0f0'  # Cor de fundo do gráfico
        ).configure_axis(
            labelColor='black',  # Cor dos números (valores dos eixos)
            titleColor='blue'    # Cor dos títulos dos eixos
        ).configure_title(
            fontSize=20,
            color='black',  # Cor do título do gráfico
            anchor='start',  # Alinhamento do título (esquerda)
            font='Verdana'
        )
        # Exibir o gráfico no Streamlit
        st.altair_chart(chart, use_container_width=False)

        # Criação do gráfico de Vazão
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='Fluxo',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'Fluxo:Q', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Vazão x Tempo',
            width=700,  # Largura do gráfico
            height=200,  # Altura do gráfico
            background='#f0f0f0'  # Cor de fundo do gráfico
        ).configure_axis(
            labelColor='black',  # Cor dos números (valores dos eixos)
            titleColor='blue'    # Cor dos títulos dos eixos
        ).configure_title(
            fontSize=20,
            color='black',  # Cor do título do gráfico
            anchor='start',  # Alinhamento do título (esquerda)
            font='Verdana'
        )
        # Exibir o gráfico no Streamlit
        st.altair_chart(chart, use_container_width=False)

        # Criação do gráfico de RPM
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='RPM',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Velocidade x Tempo',
            width=700,  # Largura do gráfico
            height=200,  # Altura do gráfico
            background='#f0f0f0'  # Cor de fundo do gráfico
        ).configure_axis(
            labelColor='black',  # Cor dos números (valores dos eixos)
            titleColor='blue'    # Cor dos títulos dos eixos
        ).configure_title(
            fontSize=20,
            color='black',  # Cor do título do gráfico
            anchor='start',  # Alinhamento do título (esquerda)
            font='Verdana'
        )
        # Exibir o gráfico no Streamlit
        st.altair_chart(chart, use_container_width=False)
      
    with coln2: # Espaço entre colunas
        pass # Espaço entre colunas 1 e 3

    with coln3: # Estrutura personalizada de exibição
        coln31, coln32, coln33, coln34 = st.columns(4)
        with coln31:
            # Criar uma estrutura personalizada
            st.markdown(
                f"""
                <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
                    Tensão [V]
                </div>
                <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                    {(dados['Tensao'].iloc[-1]):.2f}
                </div>
                """, 
                unsafe_allow_html=True
            )   
        with coln32:
            #pass
            st.markdown(
                f"""
                <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
                    Corrente [A]
                </div>
                <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                    {(dados['Corrente'].iloc[-1]):.2f}
                </div>
                """, 
                unsafe_allow_html=True
            )
        with coln33:
            st.markdown(
                f"""
                <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
                    Vazão [L/min]
                </div>
                <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                    {dados['Fluxo'].iloc[-1]}
                </div>
                """, 
                unsafe_allow_html=True
            )
        with coln34:
            # Criar uma estrutura personalizada
            st.markdown(
                f"""
                <div style="font-size: 23px; font-weight: normal; color: black; margin-bottom: 6px; background-color: #f0f0f0;">
                    Velocidade [rpm]
                </div>
                <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                    {dados['RPM'].iloc[-1]}
                </div>
                """, 
                unsafe_allow_html=True
            ) 
        ('---')
        coln35, coln36 = st.columns(2)
        with coln35:
            st.markdown(
                f"""
                <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
                    Potência [VA]
                </div>
                <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                    {(dados['Corrente'].iloc[-1] * dados['Tensao'].iloc[-1]):.2f}
                </div>
                """,    
                unsafe_allow_html=True
            )
        with coln36:
            st.markdown(
                f"""
                <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
                    Rendimento [%]
                </div>
                <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                    {((dados['Corrente'].iloc[-1] * dados['Tensao'].iloc[-1]) / (220*0.5)):.2f}
                </div>
                """,    
                unsafe_allow_html=True
            )
        ('---')
        #Menu lateral gráfico comparativo
        st.sidebar.markdown(f"""
                <div style="font-size: 22px; font-weight: bold; color: green; margin-bottom: -10px; background-color: #;">                      Comparativo entre gráficos
                </div>""", 
                unsafe_allow_html=True)
        st.sidebar.markdown(f"""
                <div style="font-size: 23px; font-weight: normal; color: black; margin-bottom: -50px; background-color: #;">                      Eixo primário:
                </div>""", 
                unsafe_allow_html=True)      
        eixo1 = st.sidebar.selectbox(label='-',options=['Corrente', 'Tensao', 'RPM', 'Fluxo'],index=None,placeholder="Escolha uma opção", label_visibility='hidden', key="ID4")

        st.sidebar.markdown(f"""
                <div style="font-size: 23px; font-weight: normal; color: black; margin-bottom: -50px; background-color: #;">                      Eixo secundário:
                </div>""",
                unsafe_allow_html=True)
        eixo2 = st.sidebar.selectbox(label='-',options=['Corrente', 'Tensao', 'RPM', 'Fluxo'],index=None,placeholder="Escolha uma opção", label_visibility='hidden',key='ID5')

        #Inserção gráfico comparativo
        st.markdown("""
                <div style="font-size: 24px; font-weight: bold; color: black; margin-bottom: -5px; background-color: #;">
                    Gráfico comparativo
                </div>""",    
                unsafe_allow_html=True)
        if eixo1 == None or eixo2 == None:
            st.markdown("""
                <div style="font-size: 22px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
                    Selecionar parâmetros no Menu lateral
                </div>""",
                unsafe_allow_html=True)
        else:
            st.session_state.fig = graf_plotly(dados_filtrados,eixo_x='Tempo', eixo_y1=eixo1, eixo_y2=eixo2,Tit_eixo1=eixo1,Tit_eixo2=eixo2)
            st.plotly_chart(st.session_state.fig, use_container_width=True)


        # Menu lateral de comandos para o arduino
        st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        st.sidebar.markdown("""
                <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -50px; margin-top: 5px; background-color: #;">
                    Nível bomba:
                </div>""",    
                unsafe_allow_html=True)
        st.session_state.param_bomba = st.sidebar.number_input('-',min_value=0, max_value=255, label_visibility='hidden', key='ID6')

        # st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        # st.sidebar.markdown("""
        #         <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -65px; margin-top: 0px; background-color: #;">
        #             Nível carga (Ohm):
        #         </div>""",    
        #         unsafe_allow_html=True)
        # st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        # st.session_state.param_carga = st.sidebar.number_input('-',min_value=0, max_value=25, label_visibility='hidden', key='ID7')

       
        # Comando comunicação (ativar-desativar)

        st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        st.sidebar.markdown("""
                <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -5px; margin-top: -10px; background-color: #;">
                    Enviar parâmetros
                </div>""",    
                unsafe_allow_html=True)
        
        st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        st.sidebar.button('Enviar',key='ID8',on_click=enviar_comando)


        st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        st.sidebar.markdown("""
                <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -20px; margin-top: -20px; background-color: #;">
                    Ativar
                </div>""",    
                unsafe_allow_html=True)
        
        st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        st.sidebar.button('Ativar',key='ID9',on_click=iniciar_comunicação_serial)

        st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        st.sidebar.markdown("""
                <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -20px; margin-top: -20px; background-color: #;">
                    Desativar
                </div>""",    
                unsafe_allow_html=True)
        st.sidebar.markdown(custom_css,unsafe_allow_html=True)
        st.sidebar.button('Desativar',key='ID10',on_click=parar_comunicação_serial)


            
       

################## FIM DO CÓDIGO#################
# COPIE E COLE O CÓDIGO PARA INICIAR A INTERFACE
# streamlit run simulador_web/tela_web/base.py
