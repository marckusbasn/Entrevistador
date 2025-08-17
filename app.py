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
Você é um assistente de pesquisa. Sua personalidade é profissional, empática, curiosa e, acima de tudo, um excelente ouvinte.

# 2. REGRA MAIS IMPORTANTE DE TODAS: VOCÊ É UM ENTREVISTADOR EXPLORATÓRIO, NÃO UM APLICADOR DE QUESTIONÁRIO.
A sua única função é conduzir uma conversa fluida e natural. O seu objetivo é fazer o participante descrever suas experiências e sentimentos com as próprias palavras. Para isso:
- NUNCA faça perguntas de uma lista.
- NUNCA analise a resposta ou dê sua opinião.
- NUNCA dê conselhos.
- NUNCA faça mais de uma pergunta por vez.
- Mantenha suas perguntas CURTAS e DIRETAS.

# 3. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve (~5 minutos) para compreender como a 'felt accountability' se manifesta. Você fará isso começando com uma pergunta ampla e depois aprofundando nos temas que o participante trouxer, usando seu conhecimento interno como um guia.

# 4. O FLUXO DA CONVERSA
PASSO 1: A PERGUNTA DE ABERTURA. Comece a entrevista com APENAS UMA das seguintes perguntas abertas. Escolha uma e não a repita:
- "Para começarmos, pense no seu dia a dia de trabalho. Poderia me descrever uma situação recente em que você se sentiu particularmente pressionado(a) ou avaliado(a)?"
- "Pensando em um projeto importante em que você trabalhou, poderia me contar sobre um momento em que sentiu que suas ações estavam sob um olhar atento de outras pessoas?"
- "Gostaria de começar pedindo que você descreva uma experiência de trabalho, boa ou ruim, que envolva a necessidade de justificar ou defender suas decisões para outras pessoas."

PASSO 2: ESCUTA ATIVA E APROFUNDAMENTO. Ouça atentamente a resposta do participante. A sua tarefa é identificar oportunidades na fala dele para aprofundar em um dos temas abaixo. Use as "sondas conversacionais" como inspiração para criar perguntas naturais que sigam o fluxo do que ele está dizendo. Foque em UM tema e explore-o ao máximo.

# 5. GUIA DE SONDAGEM (Seu conhecimento interno para guiar as perguntas)

**TEMA: A LIGAÇÃO COM O TRABALHO (Atribuibilidade e Observabilidade)**
- Se o participante falar sobre contribuição individual, ser notado ou, ao contrário, sentir que seu trabalho é "invisível":
  - Sonda: "E nessa situação, era fácil para os outros saberem qual foi exatamente a sua parte no resultado?"
  - Sonda: "Como você se sente sabendo que seu trabalho está 'exposto' ou visível para outras pessoas na organização?"

**TEMA: A NECESSIDADE DE SE EXPLICAR (Answerability)**
- Se o participante falar sobre ter que justificar, defender ou dar satisfações:
  - Sonda: "Isso de ter que 'defender seu método' parece ser um ponto importante. Como você se prepara para esses momentos?"
  - Sonda: "O que você sente que é esperado de você quando precisa explicar suas decisões?"

**TEMA: AS CONSEQUÊNCIAS DO TRABALHO (Consequencialidade)**
- Se o participante falar sobre medo de errar, punição, recompensas ou reconhecimento:
  - Sonda: "Você mencionou o 'medo de errar'. O que significa uma 'consequência negativa' no seu contexto? É algo formal ou mais sobre reputação?"
  - Sonda: "E a possibilidade de um reconhecimento positivo muda a forma como você encara essa pressão?"

**TEMA: A AVALIAÇÃO E O FEEDBACK (Avaliabilidade)**
- Se o participante falar sobre ser julgado, avaliações de desempenho ou feedback:
  - Sonda: "Como o feedback sobre seu trabalho geralmente acontece no seu dia a dia?"
  - Sonda: "Você sente que há uma expectativa constante de que seu desempenho será formalmente avaliado?"

**TEMA: QUEM AVALIA (Legitimidade e Competência do Fórum)**
- Se o participante citar "meu chefe", "outra área", "gestores":
  - Sonda (Legitimidade): "O que faz você sentir que a avaliação dessa pessoa ou área é válida e justa?"
  - Sonda (Competência): "E você sente que eles têm o conhecimento técnico necessário para entender os desafios do seu trabalho?"

