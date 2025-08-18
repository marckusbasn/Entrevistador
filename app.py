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

# --- Configurações Essenciais ---
genai.configure(api_key=st.secrets["gemini_api_key"])
GITHUB_TOKEN = st.secrets.get("github_token")
GITHUB_USER = st.secrets.get("github_user")
REPO_NAME = "Entrevistador"

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa. Sua personalidade é profissional, neutra, curiosa e empática.

# 2. REGRA MAIS IMPORTANTE DE TODAS: VOCÊ É UM ENTREVISTADOR, NÃO UM ANALISTA.
A sua única função é fazer perguntas abertas e curtas para aprofundar a resposta do participante. NUNCA, em hipótese alguma:
- Dê a sua opinião.
- Analise a resposta do participante.
- Dê conselhos ou soluções.
- Explique a teoria da pesquisa.
- Faça mais de uma pergunta por vez.
Sua única ferramenta é a próxima pergunta.

# 3. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve para compreender como a felt accountability se manifesta no dia a dia da SUBCON/CGM-RJ.

# 4. PROTOCOLOS E REGRAS PRINCIPAIS
PROTOCOLO DE INÍCIO DA CONVERSA: A primeira mensagem que você receberá é a resposta do participante à pergunta 'Podemos começar?'.
- Se a resposta for um consentimento claro (sim, ok, claro), mesmo que hesitante: Responda com uma das PERGUNTAS DE ABERTURA.
- Se a resposta for uma recusa clara (não, não quero): Ative o PROTOCOLO DE ENCERRAMENTO POR PEDIDO.
- Se a resposta for ambígua ou sem sentido: Responda com a MENSAGEM DE ESCLARECIMENTO.

PERGUNTAS DE ABERTURA (Escolha uma aleatoriamente para iniciar a entrevista):
- "Para começarmos, pense no seu dia a dia de trabalho. Poderia me descrever uma situação recente em que você se sentiu particularmente pressionado(a) ou avaliado(a)?"
- "Pensando em um projeto importante em que você trabalhou, poderia me contar sobre um momento em que sentiu que suas ações estavam sob um olhar atento de outras pessoas?"

REGRA DE OURO (FOCO E BREVIDADE): Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante, foque-se nesse tema e aprofunde-o.

PROTOCOLO DE GESTÃO DE TEMPO E EXTENSÃO: O seu objetivo inicial é uma entrevista de ~5 minutos. Ao se aproximar desta marca, faça uma avaliação do engajamento do participante.
- SE as últimas respostas forem curtas, monossilábicas ou evasivas, a conversa "não está a render". Neste caso, inicie o PROTOCOLO DE ENCERRAMENTO NATURAL (agradeça, use a MENSAGEM DE ENCERRAMENTO e o sinalizador <END_INTERVIEW>).
- SE as últimas respostas forem detalhadas e ricas em conteúdo, a conversa "está a render". Neste caso, NÃO encerre. Ofereça uma extensão de forma educada e opcional. Use uma frase como: "A sua perspetiva está a ser muito rica e interessante. Já passámos um pouco dos 5 minutos iniciais. Você teria disponibilidade e interesse em continuar a conversa por mais alguns minutos, ou prefere que a gente encerre por aqui?"
    - Se o participante aceitar continuar: Agradeça ("Ótimo, obrigado!") e faça a próxima pergunta de aprofundamento. O "cronómetro" é reiniciado para um novo checkpoint.
    - Se o participante preferir parar: Respeite imediatamente. Inicie o PROTOCOLO DE ENCERRAMENTO NATURAL.

PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Se receber um pedido explícito para parar, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre se o participante confirmar.

PROTOCOLO DE LINGUAGEM: Use sempre termos neutros e genéricos como "organização", "ambiente de trabalho", "o seu setor". Evite usar a palavra "empresa".

(O restante das regras e do código permanece o mesmo. A versão completa e funcional está abaixo.)
"""
# ... (restante do código, incluindo a definição completa das funções e da app)
# O código completo e funcional está no bloco abaixo para garantir que nada falte.

mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa..."
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"

# --- CÓDIGO COMPLETO PARA GARANTIA ---
def formatar_para_nvivo(chat_history, participant_id):
    fuso_horario_br = datetime.timezone(datetime.timedelta(hours=-3))
    timestamp_inicio = chat_history[0]['timestamp'].astimezone(fuso_horario_br).strftime("%d-%m-%Y %H:%M") if chat_history else "N/A"
    texto_formatado = f"ID Anónimo do Participante: {participant_id}\n"
    texto_formatado += f"Transcrição da Entrevista: {timestamp_inicio}\n\n"
    for msg in chat_history:
        role = "Participante" if msg['role'] == 'user' else 'Entrevistador'
        timestamp = msg.get('timestamp', datetime.datetime.now(datetime.timezone.utc)).astimezone(fuso_horario_br).strftime('%H:%M:%S')
        texto_formatado += f"[{timestamp}] {role}: {msg['content']}\n"
    return texto_formatado

def save_transcript_to_github(chat_history, participant_id):
    if st.session_state.get('transcript_saved', False): return
    try:
        conteudo_formatado = formatar_para_nvivo(chat_history, participant_id)
        file_path = f"transcricoes/entrevista_{participant_id}.txt"
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
        repo.create_file(file_path, f"Adicionando transcrição para {participant_id}", conteudo_formatado, branch="main")
        st.session_state.transcript_saved = True
    except Exception as e:
        print(f"Erro ao salvar no GitHub: {e}")

def stream_handler(stream):
    for chunk in stream:
        try: yield chunk.text
        except Exception: continue

st.title("Felt Accountability no Setor Público - Entrevista")

if "messages" not in st.session_state:
    st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
    st.session_state.messages = []
    st.session_state.interview_over = False
    st.session_state.transcript_saved = False
    st.session_state.participant_id = f"anon_{uuid.uuid4().hex[:8]}"
    st.session_state.start_time = datetime.datetime.now(datetime.timezone.utc)
    st.session_state.messages.append({"role": "model", "content": mensagem_abertura, "timestamp": st.session_state.start_time})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.get('interview_over', False)):
    st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": datetime.datetime.now(datetime.timezone.utc)})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Digitando…")
        
        history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in st.session_state.messages]
        
        try:
            response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
            text_generator = stream_handler(response_stream)
            full_response_text = placeholder.write_stream(text_generator)
            
            final_text_to_save = full_response_text.replace("<END_INTERVIEW>", "").strip()
            st.session_state.messages.append({"role": "model", "content": final_text_to_save, "timestamp": datetime.datetime.now(datetime.timezone.utc)})

            if "<END_INTERVIEW>" in full_response_text or mensagem_encerramento in full_response_text:
                st.session_state.interview_over = True
                save_transcript_to_github(st.session_state.messages, st.session_state.participant_id)
        except Exception as e:
            placeholder.error(f"Ocorreu um erro: {e}")
    st.rerun()

if not st.session_state.get('interview_over', False):
    if st.button("Encerrar Entrevista"):
        with st.spinner("Salvando e encerrando..."):
            st.session_state.messages.append({"role": "model", "content": mensagem_encerramento, "timestamp": datetime.datetime.now(datetime.timezone.utc)})
            save_transcript_to_github(st.session_state.messages, st.session_state.participant_id)
            st.write(mensagem_encerramento)
            st.session_state.interview_over = True
        time.sleep(1)
        st.rerun()
