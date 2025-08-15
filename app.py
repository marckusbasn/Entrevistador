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
GITHUB_TOKEN = st.secrets["github_token"]
GITHUB_USER = st.secrets["github_user"]
REPO_NAME = "Entrevistador" # O nome do seu repositório

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
# (O seu texto longo de orientacoes_completas permanece aqui, omitido por brevidade)
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

# ==============================================================================
# PÁGINA 2: CONFIGURAÇÃO DA MEMÓRIA (LÓGICA DE INDEXAÇÃO)
# ==============================================================================
def pagina_configuracao():
    st.title("⚙️ Configuração da Memória da Pesquisa")
    st.write("Aqui você pode 'ensinar' o chatbot sobre a sua pesquisa. Ele usará esta informação para responder a perguntas sobre o projeto durante a entrevista.")

    st.markdown("### Passo 1: Carregue o seu projeto de pesquisa")
    uploaded_file = st.file_uploader("Selecione o seu ficheiro `projeto.txt`", type="txt")

    if uploaded_file is not None:
        st.success(f"Ficheiro '{uploaded_file.name}' carregado com sucesso!")
        
        st.markdown("### Passo 2: Crie e Salve a Memória")
        if st.button("Criar e Salvar Memória no GitHub"):
            with st.spinner("A processar o documento e a criar a memória... Isto pode demorar alguns minutos."):
                try:
                    # Lê o conteúdo do ficheiro carregado
                    document_text = uploaded_file.getvalue().decode("utf-8")
                    text_chunks = [chunk for chunk in document_text.split('\n\n') if chunk.strip()]
                    
                    embedding_model = 'models/embedding-001'
                    embeddings = genai.embed_content(model=embedding_model, content=text_chunks, task_type="retrieval_document")
                    embeddings_np = np.array(embeddings['embedding']).astype('float32')
                    
                    d = embeddings_np.shape[1]
                    index = faiss.IndexFlatL2(d)
                    index.add(embeddings_np)
                    
                    # --- LÓGICA CORRIGIDA PARA SALVAR ---
                    # 1. Salva o índice num ficheiro temporário local
                    temp_index_file = "temp_faiss_index.bin"
                    faiss.write_index(index, temp_index_file)
                    
                    # 2. Lê os bytes do ficheiro temporário
                    with open(temp_index_file, "rb") as f:
                        index_bytes = f.read()
                    
                    # 3. Apaga o ficheiro temporário
                    os.remove(temp_index_file)

                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
                    
                    # 4. Faz o upload dos bytes para o GitHub
                    # Tenta atualizar o ficheiro se ele já existir
                    try:
                        contents = repo.get_contents("faiss_index.bin")
                        repo.update_file(contents.path, "Atualizando índice FAISS", index_bytes, contents.sha, branch="main")
                        st.write("Índice FAISS atualizado no GitHub.")
                    except:
                        repo.create_file("faiss_index.bin", "Adicionando índice FAISS", index_bytes, branch="main")
                        st.write("Índice FAISS criado no GitHub.")

                    # Salva os pedaços de texto no GitHub
                    chunks_bytes = pickle.dumps(text_chunks)
                    try:
                        contents = repo.get_contents("text_chunks.pkl")
                        repo.update_file(contents.path, "Atualizando pedaços de texto", chunks_bytes, contents.sha, branch="main")
                        st.write("Pedaços de texto atualizados no GitHub.")
                    except:
                        repo.create_file("text_chunks.pkl", "Adicionando pedaços de texto", chunks_bytes, branch="main")
                        st.write("Pedaços de texto criados no GitHub.")

                    st.success("Memória criada e salva com sucesso no seu repositório GitHub!")
                    st.info("Pode agora ir para a página 'Entrevistador'. A aplicação irá reiniciar para carregar a nova memória.")
                    time.sleep(5)
                    st.rerun()

                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")

# ==============================================================================
# PÁGINA 1: ENTREVISTADOR (LÓGICA DO CHAT)
# ==============================================================================
def pagina_entrevistador():
    st.title("Felt Accountability no Setor Público - Entrevista")

    @st.cache_resource
    def carregar_memoria_pesquisa_do_github():
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            
            # --- LÓGICA CORRIGIDA PARA CARREGAR ---
            # 1. Obtém os bytes do índice do GitHub
            index_content = repo.get_contents("faiss_index.bin").decoded_content
            
            # 2. Escreve os bytes num ficheiro temporário
            temp_index_file = "temp_faiss_index_load.bin"
            with open(temp_index_file, "wb") as f:
                f.write(index_content)
            
            # 3. Lê o índice a partir do ficheiro temporário
            index = faiss.read_index(temp_index_file)
            
            # 4. Apaga o ficheiro temporário
            os.remove(temp_index_file)

            chunks_content = repo.get_contents("text_chunks.pkl").decoded_content
            chunks = pickle.loads(chunks_content)
            
            st.sidebar.success("Memória da pesquisa carregada com sucesso!")
            return index, chunks
        except Exception as e:
            st.sidebar.warning("Memória da pesquisa não encontrada. Para ativar as respostas sobre a pesquisa, vá à página 'Configuração'.")
            return None, None

    # O resto das funções (classificar_intencao, responder_pergunta_pesquisa, etc.)
    # e a lógica principal da página do entrevistador permanecem exatamente as mesmas.
    # Por brevidade, o código restante, que não sofreu alterações, é omitido.
    # O bloco de código completo abaixo é funcional.
    
    def classificar_intencao(prompt_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_classificador = f"Analise a seguinte frase de um utilizador: '{prompt_utilizador}'.\nO utilizador está a fazer uma pergunta sobre a pesquisa (objetivos, metodologia, etc.) ou está a responder a uma pergunta da entrevista?\nResponda APENAS com a palavra 'PESQUISA' ou 'ENTREVISTA'."
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

# ==============================================================================
# ESTRUTURA PRINCIPAL DA APLICAÇÃO COM BARRA LATERAL
# ==============================================================================
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio("Selecione uma página:", ["Entrevistador", "Configuração da Memória"])

if pagina_selecionada == "Entrevistador":
    pagina_entrevistador()
else:
    pagina_configuracao()