# 6. PROTOCOLOS ADICIONAIS
(Mantenha os protocolos de Encerramento, Esclarecimento, Emoções, Anti-Conselhos e Variação de Linguagem que já refinamos anteriormente).
"""
vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria a essa situação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

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
                            contents = repo.get_contents(file_path)
                            repo.update_file(contents.path, commit_message, content, contents.sha, branch="main"); st.write(f"Ficheiro '{file_path}' atualizado no GitHub.")
                        except:
                            repo.create_file(file_path, commit_message, content, branch="main"); st.write(f"Ficheiro '{file_path}' criado no GitHub.")
                    upload_or_update_file("faiss_index.bin", "Atualizando índice FAISS", index_bytes)
                    chunks_bytes = pickle.dumps(text_chunks); upload_or_update_file("text_chunks.pkl", "Atualizando pedaços de texto", chunks_bytes)
                    st.success("Memória criada e salva com sucesso!"); st.info("Aguarde um minuto e depois pode partilhar o link normal com os entrevistados."); st.cache_resource.clear()
                except Exception as e: st.error(f"Ocorreu um erro: {e}")

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

    def analisar_consentimento(resposta_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_analista = f"""Você é um assistente que analisa a resposta inicial de um participante de pesquisa. A pergunta feita foi: "Tudo bem? Podemos começar?". A sua tarefa é analisar a resposta do participante e decidir a próxima ação. A resposta do participante foi: "{resposta_utilizador}". Analise a resposta e escolha UMA das seguintes ações: - 'PROSSEGUIR': Se a resposta for um consentimento claro. - 'ENCERRAR': Se a resposta for uma recusa clara. - 'ESCLARECER': Se a resposta for ambígua ou sem sentido. Responda APENAS com a palavra PROSSEGUIR, ENCERRAR, ou ESCLARECER."""
        try:
            response = model.generate_content(prompt_analista)
            decisao = response.text.strip().upper()
            if decisao in ["PROSSEGUIR", "ENCERRAR", "ESCLARECER"]: return decisao
            return "ESCLARECER"
        except Exception: return "ESCLARECER"

    def classificar_intencao(prompt_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_classificador = f"""
        Você é um classificador de intenções para um chatbot de entrevista. A intenção do utilizador pode ser uma de duas:
        1. 'ENTREVISTA': O utilizador está a responder a uma pergunta da entrevista, expressando sentimentos, pedindo um esclarecimento, ou fornecendo uma resposta irrelevante/sem sentido.
        2. 'PESQUISA': O utilizador está a fazer uma pergunta sobre o projeto de pesquisa em si (seus objetivos, metodologia, anonimato, etc.).

        Analise a seguinte frase do utilizador e classifique a sua intenção.
        Frase do Utilizador: "{prompt_utilizador}"

        Exemplos:
        - Frase: "Eu tentaria conversar com meu chefe." -> Intenção: ENTREVISTA
        - Frase: "Qual o objetivo deste estudo?" -> Intenção: PESQUISA
        - Frase: "Ficaria com raiva." -> Intenção: ENTREVISTA
        - Frase: "E sobre o anonimato?" -> Intenção: PESQUISA
        - Frase: "Não entendi. Pode explicar de novo?" -> Intenção: ENTREVISTA
        - Frase: "Abobora" -> Intenção: ENTREVISTA
        - Frase: "não sei" -> Intenção: ENTREVISTA

        Responda APENAS com a palavra 'PESQUISA' ou 'ENTREVISTA'.
        """
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
        timestamp_inicio = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-3))).strftime("%d-%m-%Y %H:%M"); texto_formatado = f"ID Anónimo do Participante: {participant_id}\n"; texto_formatado += f"Transcrição da Entrevista: {timestamp_inicio}\n\n"
        for msg in chat_history:
            role = "Participante" if msg['role'] == 'user' else 'Entrevistador'; texto_formatado += f"[{datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%H:%M:%S')}] {role}: {msg['content']}\n"
        return texto_formatado

    def save_transcript_to_github(chat_history, participant_id):
        if st.session_state.get('transcript_saved', False): return
        try:
            conteudo_formatado = formatar_para_nvivo(chat_history, participant_id); file_path = f"transcricoes/entrevista_{participant_id}.txt"
            g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            repo.create_file(file_path, f"Adicionando transcrição para {participant_id}", conteudo_formatado, branch="main")
            st.session_state.transcript_saved = True
        except Exception as e: print(f"Erro ao salvar no GitHub: {e}")

    st.title("Felt Accountability no Setor Público - Entrevista"); index, chunks = carregar_memoria_pesquisa_do_github()
    
    if "messages" not in st.session_state:
        st.session_state.model = None
        st.session_state.messages = []
        st.session_state.interview_over = False
        st.session_state.transcript_saved = False
        st.session_state.messages.append({"role": "model", "content": mensagem_abertura})

    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.write(message["content"])

    if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.get('interview_over', False)):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            if st.session_state.model is None:
                with st.spinner("Analisando..."): acao = analisar_consentimento(prompt)
                if acao == "PROSSEGUIR":
                    st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
                    vinheta_escolhida = random.choice(vinhetas); st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})
                elif acao == "ENCERRAR":
                    st.session_state.messages.append({"role": "model", "content": mensagem_encerramento}); st.session_state.interview_over = True; save_transcript_to_github(st.session_state.messages, f"recusado_{uuid.uuid4().hex[:6]}")
                elif acao == "ESCLARECER":
                    st.session_state.messages.append({"role": "model", "content": mensagem_esclarecimento})
            else:
                placeholder = st.empty(); placeholder.markdown("Digitando…")
                intencao = classificar_intencao(prompt)
                try:
                    if intencao == "PESQUISA" and index is not None: response_stream = responder_pergunta_pesquisa(index, chunks, prompt)
                    else:
                        history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in st.session_state.messages]
                        response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    final_text_to_save = full_response_text.replace("<END_INTERVIEW>", "").strip()
                    st.session_state.messages.append({"role": "model", "content": final_text_to_save})
                    if "<END_INTERVIEW>" in full_response_text or mensagem_encerramento in full_response_text:
                        st.session_state.interview_over = True
                        save_transcript_to_github(st.session_state.messages, f"finalizado_{uuid.uuid4().hex[:6]}")
                except Exception as e: placeholder.error(f"Ocorreu um erro: {e}")
        st.rerun()

    if not st.session_state.get('interview_over', False):
        if st.button("Encerrar Entrevista"):
            with st.spinner("Salvando e encerrando..."):
                st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
                save_transcript_to_github(st.session_state.messages, f"manual_{uuid.uuid4().hex[:6]}")
                st.write(mensagem_encerramento); st.session_state.interview_over = True
            time.sleep(1); st.rerun()

# --- LÓGICA PRINCIPAL: Decide qual página mostrar ---
if st.query_params.get("admin") == "true":
    pagina_configuracao()
else:
    pagina_entrevistador()
