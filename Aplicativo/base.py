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
import numpy as np
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


def desenhar_leds(n_led, intensidade_base=0.8):
            fig = go.Figure()
            
            total_leds = 8  # Quantidade máxima de LEDs
            
            for i in range(total_leds):
                # Criando um efeito pulsante no brilho
                intensidade_pulso = intensidade_base + 0.2 * np.sin(time.time() * 2)  
                intensidade = min(1, (i + 1) / total_leds * intensidade_pulso)  
                
                if i < n_led:
                    cor = f"rgba(255, 215, 0, {intensidade})"  # Amarelo Dourado com brilho variável
                    borda = "rgba(255, 255, 100, 1)"  # Contorno brilhante
                else:
                    cor = "rgba(50, 50, 50, 0.2)"  # LED apagado
                    borda = "rgba(100, 100, 100, 0.5)"  # Contorno mais discreto

                fig.add_trace(go.Scatter(
                    x=[i], y=[1],
                    mode="markers",
                    marker=dict(
                        size=60,
                        color=cor,
                        line=dict(color=borda, width=3),
                        opacity=1
                    ),
                    showlegend=False
                ))

            # Configuração do layout
            fig.update_layout(
                xaxis=dict(visible=False, range=[-1, total_leds]),
                yaxis=dict(visible=False, range=[0, 2]),
                width=500, height=200,
                paper_bgcolor="black",  # Fundo preto
                plot_bgcolor="black",
                margin=dict(l=0, r=0, t=0, b=0)
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


# Verifica se o arquivo CSV foi modificado e atualiza os dados
current_modified = os.path.getmtime("dados.csv")
if current_modified != st.session_state.last_modified:
    dados = ler_dados()
    st.session_state.last_modified = current_modified
else:
    dados = ler_dados()

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


#------------------ Interface ----------------------

# Atualização automática dos dados a cada 5 segundos
st_autorefresh(interval=5000, limit=None, key="data_refresh")


#----------- Menu lateral ---------------

st.sidebar.image("aplicativo/static/simbol_ifsc.jpeg", width=60)
st.sidebar.markdown("""
                <div style="font-size: 30px; font-weight: bold; color: black; margin-bottom: 10px; margin-top: -5px; background-color: #;">
                    Menu
                </div>""",    
                unsafe_allow_html=True)

# Link direcionado ao repositório da bancada didática no GitHub
st.sidebar.markdown("[🔗 Baixe o repositório no GitHub](https://github.com/GuilhermeCanfild30/Interface_streamlit/tree/main)")


#----------------- Abas principais da Interface -----------------

tab1, tab2, tab3, tab4 = st.tabs(["📊 Monitoramento", "📈 Comparativo", "📖 Tutorial", "🎴 Animação"])

with tab1:
    
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
    coln1 = st.columns(1)

    # Estrutura personalizada de exibição
    coln11, coln12, coln13, coln14, coln15 = st.columns(5)
    with coln11:
        # Criar uma estrutura personalizada
        st.markdown(
            f"""
            <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 10px; background-color: #f0f0f0;">
                Tensão [V]
            </div>
            <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                {(dados['Tensao'].iloc[-1]):.2f}
            </div>
            """, 
            unsafe_allow_html=True
        ) 
        st.markdown("<br>", unsafe_allow_html=True)  
    with coln12:
        #pass
        st.markdown(
            f"""
            <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 10px; background-color: #f0f0f0;">
                Corrente [A]
            </div>
            <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                {(dados['Corrente'].iloc[-1]):.2f}
            </div>
            """, 
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
    with coln13:
        st.markdown(
            f"""
            <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 10px; background-color: #f0f0f0;">
                Vazão [L/min]
            </div>
            <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                {dados['Fluxo'].iloc[-1]}
            </div>
            """, 
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
    with coln14:
        # Criar uma estrutura personalizada
        st.markdown(
            f"""
            <div style="font-size: 23px; font-weight: normal; color: black; margin-bottom: 10px; background-color: #f0f0f0;">
                Velocidade [rpm]
            </div>
            <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                {dados['RPM'].iloc[-1]}
            </div>
            """, 
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
    with coln15:
        st.markdown(
            f"""
            <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 10px; background-color: #f0f0f0;">
                Potência [VA]
            </div>
            <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                {(dados['Corrente'].iloc[-1] * dados['Tensao'].iloc[-1]):.2f}
            </div>
            """,    
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
    # with coln36:
    #     st.markdown(
    #         f"""
    #         <div style="font-size: 24px; font-weight: normal; color: black; margin-bottom: 5px; background-color: #f0f0f0;">
    #             Rendimento [%]
    #         </div>
    #         <div style="font-size: 45px; font-weight: bold; color: green; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
    #             {((dados['Corrente'].iloc[-1] * dados['Tensao'].iloc[-1]) / (220*0.5)):.2f}
    #         </div>
    #         """,    
    #         unsafe_allow_html=True
    #     )
    ('---')

    col1, col2 = st.columns(2)
    with col1:     # Criação dos gráficos com biblioteca Altair
        # Criação do gráfico de Tensão
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='Tensao',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Tensão x Tempo',
            width=700,  # Largura do gráfico
            height=300,  # Altura do gráfico
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

    with col2:
        # Criação do gráfico de Corrente
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='Corrente',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Corrente x Tempo',
            width=700,  # Largura do gráfico
            height=300,  # Altura do gráfico
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

    col3, col4 = st.columns(2)
    with col3:
        # Criação do gráfico de Vazão
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='Fluxo',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'Fluxo:Q', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Vazão x Tempo',
            width=700,  # Largura do gráfico
            height=300,  # Altura do gráfico
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

    with col4:
        # Criação do gráfico de RPM
        chart = alt.Chart(dados_filtrados).mark_line().encode(
            x='Tempo',
            y='RPM',
            color=alt.value('green'),  # Define a cor da linha como verde
            tooltip=['Tempo:T', 'RPM:Q']  # Adiciona informações no tooltip
        ).properties(
            title='Velocidade x Tempo',
            width=700,  # Largura do gráfico
            height=300,  # Altura do gráfico
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

with tab2:
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

with tab3:
    st.write("## Tutorial...")

with tab4:
    # st.info("Página em revisão e desenvolvimento")
    dados['Tempo'] = pd.to_datetime(dados['Tempo'], errors='coerce')

    # Controle da animação
    colc1, colc2 = st.columns([3,3])
    with colc1:
        st.markdown(custom_css,unsafe_allow_html=True)
        st.markdown("""
                <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -15px; margin-top: 0px; background-color: #;">
                    Nível bomba:
                </div>""",    
                unsafe_allow_html=True)
        bombamax = 255
        bomba = st.slider('-',min_value=0, max_value=bombamax, label_visibility='hidden')
        
        st.markdown(custom_css,unsafe_allow_html=True)
        st.markdown("""
                <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -15px; margin-top: 0px; background-color: #;">
                    Nível carga (Ohm):
                </div>""",    
                unsafe_allow_html=True)
        cargamax = 100
        carga = st.slider('-',min_value=0, max_value=cargamax, label_visibility='hidden', key='ID7')

        ('---')

    # Condições para exibição da velocidade e geração nos leds
        if  bomba == 0: # Desligado
            v_turbina = 0
            n_led = 0
        elif bomba <= (0.3 * bombamax):  # Até 30% da vazão - máx 2 leds
            if carga == 0:
                v_turbina = 1
                n_led = 2
            elif carga > (0.40 * cargamax): # Carga acima de 40%
                v_turbina = 5 #parado
                n_led = 0            
            else:
                v_turbina = 1
                n_led = 1
        elif bomba <= (0.5 * bombamax): # Até 50% da vazão - máx 4 leds
            if carga <= (0.3 * cargamax):
                v_turbina = 3
                n_led = 4
            elif carga <= (0.6 * cargamax):
                v_turbina = 2
                n_led = 3
            elif carga <= (0.9 * cargamax):
                v_turbina = 2
                n_led = 2
            else:
                v_turbina = 1
                n_led = 1
        elif bomba <= (0.8 * bombamax): # Até 80% da vazão - máx 6 leds
            if carga <= (0.3 * cargamax):
                v_turbina = 4
                n_led = 6
            elif carga <= (0.5 * cargamax):
                v_turbina = 3
                n_led = 5
            elif carga <= (0.7 * cargamax):
                v_turbina = 3
                n_led = 4
            elif carga <= (0.85 * cargamax):
                v_turbina = 2
                n_led = 3
            elif carga <= (0.95 * cargamax):
                v_turbina = 2
                n_led = 2               
            else:
                v_turbina = 2
                n_led = 2
        elif bomba <= (1 * bombamax): # Até 100% da vazão - máx 8 leds
            if carga <= (0.3 * cargamax):
                v_turbina = 4
                n_led = 8
            elif carga <= (0.50 * cargamax):
                v_turbina = 3
                n_led = 7
            elif carga <= (0.70 * cargamax):
                v_turbina = 2
                n_led = 6
            elif carga <= (0.85 * cargamax):
                v_turbina = 2
                n_led = 5
            elif carga <= (0.95 * cargamax):
                v_turbina = 2
                n_led = 4
            else:
                v_turbina = 2
                n_led = 3

        #---------- Animação leds chamada ------------
        st.markdown("""
                <div style="font-size: 28px; font-weight: bold; color: green; margin-bottom: 0px; margin-top: 0px; background-color: #;">
                    Potência em carga resistiva representada por LEDs
                </div>""",    
                unsafe_allow_html=True)

        # Área da animação
        plot_area = st.empty()

        # Botão para iniciar a animação
        for _ in range(50):
            st.session_state.fig = desenhar_leds(n_led)
            plot_area.plotly_chart(st.session_state.fig, use_container_width=True)
        

    #------- Bancada com efeito rotação da turbina ----------
    with colc2:
        colc21, colc22 = st.columns([2,8])
        with colc21:
            pass
        with colc22:
            velocidade_turbina = ["aplicativo/static/vel_del.gif",
                                "aplicativo/static/vel_1.gif",
                                "aplicativo/static/vel_2.gif",
                                "aplicativo/static/vel_3.gif",
                                "aplicativo/static/vel_4.gif",
                                "aplicativo/static/vel_parado.gif"
                                ]
            st.image(velocidade_turbina[v_turbina])




        # Usando CSS para garantir que o GIF não perca a animação
        # st.markdown("""
        #     <style>
        #         .gif-container {
        #             display: flex;
        #             justify-content: flex-start;
        #             padding-left: 50px;
        #             padding-top: 20px;
        #         }
        #     </style>
        #     <div class="gif-container">
        #         <img src="aplicativo/static/""" + velocidade_turbina[v_turbina] + """ " width="300">
        #     </div>
        # """, unsafe_allow_html=True)



#----------- Menu lateral: comandos para o arduino ----------------

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

st.sidebar.markdown(custom_css,unsafe_allow_html=True)
st.sidebar.markdown("""
        <div style="font-size: 24px; font-weight: bold; color: green; margin-bottom: -5px; margin-top: -10px; background-color: #;">
            Enviar parâmetros
        </div>""",    
        unsafe_allow_html=True)

st.sidebar.markdown(custom_css,unsafe_allow_html=True)
st.sidebar.button('Enviar',key='ID8',on_click=enviar_comando)


#--------- Menu lateral: Funções de comunicação (ativar-desativar) -------------

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
# streamlit run aplicativo/base.py
