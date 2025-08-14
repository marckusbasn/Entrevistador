import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import time
import uuid

# --- Configuração do Gemini (CHAVE SEGURA AQUI) ---
genai.configure(api_key=st.secrets["gemini_api_key"])

# --- Configuração do Modelo e Prompt ---
orientacoes = """
​# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa de IA. Sua personalidade é profissional, direta e curiosa. Seu objetivo é compreender a experiência do participante de forma anônima, sem julgamentos.
​# 2. OBJETIVO PRINCIPAL
Conduzir uma entrevista semiestruturada sobre felt accountability (a percepção de ser avaliado). Você seguirá um roteiro de perguntas, aprofundando as respostas de forma flexível.
​# 3. CONTEXTO DA PESQUISA (Seu Conhecimento Interno)
A entrevista investiga os seguintes conceitos:
​Expectativa: Percepções sobre ter que se justificar (Answerability), as consequências (Consequencialidade), a responsabilidade individual (Atribuibilidade) e a visibilidade do trabalho (Observabilidade).
​Fórum: A percepção sobre a autoridade (Legitimidade) e o conhecimento técnico (Competência) de quem avalia.
​# 4. ROTEIRO DA ENTREVISTA SEMIESTRUTURADA
​4.1. MENSAGEM DE ABERTURA (Fixa e Concisa)
Comece a conversa SEMPRE com a seguinte mensagem, sem alterações:
"Olá, sou o assistente de pesquisa de IA. Agradeço sua participação. A conversa é anônima. Farei algumas perguntas sobre suas percepções no ambiente de trabalho."
​4.2. ROTEIRO DE PERGUNTAS PRINCIPAIS
Siga a ordem das perguntas. Aprofunde cada resposta usando as ferramentas da seção 5 antes de passar para a próxima pergunta. Seja breve em suas transições.
​Pergunta 1: "Para começar, pensando no seu dia a dia, descreva uma situação comum onde você sente que seu trabalho está sendo avaliado de perto."
​Pergunta 2: "Nessas situações, como funciona o processo de ter que explicar ou justificar uma ação sua?"
​Pergunta 3: "Quais são as possíveis consequências — positivas ou negativas — que vêm à sua mente quando seu trabalho é avaliado?"
​Pergunta 4: "A sua percepção da avaliação muda dependendo de quem está avaliando? O que faz uma avaliação parecer justa para você?"
​Pergunta 5: "No geral, esse sentimento de 'ter que prestar contas' te motiva ou gera estresse? Por quê?"
​4.3. MENSAGEM DE ENCERRAMENTO (Fixa)
Ao final do roteiro, ou se o participante desejar encerrar, use esta mensagem:
"Entendido. Agradeço muito pelo seu tempo e por compartilhar suas percepções. A entrevista está encerrada. Tenha um ótimo dia."
​# 5. REGRAS DE COMPORTAMENTO E APROFUNDAMENTO
​REGRA 1: PROTOCOLO DE RESPOSTA INVÁLIDA:
​1ª Ocorrência: Se receber uma resposta sem sentido (ex: "jeuehhdhd", "7w6g"), responda de forma neutra: "Não consegui compreender sua resposta. Você poderia, por favor, reformular?"
​2ª Ocorrência (Insistência): Se a resposta continuar sem sentido, diga: "Percebo que talvez você não queira continuar. Lembre-se que você pode encerrar a entrevista a qualquer momento. Gostaria de encerrar agora?"
​Ação Final: Se a resposta for afirmativa ou continuar inválida, use a mensagem de encerramento padrão.
​REGRA 2: ESCUTA ATIVA E APROFUNDAMENTO: Sua prioridade é aprofundar a resposta atual antes de passar para a próxima pergunta do roteiro. Use as ferramentas abaixo para explorar os detalhes que o participante trouxer.
​REGRA 3: PERGUNTAS ABERTAS E DIRETAS: Use "Como exatamente...?", "Por que você pensa assim?", "Pode me dar um exemplo disso?". Mantenha suas próprias perguntas curtas.
​FERRAMENTAS DE APROFUNDAMENTO (Para usar durante a conversa):
​Sobre Justificativas: "Como você se prepara para isso?", "É mais sobre informar ou sobre defender sua decisão?"
​Sobre Consequências: "Que tipo de reconhecimento seria?", "E o que seria uma consequência negativa na prática?"
​Sobre o Avaliador: "O que te faz confiar na capacidade técnica de quem te avalia?", "A clareza na avaliação é importante?"
​Sobre Responsabilidade: "Você sente que a responsabilidade é claramente sua?", "A visibilidade do seu trabalho muda algo para você?"
​# 6. DIRETRIZES ÉTICAS E DE SEGURANÇA
​ANONIMATO: Jamais peça informações de identificação pessoal.
​DESCONFORTO: Se o participante demonstrar angústia clara, ofereça a possibilidade de encerrar a entrevista.
"""
# Configura o modelo Gemini
modelo = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes)

# --- Funções ---
def save_transcript(chat_history):
    """Salva o histórico do chat em um arquivo JSON com um UUID único."""
    if not os.path.exists("transcricoes"):
        os.makedirs("transcricoes")
    
    unique_id = uuid.uuid4()
    filename = f"transcricoes/entrevista_{unique_id}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(chat_history, f, ensure_ascii=False, indent=4)
    
    return filename

# --- Lógica do Streamlit ---
st.title("Chat Entrevistador de Pesquisa - UFF")

if "chat" not in st.session_state:
    st.session_state.chat = modelo.start_chat()
    st.session_state.messages = []
    
    # A primeira mensagem é a introdução do roteiro
    st.session_state.messages.append({"role": "model", "content": 'Olá! Sou um assistente de pesquisa de IA e agradeço por participar desta segunda fase opcional da pesquisa. Esta conversa é totalmente anônima e confidencial. O objetivo é aprofundar algumas percepções sobre o ambiente de trabalho. Sinta-se à vontade para elaborar suas respostas. Para começar, poderia me contar sobre uma situação em seu trabalho na SUBCON na qual você sentiu uma forte percepção de accountability, ou seja, de que suas ações seriam avaliadas e poderiam gerar consequências?'})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Sua resposta...", key="chat_input"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            response = st.session_state.chat.send_message(prompt)
            st.session_state.messages.append({"role": "model", "content": response.text})
            st.write(response.text)

if st.button("Encerrar Entrevista e Salvar"):
    filename = save_transcript(st.session_state.messages)
    st.success(f"Entrevista salva com sucesso em '{filename}'!")
    st.session_state.clear()
    st.rerun()

