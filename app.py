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

# 4. CONCEITOS-GUIA PARA AS SUAS PERGUNTAS (NUNCA OS MENCIONE DIRETAMENTE)
Use os seguintes temas como inspiração para as suas perguntas de aprofundamento, mas NUNCA os revele ao participante:
- Justificativas (Answerability): O sentimento de ter que explicar ou defender as suas ações.
- Consequências (Consequencialidade): A percepção de que haverá recompensas ou sanções.
- Atribuição (Atribuibilidade): A ligação clara entre uma ação e o indivíduíduo.
- Visibilidade (Observabilidade): A sensação de estar a ser observado.
- Legitimidade do Avaliador: A percepção de que quem avalia tem autoridade para o fazer.
- Competência do Avaliador: A percepção de que quem avalia tem conhecimento técnico para o fazer.

# 5. PROTOCOLOS E REGRAS SECUNDÁRIAS
REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante, foque-se nesse tema e aprofunde-o.

PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Este protocolo NÃO se aplica a respostas curtas como "não" ou "não sei" dadas a uma pergunta da entrevista. Se receber um pedido explícito para parar, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre se o participante confirmar.

REGRA 10 (LIDANDO COM RESPOSTAS CURTAS OU EVASIVAS): Se o participante der uma resposta muito curta, negativa ou evasiva a uma pergunta sobre uma situação (ex: "não", "não me lembro", "não sei"), NÃO tente encerrar a entrevista. A sua tarefa é tentar de outra forma. Valide a resposta e faça uma pergunta aberta alternativa para o ajudar.

