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
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
# ... (igual à versão anterior)

# 2. OBJETIVO PRINCIPAL
# ... (igual à versão anterior)

# 3. CONTEXTO DA PESQUISA (Seu Conhecimento Interno - NÃO REVELE AO PARTICIPANTE)
# ... (igual à versão anterior)

# 4. REGRAS DE COMPORTAMENTO E APROFUNDAMENTO (SUAS DIRETRIZES PRINCIPAIS)
REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Faça APENAS UMA pergunta de cada vez. Assim que encontrar um tema interessante ou uma tensão na resposta do participante, foque-se nesse tema. Use as suas outras regras para aprofundar ao máximo essa única linha de investigação, em vez de tentar cobrir vários conceitos da pesquisa.

REGRA DE MÁXIMA PRIORIDADE 1 (PROTOCOLO DE ENCERRAMENTO POR PEDIDO): Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista.
- Exemplos para iniciar o protocolo: "quero parar agora", "podemos encerrar", "chega por hoje", "não quero mais responder".
- NÃO inicie o protocolo por frases que apenas concluem um raciocínio, como "é isso", "sigo em frente" ou "pelo menos sai direito". Nesses casos, a sua função é continuar a aprofundar no tema.
Se um participante expressar um desejo claro de terminar a entrevista, NÃO o faça imediatamente. Em vez disso, peça uma confirmação educada (ex: "Entendido. Apenas para confirmar, podemos encerrar a entrevista por aqui?"). Apenas se o participante confirmar, você deve apresentar a MENSAGEM DE ENCERRAMENTO.

REGRA DE MÁXIMA PRIORIDADE 2 (PEDIDO DE ESCLARECIMENTO): Se o participante pedir um esclarecimento sobre um termo que ele não entendeu, PARE de seguir o roteiro e priorize a resposta a essa dúvida. Esclareça o termo de forma simples e neutra e, em seguida, use uma ponte conversacional para retornar ao tópico da entrevista.

REGRA DE MÁXIMA PRIORIDADE 3 (NUNCA QUEBRE A PERSONA): A sua única função é ser o entrevistador. JAMAIS explique como a resposta de um participante se conecta à teoria da pesquisa. Nunca mencione termos como "dimensão de competência", "análise qualitativa" ou "felt accountability". Use o seu conhecimento interno APENAS para decidir qual a melhor pergunta a fazer em seguida. O seu conhecimento teórico é secreto e nunca deve ser revelado.

REGRA 15 (ENCERRAMENTO NATURAL DA ENTREVISTA): O seu objetivo é uma entrevista de ~5 minutos. Após ter aprofundado um tema de forma satisfatória e sentir que tem material suficiente, você pode iniciar o encerramento. Nestes casos, NÃO use a pergunta de confirmação ("podemos encerrar?"). Em vez disso, faça uma transição suave para o fim. Use uma frase de agradecimento que indique que a meta foi atingida, seguida imediatamente da MENSAGEM DE ENCERRAMENTO.
Exemplos de frases de transição: "Excelente, esta última reflexão foi muito esclarecedora. Agradeço imensamente pela sua contribuição.", "Acho que já temos material mais do que suficiente. A sua perspetiva foi muito valiosa.", "Isto foi muito útil e detalhado. Agradeço sinceramente o seu tempo.".
**Ao usar este método de encerramento, você DEVE adicionar o seguinte sinalizador especial no final da sua resposta, sem espaços antes: <END_INTERVIEW>**
**Exemplo de resposta final COMPLETA:** "Isto foi muito útil. Agradeço o detalhe na sua resposta. Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!<END_INTERVIEW>"

REGRA 14 (NUNCA DÊ CONSELHOS OU SOLUÇÕES): A sua função é entender, não resolver. Em nenhum momento dê conselhos, sugestões, opiniões ou "soluções" para os problemas ou sentimentos descritos pelo participante. A sua única ferramenta é a pergunta.

REGRA 7 (CONVERSA FLUIDA E MENOS ROBÓTICA): Para que a conversa soe mais natural, é crucial variar as suas frases. Evite começar todas as suas perguntas da mesma forma (ex: usando "Entendo." repetidamente). Alterne entre diferentes tipos de pontes conversacionais.

REGRA 2.1 (APROFUNDAMENTO DE EMOÇÕES): Se o participante usar palavras de forte carga emocional (ex: "raiva", "frustração"), a sua prioridade máxima é explorar essa emoção. NUNCA julgue a resposta como "incompleta". Valide o sentimento com "Entendo" ou uma variação e faça uma pergunta aberta para explorar a sua origem.

