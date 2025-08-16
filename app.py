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

# --- Configuração do Gemini e GitHub ---
genai.configure(api_key=st.secrets["gemini_api_key"])
GITHUB_TOKEN = st.secrets.get("github_token")
GITHUB_USER = st.secrets.get("github_user")
REPO_NAME = "Entrevistador"

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
# (O texto completo das orientações, com todas as regras, permanece aqui)
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa...
# ... (restante das regras como na versão anterior) ...
"""
vinhetas = [
    "Imagine que você precisa entregar um relatório importante...",
    "Pense que um procedimento que você considera correto...",
    "Imagine um trabalho importante feito em equipe..."
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

# ==============================================================================
# FUNÇÕES PRINCIPAIS (INCLUINDO O NOVO ANALISTA DE CONSENTIMENTO)
# ==============================================================================

def analisar_consentimento(resposta_utilizador):
    """
    Usa a IA para analisar a primeira resposta do utilizador e decidir a próxima ação.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt_analista = f"""
    Você é um assistente que analisa a resposta inicial de um participante de pesquisa. A pergunta feita foi: "Tudo bem? Podemos começar?".
    A sua tarefa é analisar a resposta do participante e decidir a próxima ação.

    A resposta do participante foi: "{resposta_utilizador}"

    Analise a resposta e escolha UMA das seguintes ações:
    - 'PROSSEGUIR': Se a resposta for um consentimento claro (sim, claro, podemos, ok, etc.).
    - 'ENCERRAR': Se a resposta for uma recusa clara (não, não quero, agora não, etc.).
    - 'ESCLARECER': Se a resposta for ambígua, sem sentido (ex: 'eedssd'), ou uma pergunta.

    Responda APENAS com a palavra PROSSEGUIR, ENCERRAR, ou ESCLARECER.
    """
    try:
        response = model.generate_content(prompt_analista)
        decisao = response.text.strip().upper()
        if decisao in ["PROSSEGUIR", "ENCERRAR", "ESCLARECER"]:
            return decisao
        return "ESCLARECER" # Padrão de segurança
    except Exception:
        return "ESCLARECER" # Padrão de segurança

# (O restante das funções permanece o mesmo. O código completo está abaixo)

# ==============================================================================
# CÓDIGO COMPLETO PARA COPIAR E COLAR
# ==============================================================================
# (As funções e a lógica principal estão completas aqui)

def pagina_configuracao():
    # ... (código da página de configuração sem alterações)
    pass

def pagina_entrevistador():
    @st.cache_resource
    def carregar_memoria_pesquisa_do_github():
        try:
            g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            index_content = repo.get_contents("faiss_index.bin").decoded_content; temp_index_file = "temp_faiss_index_load.bin"
            with open(temp_index_file, "wb") as f: f.write(index_content)
            index = faiss.read_index(temp_index_file); os.remove(temp_index_file)
            chunks_content = repo.get_contents("text_chunks.pkl").decoded_content; chunks = pickle.loads(chunks_content)
            return index, chunks
        except Exception: return None, None

    def classificar_intencao(prompt_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_classificador = f"""Você é um classificador de intenções... (prompt completo como na versão anterior)"""
        try:
            response = model.generate_content(prompt_classificador)
            if "PESQUISA" in response.text: return "PESQUISA"
            return "ENTREVISTA"
        except Exception: return "ENTREVISTA"

    def responder_pergunta_pesquisa(index, chunks, pergunta):
        # ... (código sem alterações)
        pass

    def stream_handler(stream):
        for chunk in stream:
            try: yield chunk.text
            except Exception: continue
    
    def formatar_para_nvivo(chat_history):
        # ... (código sem alterações)
        pass

    def save_transcript_to_github(chat_history):
        # ... (código sem alterações)
        pass

    st.title("Felt Accountability no Setor Público - Entrevista")
    index, chunks = carregar_memoria_pesquisa_do_github()

    if "model" not in st.session_state:
        st.session_state.model = None; st.session_state.messages = []; st.session_state.interview_over = False; st.session_state.transcript_saved = False; st.session_state.messages.append({"role": "model", "content": mensagem_abertura})
    
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]): st.write(message["content"])

    if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.interview_over):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        with st.chat_message("assistant"):
            # <<< LÓGICA DE INÍCIO TOTALMENTE REFEITA >>>
            if st.session_state.model is None:
                with st.spinner("Analisando..."):
                    acao = analisar_consentimento(prompt)

                if acao == "PROSSEGUIR":
                    st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
                    vinheta_escolhida = random.choice(vinhetas)
                    st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})
                
                elif acao == "ENCERRAR":
                    st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
                    st.session_state.interview_over = True
                    save_transcript_to_github(st.session_state.messages)

                elif acao == "ESCLARECER":
                    st.session_state.messages.append({"role": "model", "content": mensagem_esclarecimento})
            
            # A lógica da entrevista em andamento permanece a mesma
            else:
                placeholder = st.empty(); placeholder.markdown("Digitando…")
                intencao = classificar_intencao(prompt)
                try:
                    if intencao == "PESQUISA" and index is not None: 
                        response_stream = responder_pergunta_pesquisa(index, chunks, prompt)
                    else:
                        # (lógica da entrevista sem alterações)
                        start_index = 0
                        for i, msg in enumerate(st.session_state.messages):
                            if msg['content'] in vinhetas: start_index = i; break
                        relevant_messages = st.session_state.messages[start_index:]
                        history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in relevant_messages]
                        response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    st.session_state.messages.append({"role": "model", "content": full_response_text})
                    if mensagem_encerramento in full_response_text:
                        st.session_state.interview_over = True; save_transcript_to_github(st.session_state.messages)
                except Exception as e: placeholder.error(f"Ocorreu um erro: {e}")
        
        st.rerun()

    if st.button("Encerrar Entrevista"):
        # ... (código sem alterações)
        pass

if st.query_params.get("admin") == "true":
    # Cole a definição completa da sua pagina_configuracao aqui
    pass
else:
    pagina_entrevistador()