REGRA 15 (ENCERRAMENTO NATURAL DA ENTREVISTA): Inicie o encerramento APENAS quando você tiver aprofundado um tema com várias perguntas de seguimento (pelo menos 3 a 4 trocas de mensagens) E a resposta mais recente do participante for curta ou conclusiva. NÃO encerre a entrevista logo após uma resposta longa e detalhada. Para encerrar, sua resposta final DEVE seguir esta estrutura de 3 passos: 1. Comece com uma frase de transição positiva. 2. Continue com a frase de encerramento completa: "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!" 3. Anexe o sinalizador secreto <END_INTERVIEW> no final de tudo.
"""
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

def pagina_configuracao():
    st.title("⚙️ Painel de Controlo do Pesquisador")
    st.write("Use esta ferramenta para criar ou atualizar a 'memória' do seu chatbot.")
    uploaded_file = st.file_uploader("Selecione o seu ficheiro `projeto.txt`", type="txt")
    if uploaded_file is not None:
        if st.button("Criar e Salvar Memória no GitHub"):
            with st.spinner("A processar o documento..."):
                try:
                    document_text = uploaded_file.getvalue().decode("utf-8"); text_chunks = [chunk for chunk in document_text.split('\n\n') if chunk.strip()]
                    embedding_model = 'models/embedding-001'; embeddings = genai.embed_content(model=embedding_model, content=text_chunks, task_type="retrieval_document")
                    embeddings_np = np.array(embeddings['embedding']).astype('float32'); d = embeddings_np.shape[1]; index = faiss.IndexFlatL2(d); index.add(embeddings_np)
                    temp_index_file = "temp_faiss_index.bin"; faiss.write_index(index, temp_index_file)
                    with open(temp_index_file, "rb") as f: index_bytes = f.read()
                    os.remove(temp_index_file)
                    g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
                    def upload_or_update_file(file_path, commit_message, content):
                        try:
                            contents = repo.get_contents(file_path)
                            repo.update_file(contents.path, commit_message, content, contents.sha, branch="main"); st.write(f"Ficheiro '{file_path}' atualizado.")
                        except:
                            repo.create_file(file_path, commit_message, content, branch="main"); st.write(f"Ficheiro '{file_path}' criado.")
                    upload_or_update_file("faiss_index.bin", "Atualizando índice FAISS", index_bytes)
                    chunks_bytes = pickle.dumps(text_chunks); upload_or_update_file("text_chunks.pkl", "Atualizando pedaços de texto", chunks_bytes)
                    st.success("Memória criada e salva com sucesso!"); st.info("Aguarde um minuto e depois partilhe o link normal com os entrevistados."); st.cache_resource.clear()
                except Exception as e: st.error(f"Ocorreu um erro: {e}")

def pagina_entrevistador():
    @st.cache_resource
    def carregar_memoria_pesquisa_do_github():
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            index_content = repo.get_contents("faiss_index.bin").decoded_content
            temp_index_file = "temp_faiss_index_load.bin"
            with open(temp_index_file, "wb") as f: f.write(index_content)
            index = faiss.read_index(temp_index_file)
            os.remove(temp_index_file)
            chunks_content = repo.get_contents("text_chunks.pkl").decoded_content
            chunks = pickle.loads(chunks_content)
            return index, chunks
        except Exception:
            # <<< CORREÇÃO CRÍTICA AQUI >>>
            # Garante que, em caso de falha, a função retorna uma tupla de dois elementos.
            return None, None

    def analisar_consentimento(resposta_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_analista = f"""Analise a resposta do participante à pergunta 'Podemos começar?'. A resposta foi: "{resposta_utilizador}". Responda APENAS com 'PROSSEGUIR', 'ENCERRAR', ou 'ESCLARECER'."""
        try:
            response = model.generate_content(prompt_analista)
            decisao = response.text.strip().upper()
            if decisao in ["PROSSEGUIR", "ENCERRAR", "ESCLARECER"]: return decisao
            return "ESCLARECER"
        except Exception: return "ESCLARECER"

    def classificar_intencao(prompt_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_classificador = f"""Classifique a intenção: 'ENTREVISTA' (resposta à entrevista) ou 'PESQUISA' (pergunta sobre o projeto). Frase: "{prompt_utilizador}". Exemplos: 'Ficaria com raiva.' -> ENTREVISTA. 'Qual o objetivo?' -> PESQUISA. 'Não entendi.' -> ENTREVISTA."""
        try:
            response = model.generate_content(prompt_classificador)
            if "PESQUISA" in response.text: return "PESQUISA"
            return "ENTREVISTA"
        except Exception: return "ENTREVISTA"

    def responder_pergunta_pesquisa(index, chunks, pergunta):
        embedding_model = 'models/embedding-001'; pergunta_embedding = genai.embed_content(model=embedding_model, content=pergunta, task_type="retrieval_query")['embedding']
        k = 3; D, I = index.search(np.array([pergunta_embedding]).astype('float32'), k)
        contexto_relevante = " ".join([chunks[i] for i in I[0]])
        model = genai.GenerativeModel('gemini-1.5-flash'); prompt_final = f"Baseado nisto: {contexto_relevante}. Responda a: \"{pergunta}\""
        response = model.generate_content(prompt_final, stream=True)
        return response

    def stream_handler(stream):
        for chunk in stream:
            try: yield chunk.text
            except Exception: continue
    
    def formatar_para_nvivo(chat_history, participant_id):
        fuso_horario_br = datetime.timezone(datetime.timedelta(hours=-3))
        timestamp_inicio = datetime.datetime.now(datetime.timezone.utc).astimezone(fuso_horario_br).strftime("%d-%m-%Y %H:%M"); texto_formatado = f"ID Anónimo do Participante: {participant_id}\n"; texto_formatado += f"Transcrição da Entrevista: {timestamp_inicio}\n\n"
        for msg in chat_history:
            role = "Participante" if msg['role'] == 'user' else 'Entrevistador'
            timestamp = msg.get('timestamp', datetime.datetime.now(datetime.timezone.utc)).astimezone(fuso_horario_br).strftime('%H:%M:%S')
            texto_formatado += f"[{timestamp}] {role}: {msg['content']}\n"
        return texto_formatado

    def save_transcript_to_github(chat_history, participant_id):
        if st.session_state.get('transcript_saved', False): return
        try:
            conteudo_formatado = formatar_para_nvivo(chat_history, participant_id); file_path = f"transcricoes/entrevista_{participant_id}.txt"
            g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            repo.create_file(file_path, f"Adicionando transcrição para {participant_id}", conteudo_formatado, branch="main")
            st.session_state.transcript_saved = True
        except Exception as e: print(f"Erro ao salvar no GitHub: {e}")

    st.title("Felt Accountability no Setor Público - Entrevista")
    index, chunks = carregar_memoria_pesquisa_do_github()
    
    if "messages" not in st.session_state:
        st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
        st.session_state.messages = []
        st.session_state.interview_over = False
        st.session_state.transcript_saved = False
        st.session_state.messages.append({"role": "model", "content": mensagem_abertura, "timestamp": datetime.datetime.now(datetime.timezone.utc)})

    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.write(message["content"])

    if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.get('interview_over', False)):
        st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": datetime.datetime.now(datetime.timezone.utc)})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            placeholder = st.empty(); placeholder.markdown("Digitando…")
            history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in st.session_state.messages]
            try:
                if len(st.session_state.messages) < 3: # Se é a primeira resposta do utilizador
                     acao = analisar_consentimento(prompt)
                     if acao == "PROSSEGUIR":
                         full_response_text = random.choice(vinhetas)
                         placeholder.write(full_response_text)
                     elif acao == "ENCERRAR":
                         full_response_text = mensagem_encerramento
                         st.session_state.interview_over = True
                         placeholder.write(full_response_text)
                     else: # ESCLARECER
                         full_response_text = mensagem_esclarecimento
                         placeholder.write(full_response_text)
                else:
                    intencao = classificar_intencao(prompt)
                    if intencao == "PESQUISA" and index is not None: response_stream = responder_pergunta_pesquisa(index, chunks, prompt)
                    else: response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                
                final_text_to_save = full_response_text.replace("<END_INTERVIEW>", "").strip()
                st.session_state.messages.append({"role": "model", "content": final_text_to_save, "timestamp": datetime.datetime.now(datetime.timezone.utc)})
                if "<END_INTERVIEW>" in full_response_text or mensagem_encerramento in full_response_text:
                    st.session_state.interview_over = True
                    save_transcript_to_github(st.session_state.messages, f"finalizado_{uuid.uuid4().hex[:6]}")
            except Exception as e: placeholder.error(f"Ocorreu um erro: {e}")
        st.rerun()

    if not st.session_state.get('interview_over', False):
        if st.button("Encerrar Entrevista"):
             with st.spinner("Salvando e encerrando..."):
                st.session_state.messages.append({"role": "model", "content": mensagem_encerramento, "timestamp": datetime.datetime.now(datetime.timezone.utc)})
                save_transcript_to_github(st.session_state.messages, f"manual_{uuid.uuid4().hex[:6]}")
                st.write(mensagem_encerramento); st.session_state.interview_over = True
             time.sleep(1); st.rerun()

if st.query_params.get("admin") == "true":
    pagina_configuracao()
else:
    pagina_entrevistador()