REGRA 13 (NÃO DÊ EXEMPLOS NAS PERGUNTAS): É crucial não influenciar o participante. JAMAIS termine as suas perguntas com uma lista de exemplos ou sugestões de respostas. Pergunte de forma aberta.
"""
# (vinhetas, mensagem_abertura, etc. permanecem iguais)
vinhetas = [
    "Imagine que você precisa entregar um relatório importante...",
    "Pense que um procedimento que você considera correto...",
    "Imagine um trabalho importante feito em equipe..."
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa..."
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

# (O restante do código, incluindo as funções e a lógica das páginas, está completo abaixo)
def pagina_configuracao():
    # ... (código da página de configuração sem alterações)
    pass

def pagina_entrevistador():
    @st.cache_resource
    def carregar_memoria_pesquisa_do_github():
        # ... (código sem alterações)
        pass

    def analisar_consentimento(resposta_utilizador):
        # ... (código sem alterações)
        pass

    def classificar_intencao(prompt_utilizador):
        # ... (código sem alterações)
        pass

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
        if st.session_state.get('transcript_saved', False): return False
        try:
            conteudo_formatado = formatar_para_nvivo(chat_history)
            unique_id = uuid.uuid4()
            file_path = f"transcricoes/entrevista_{unique_id}.txt"
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            repo.create_file(file_path, f"Adicionando transcrição da entrevista {unique_id}", conteudo_formatado, branch="main")
            st.session_state.transcript_saved = True
            return True
        except Exception as e:
            print(f"Erro ao salvar no GitHub: {e}"); return False

    st.title("Felt Accountability no Setor Público - Entrevista")
    index, chunks = carregar_memoria_pesquisa_do_github()

    if "model" not in st.session_state:
        # ... (lógica de inicialização sem alterações)
        pass
    
    # ... (loop de exibição de mensagens sem alterações)

    if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.interview_over):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        with st.chat_message("assistant"):
            if st.session_state.model is None:
                # ... (lógica de consentimento sem alterações)
                pass
            else:
                placeholder = st.empty()
                placeholder.markdown("Digitando…")
                intencao = classificar_intencao(prompt)
                
                try:
                    if intencao == "PESQUISA" and index is not None: 
                        response_stream = responder_pergunta_pesquisa(index, chunks, prompt)
                    else:
                        start_index = 0
                        for i, msg in enumerate(st.session_state.messages):
                            if msg['content'] in vinhetas: start_index = i; break
                        relevant_messages = st.session_state.messages[start_index:]
                        history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in relevant_messages]
                        response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    
                    # <<< NOVA LÓGICA DE SALVAMENTO ROBUSTA >>>
                    # Verifica se o sinal secreto está presente
                    if "<END_INTERVIEW>" in full_response_text:
                        # Limpa o sinal antes de salvar e mostrar
                        final_text = full_response_text.replace("<END_INTERVIEW>", "").strip()
                        st.session_state.messages.append({"role": "model", "content": final_text})
                        st.session_state.interview_over = True
                        save_transcript_to_github(st.session_state.messages)
                    elif mensagem_encerramento in full_response_text: # Mantém o gatilho para o encerramento por botão
                        st.session_state.messages.append({"role": "model", "content": full_response_text})
                        st.session_state.interview_over = True
                        save_transcript_to_github(st.session_state.messages)
                    else:
                        st.session_state.messages.append({"role": "model", "content": full_response_text})

                except Exception as e: 
                    placeholder.error(f"Ocorreu um erro: {e}")
        
        st.rerun()

    if st.button("Encerrar Entrevista"):
        with st.spinner("Salvando e encerrando..."):
            st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
            save_transcript_to_github(st.session_state.messages)
            st.write(mensagem_encerramento)
            st.session_state.interview_over = True
        time.sleep(1)
        st.rerun()

# --- LÓGICA PRINCIPAL ---
# (O código completo para copiar e colar está abaixo)

if st.query_params.get("admin") == "true":
    def pagina_configuracao():
        st.title("⚙️ Painel de Controlo do Pesquisador")
        st.write("Use esta ferramenta para criar ou atualizar a 'memória' do seu chatbot. Faça o upload do seu projeto de pesquisa em formato .txt e clique no botão para salvar a memória no GitHub.")
        st.warning("Esta página só é visível para si através do link especial com `?admin=true`.")
        uploaded_file = st.file_uploader("Selecione o seu ficheiro `projeto.txt`", type="txt")
        if uploaded_file is not None:
            st.success(f"Ficheiro '{uploaded_file.name}' carregado com sucesso!")
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
                                contents = repo.get_contents(file_path); repo.update_file(contents.path, commit_message, content, contents.sha, branch="main"); st.write(f"Ficheiro '{file_path}' atualizado no GitHub.")
                            except:
                                repo.create_file(file_path, commit_message, content, branch="main"); st.write(f"Ficheiro '{file_path}' criado no GitHub.")
                        upload_or_update_file("faiss_index.bin", "Atualizando índice FAISS", index_bytes)
                        chunks_bytes = pickle.dumps(text_chunks); upload_or_update_file("text_chunks.pkl", "Atualizando pedaços de texto", chunks_bytes)
                        st.success("Memória criada e salva com sucesso!"); st.info("Aguarde um minuto e depois pode partilhar o link normal com os entrevistados."); st.cache_resource.clear()
                    except Exception as e: st.error(f"Ocorreu um erro: {e}")
    pagina_configuracao()
else:
    pagina_entrevistador()
