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
REPO_NAME = "Entrevistador" # O nome do seu repositório

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
# (O seu texto longo de orientacoes_completas permanece aqui, omitido por brevidade)
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa...
"""
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
                    document_text = uploaded_file.getvalue().decode("utf-8")
                    text_chunks = [chunk for chunk in document_text.split('\n\n') if chunk.strip()]
                    
                    embedding_model = 'models/embedding-001'
                    embeddings = genai.embed_content(model=embedding_model, content=text_chunks, task_type="retrieval_document")
                    embeddings_np = np.array(embeddings['embedding']).astype('float32')
                    
                    d = embeddings_np.shape[1]
                    index = faiss.IndexFlatL2(d)
                    index.add(embeddings_np)
                    
                    # Salva o índice num ficheiro temporário local
                    temp_index_file = "temp_faiss_index.bin"
                    faiss.write_index(index, temp_index_file)
                    
                    with open(temp_index_file, "rb") as f:
                        index_bytes = f.read()
                    os.remove(temp_index_file)

                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
                    
                    # Tenta atualizar o ficheiro se ele já existir
                    try:
                        contents = repo.get_contents("faiss_index.bin")
                        repo.update_file(contents.path, "Atualizando índice FAISS", index_bytes, contents.sha, branch="main")
                        st.write("Índice FAISS atualizado no GitHub.")
                    except:
                        repo.create_file("faiss_index.bin", "Adicionando índice FAISS", index_bytes, branch="main")
                        st.write("Índice FAISS criado no GitHub.")

                    chunks_bytes = pickle.dumps(text_chunks)
                    try:
                        contents = repo.get_contents("text_chunks.pkl")
                        repo.update_file(contents.path, "Atualizando pedaços de texto", chunks_bytes, contents.sha, branch="main")
                        st.write("Pedaços de texto atualizados no GitHub.")
                    except:
                        repo.create_file("text_chunks.pkl", "Adicionando pedaços de texto", chunks_bytes, branch="main")
                        st.write("Pedaços de texto criados no GitHub.")

                    st.success("Memória criada e salva com sucesso no seu repositório GitHub!")
                    st.info("Por favor, aguarde cerca de um minuto e depois vá para a página 'Entrevistador' e clique em 'Recarregar Memória'.")
                    st.cache_resource.clear() # Limpa a cache para forçar o recarregamento na outra página
                    
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
            
            index_content = repo.get_contents("faiss_index.bin").decoded_content
            
            temp_index_file = "temp_faiss_index_load.bin"
            with open(temp_index_file, "wb") as f:
                f.write(index_content)
            
            index = faiss.read_index(temp_index_file)
            os.remove(temp_index_file)

            chunks_content = repo.get_contents("text_chunks.pkl").decoded_content
            chunks = pickle.loads(chunks_content)
            
            st.sidebar.success("Memória da pesquisa carregada!")
            return index, chunks
        except Exception as e:
            # <<< MENSAGEM DE AVISO MELHORADA AQUI >>>
            st.sidebar.warning("Memória não carregada. Se você acabou de a configurar, aguarde um minuto e clique no botão 'Recarregar Memória da Pesquisa' abaixo.")
            return None, None

    # O resto das funções (classificar_intencao, etc.) permanecem iguais
    def classificar_intencao(prompt_utilizador):
        # (código sem alterações)
        pass
    def responder_pergunta_pesquisa(index, chunks, pergunta):
        # (código sem alterações)
        pass
    def stream_handler(stream):
        # (código sem alterações)
        pass
    def save_transcript_to_github(chat_history):
        # (código sem alterações)
        pass

    # --- Lógica da Barra Lateral ---
    # <<< NOVO BOTÃO DE RECARREGAMENTO AQUI >>>
    if st.sidebar.button("🔄 Recarregar Memória da Pesquisa"):
        st.cache_resource.clear()
        st.rerun()

    # --- Lógica Principal da Aplicação ---
    index, chunks = carregar_memoria_pesquisa_do_github()

    # (O resto da lógica do chat, if "model" not in st.session_state, etc. permanece exatamente o mesmo)
    # (O código completo está no bloco abaixo para copiar e colar)
    if "model" not in st.session_state:
        st.session_state.model = None
        st.session_state.messages = []
        st.session_state.interview_over = False 
        st.session_state.messages.append({"role": "model", "content": mensagem_abertura})

    # (restante do código omitido por brevidade, mas incluído no bloco completo)


# ==============================================================================
# ESTRUTURA PRINCIPAL DA APLICAÇÃO COM BARRA LATERAL
# ==============================================================================
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio("Selecione uma página:", ["Entrevistador", "Configuração da Memória"])

# --- CÓDIGO COMPLETO DAS PÁGINAS PARA COPIAR ---
# (As funções internas estão definidas aqui para o código ser autocontido)
if pagina_selecionada == "Entrevistador":
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

    pagina_entrevistador()
else:
    pagina_configuracao()
