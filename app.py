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

# --- Configurações Essenciais ---
genai.configure(api_key=st.secrets["gemini_api_key"])
GITHUB_TOKEN = st.secrets.get("github_token")
GITHUB_USER = st.secrets.get("github_user")
REPO_NAME = "Entrevistador"

# <<< INFORMAÇÕES DO SEU GOOGLE FORM INSERIDAS AQUI >>>
GOOGLE_FORM_LINK = "https://docs.google.com/forms/d/e/1FAIpQLSfwbE7jsSBd1vRgh0alaCIkeqAuoTC8w-c4E6M7XnRAS9y-1Q/viewform" 
FORM_ID_ENTRY = "600654660" 

# --- Textos e Orientações da IA ---
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa. Sua personalidade é profissional, neutra e curiosa.

# 2. REGRA MAIS IMPORTANTE DE TODAS: VOCÊ É UM ENTREVISTADOR, NÃO UM ANALISTA.
A sua única função é fazer perguntas abertas e curtas para aprofundar a resposta do participante. NUNCA, em hipótese alguma:
- Dê a sua opinião.
- Analise a resposta do participante (como em "vantagens e desvantagens").
- Dê conselhos ou soluções.
- Explique a teoria da pesquisa ou mencione os seus conceitos.
- Faça mais de uma pergunta por vez.
Se você fizer qualquer uma destas coisas, você falhou na sua única tarefa. A sua única ferramenta é a próxima pergunta de aprofundamento.

# 3. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve para compreender como a felt accountability se manifesta no dia a dia da SUBCON/CGM-RJ.

# 5. PROTOCOLOS E REGRAS SECUNDÁRIAS
REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante ou uma tensão na resposta do participante, foque-se nesse tema e aprofunde-o.
PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Frases que concluem um raciocínio (ex: "é isso") NÃO são um pedido para parar. Se receber um pedido, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre se o participante confirmar.
REGRA 15 (ENCERRAMENTO NATURAL DA ENTREVISTA): O seu objetivo é uma entrevista de ~5 minutos. Após ter aprofundado um tema de forma satisfatória e sentir que tem material suficiente, você pode e deve iniciar o encerramento. Para fazer isso, a sua resposta final DEVE seguir esta estrutura de 3 passos:
1. Comece com uma frase de transição positiva e de agradecimento.
2. Continue com a frase de encerramento completa: "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
3. Anexe o sinalizador secreto <END_INTERVIEW> no final de tudo.
PROTOCOLO DE ESCLARECIMENTO: Se o participante não entender algo, explique o termo de forma simples e volte à pergunta.
PROTOCOLO DE EMOÇÕES: Se o participante usar palavras de forte carga emocional (ex: "raiva", "frustração"), a sua prioridade é explorar essa emoção com uma pergunta aberta.
PROTOCOLO ANTI-CONSELHOS: A sua função é entender, não resolver. Nunca dê conselhos ou soluções.
PROTOCOLO DE VARIAÇÃO DE LINGUAGEM: Evite soar repetitivo. Varie as suas frases de transição.
"""
vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria a essa situação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"

# --- Funções Auxiliares ---
def formatar_para_nvivo(chat_history, participant_id):
    timestamp_inicio = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-3))).strftime("%d-%m-%Y %H:%M")
    texto_formatado = f"ID Anónimo do Participante: {participant_id}\n"
    texto_formatado += f"Transcrição da Entrevista: {timestamp_inicio}\n\n"
    for msg in chat_history:
        role = "Participante" if msg['role'] == 'user' else 'Entrevistador'
        timestamp = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-3))).strftime("%H:%M:%S")
        texto_formatado += f"[{timestamp}] {role}: {msg['content']}\n"
    return texto_formatado

def save_transcript_to_github(chat_history, participant_id):
    if st.session_state.get('transcript_saved', False): return False
    try:
        conteudo_formatado = formatar_para_nvivo(chat_history, participant_id)
        file_path = f"transcricoes/entrevista_{participant_id}.txt"
        g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
        repo.create_file(file_path, f"Adicionando transcrição para {participant_id}", conteudo_formatado, branch="main")
        st.session_state.transcript_saved = True; return True
    except Exception as e:
        print(f"Erro ao salvar no GitHub: {e}"); return False

def stream_handler(stream):
    for chunk in stream:
        try: yield chunk.text
        except Exception: continue

# --- Lógica Principal da Aplicação ---

st.title("Felt Accountability no Setor Público - Entrevista")

# Gerenciador de Estágios da Entrevista
if 'stage' not in st.session_state:
    st.session_state.stage = "welcome"
    st.session_state.participant_id = f"p_{uuid.uuid4().hex[:8]}"

# ESTÁGIO 1: BOAS-VINDAS E LINK PARA O FORMULÁRIO
if st.session_state.stage == "welcome":
    st.header("Bem-vindo(a) à Pesquisa")
    st.write("Obrigado pela sua participação. A pesquisa é composta por duas partes:")
    st.markdown("1.  Um **questionário quantitativo** breve (no Google Forms).")
    st.markdown("2.  Uma **entrevista qualitativa** curta (aqui mesmo nesta página).")
    
    prefilled_link = f"{GOOGLE_FORM_LINK}?usp=pp_url&entry.{FORM_ID_ENTRY}={st.session_state.participant_id}"

    st.link_button("Passo 1: Ir para o Questionário Quantitativo", prefilled_link, type="primary")

    st.write("---")
    st.write("Após submeter o questionário, a página de confirmação pedirá para você **voltar a este separador** do seu browser.")

    if st.button("Já respondi, iniciar a entrevista"):
        st.session_state.stage = "interview"
        st.rerun()

# ESTÁGIO 2: A ENTREVISTA
elif st.session_state.stage == "interview":
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
        vinheta_escolhida = random.choice(vinhetas)
        st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Sua resposta...", key="chat_input"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty(); placeholder.markdown("Digitando…")
            try:
                start_index = 0
                for i, msg in enumerate(st.session_state.messages):
                    if msg['content'] in vinhetas: start_index = i; break
                relevant_messages = st.session_state.messages[start_index:]
                history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in relevant_messages]
                
                response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                
                text_generator = stream_handler(response_stream)
                full_response_text = placeholder.write_stream(text_generator)
                
                final_text_to_save = full_response_text.replace("<END_INTERVIEW>", "").strip()
                st.session_state.messages.append({"role": "model", "content": final_text_to_save})

                if "<END_INTERVIEW>" in full_response_text:
                    st.session_state.interview_over = True
                    save_transcript_to_github(st.session_state.messages, st.session_state.participant_id)
            
            except Exception as e: 
                placeholder.error(f"Ocorreu um erro: {e}")
        
        st.rerun()

# ESTÁGIO 3: FIM DA ENTREVISTA
if st.session_state.get('interview_over', False):
    st.info("A entrevista foi encerrada. Obrigado pela sua participação. Já pode fechar esta janela.")
    # Adiciona um botão de encerrar para salvar manualmente, caso o automático falhe
    if st.button("Garantir Salvamento e Encerrar"):
        save_transcript_to_github(st.session_state.messages, st.session_state.participant_id)
