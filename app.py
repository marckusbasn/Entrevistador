import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import time
import uuid
from github import Github
import random # <--- Biblioteca para escolher vinhetas aleatoriamente

# --- Configuração do Gemini (CHAVE SEGURA AQUI) ---
genai.configure(api_key=st.secrets["gemini_api_key"])

# --- Configuração do Modelo e Prompt ---
# Seu prompt foi movido para uma variável separada para melhor organização.
# A vinheta será adicionada a essa instrução.
orientacoes_base = """
# IDENTIDADE E PERSONA
Você é um assistente de pesquisa virtual, desenvolvido para um projeto de Mestrado Acadêmico em Administração da Universidade Federal Fluminense (UFF). Sua personalidade é profissional, neutra, curiosa, acolhedora e empática. Você nunca julga ou emite opiniões. Seu único propósito é compreender a experiência do participante.  

# OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa em profundidade para compreender como a felt accountability se manifesta no contexto organizacional vivenciado pelos servidores públicos da SUBCON/CGM-RJ. Você deve explorar as percepções, histórias e sentimentos por trás do fenômeno, focando nos "porquês".  

# CONTEXTO DA PESQUISA
Para seu conhecimento, felt accountability é definida como a percepção e expectativa individual de que suas decisões ou comportamentos serão avaliados por uma audiência relevante, gerando consequências positivas ou negativas. Sua tarefa é explorar as dimensões que compõem essa percepção, especialmente:  
Answerability: A expectativa de ter que explicar e justificar as próprias ações.  
Consequencialidade: A expectativa de que haverá recompensas ou sanções como resultado das ações.  
Legitimidade e Competência do Fórum: A percepção do servidor sobre a autoridade (legitimidade) e a capacidade técnica (competência) da instância que o avalia (o "fórum" ou "audiência").  
...
(O resto do seu prompt original está aqui, com as regras de aprofundamento e ética.)
...
"""

# Vinhetas para o sistema de rotação
vinhetas = [
    # Opção A
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar e o que você sentiria?",
    # Opção B
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria e o que pensaria sobre essa avaliação?",
    # Opção C
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]

# Mensagem de abertura fixa
mensagem_abertura = "Olá! Sou um assistente de pesquisa de IA. Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente de trabalho. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões."


# --- Funções ---
def save_transcript_to_github(chat_history):
    """Salva o histórico do chat em um arquivo JSON e faz o commit no GitHub."""
    
    # Preenchido com o nome do seu repositório
    repo_name = "Entrevistador" 
    branch_name = "main"

    try:
        g = Github(st.secrets["github_token"])
        user = g.get_user(st.secrets["github_user"])
        repo = user.get_repo(repo_name)

        unique_id = uuid.uuid4()
        file_path = f"transcricoes/entrevista_{unique_id}.json"
        
        try:
            repo.get_contents("transcricoes")
        except:
            repo.create_file("transcricoes/.gitkeep", "Initial commit", "")

        json_content = json.dumps(chat_history, ensure_ascii=False, indent=4)
        
        repo.create_file(file_path, f"Adicionando transcrição da entrevista {unique_id}", json_content, branch=branch_name)
        
        return f"Entrevista salva no GitHub em {repo_name}/{file_path}"
    
    except Exception as e:
        return f"Erro ao salvar no GitHub: {e}"

# --- Lógica do Streamlit ---
st.title("Chat Entrevistador de Pesquisa - UFF")

if "chat" not in st.session_state:
    
    # Seleciona uma vinheta aleatória e a anexa ao prompt
    vinheta_escolhida = random.choice(vinhetas)
    prompt_completo = orientacoes_base + "\n" + vinheta_escolhida
    
    # Inicia o modelo com o novo prompt
    modelo = genai.GenerativeModel('gemini-1.5-flash', system_instruction=prompt_completo)
    st.session_state.chat = modelo.start_chat()
    st.session_state.messages = []
    
    # Envia a mensagem de abertura e a vinheta para o participante
    st.session_state.messages.append({"role": "model", "content": mensagem_abertura + "\n\n" + vinheta_escolhida})

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
    with st.spinner("Salvando entrevista no GitHub..."):
        status_message = save_transcript_to_github(st.session_state.messages)
        st.write(status_message)
    st.session_state.clear()
    time.sleep(2)
    st.rerun()

