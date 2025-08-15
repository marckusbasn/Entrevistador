import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import time
import uuid
from github import Github
import random
import google.api_core.exceptions
import faiss
import numpy as np
import pickle
from io import BytesIO

# --- Configuração do Gemini e GitHub (CHAVE SEGURA AQUI) ---
genai.configure(api_key=st.secrets["gemini_api_key"])
GITHUB_TOKEN = st.secrets.get("github_token")
GITHUB_USER = st.secrets.get("github_user")
REPO_NAME = "Entrevistador"

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
# (O seu texto longo de orientacoes_completas permanece aqui)
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa...
"""
# (vinhetas, mensagem_abertura, mensagem_encerramento permanecem aqui)
vinhetas = [
    "Imagine que você precisa entregar um relatório importante...",
    "Pense que um procedimento que você considera correto...",
    "Imagine um trabalho importante feito em equipe..."
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa..."
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções..."

# --- FUNÇÕES ---

@st.cache_resource
def carregar_memoria_pesquisa_do_github():
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
        
        index_content = repo.get_contents("faiss_index.bin").decoded_content
        temp_index_file = "temp_faiss_index_load.bin"
        with open(temp_index_file, "wb") as f:
            f.write(index_content)
        index = faiss.read_index(temp_index_file)
        os.remove(temp_index_file)

        chunks_content = repo.get_contents("text_chunks.pkl").decoded_content
        chunks = pickle.loads(chunks_content)
        
        return index, chunks
    except Exception:
        return None, None

def classificar_intencao(prompt_utilizador):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt_classificador = f"Analise a seguinte frase de um utilizador: '{prompt_utilizador}'.\nO utilizador está a fazer uma pergunta sobre a pesquisa ou está a responder a uma pergunta da entrevista?\nResponda APENAS com a palavra 'PESQUISA' ou 'ENTREVISTA'."
    try:
        response = model.generate_content(prompt_classificador)
        return response.text.strip()
    except Exception:
        return "ENTREVISTA"

def responder_pergunta_pesquisa(index, chunks, pergunta):
    embedding_model = 'models/embedding-001'
    pergunta_embedding = genai.embed_content(model=embedding_model, content=pergunta, task_type="retrieval_query")['embedding']
    k = 3
    D, I = index.search(np.array([pergunta_embedding]).astype('float32'), k)
    contexto_relevante = " ".join([chunks[i] for i in I[0]])
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt_final = f"Com base no seguinte contexto extraído do projeto de pesquisa:\n---\n{contexto_relevante}\n---\nPor favor, responda à seguinte pergunta do utilizador de forma clara e concisa: \"{pergunta}\""
    response = model.generate_content(prompt_final, stream=True)
    return response

def stream_handler(stream):
    for chunk in stream:
        try: yield chunk.text
        except Exception: continue

def save_transcript_to_github(chat_history):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
    unique_id = uuid.uuid4()
    file_path = f"transcricoes/entrevista_{unique_id}.json"
    json_content = json.dumps(chat_history, ensure_ascii=False, indent=4)
    repo.create_file(file_path, f"Adicionando transcrição da entrevista {unique_id}", json_content, branch="main")

# --- INTERFACE PRINCIPAL ---

st.title("Felt Accountability no Setor Público - Entrevista")

index, chunks = carregar_memoria_pesquisa_do_github()

if "model" not in st.session_state:
    st.session_state.model = None
    st.session_state.messages = []
    st.session_state.interview_over = False 
    st.session_state.messages.append({"role": "model", "content": mensagem_abertura})

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.interview_over):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        if st.session_state.model is None:
            negative_responses = ["não", "nao", "não quero", "nao quero", "não, obrigado", "nao, obrigado"]
            if prompt.lower().strip() in negative_responses:
                st.write(mensagem_encerramento)
                st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
                st.session_state.interview_over = True
                st.rerun() 
            else:
                st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
                vinheta_escolhida = random.choice(vinhetas)
                st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})
                st.rerun()
        else:
            placeholder = st.empty()
            placeholder.markdown("Digitando…")
            
            intencao = classificar_intencao(prompt)
            
            try:
                if intencao == "PESQUISA" and index is not None:
                    response_stream = responder_pergunta_pesquisa(index, chunks, prompt)
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    st.session_state.messages.append({"role": "model", "content": full_response_text})
                else:
                    start_index = 0
                    for i, msg in enumerate(st.session_state.messages):
                        if msg['content'] in vinhetas: start_index = i; break
                    relevant_messages = st.session_state.messages[start_index:]
                    history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in relevant_messages]
                    response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    st.session_state.messages.append({"role": "model", "content": full_response_text})
            except Exception as e:
                placeholder.error(f"Ocorreu um erro: {e}")

if st.button("Encerrar Entrevista"):
    with st.spinner("Salvando e encerrando..."):
        st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
        save_transcript_to_github(st.session_state.messages)
        st.write(mensagem_encerramento)
        st.session_state.interview_over = True
    time.sleep(1) 
    st.rerun()
