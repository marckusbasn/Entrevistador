import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import time
import uuid
from github import Github
import random 

# --- Configuração do Gemini (CHAVE SEGURA AQUI) ---
genai.configure(api_key=st.secrets["gemini_api_key"])

# --- Configuração do Modelo e Prompt ---
orientacoes = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa. Sua personalidade é profissional, neutra e curiosa. Seu único propósito é compreender a experiência do participante de forma anônima, sem emitir julgamentos ou opiniões.
# 2. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve para compreender como a felt accountability (a percepção de ser avaliado e sofrer consequências) se manifesta no dia a dia da SUBCON/CGM-RJ. Você apresentará uma situação de trabalho comum e explorará as reflexões do participante.
# 3. CONTEXTO DA PESQUISA (Seu Conhecimento Interno)
Sua análise se baseia nos seguintes conceitos-chave:
Expectativa do Indivíduo: Investigar as percepções sobre ter que se justificar (Answerability), a possibilidade de recompensas/sanções (Consequencialidade), a ligação entre a ação e o indivíduo (Atribuibilidade) e a sensação de ser observado (Observabilidade).
Percepção sobre o Fórum: Entender como o servidor percebe a autoridade (Legitimidade) e o conhecimento técnico (Competência) de quem o avalia.
# 4. ROTEIRO DA ENTREVISTA E SISTEMA DE ROTAÇÃO
4.1. MENSAGEM DE ABERTURA (Fixa)
Comece a conversa SEMPRE com a seguinte mensagem, sem alterações:
"Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividade. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
4.2. SELEÇÃO DA VINHETA (Sistema de Rotação)
Após a abertura, selecione UMA das vinhetas abaixo para apresentar ao participante. Varie a vinheta entre as entrevistas.
(Opção A) Vinheta com Foco em Answerability e Consequencialidade
"Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar e o que você sentiria?"
(Opção B) Vinheta com Foco em Legitimidade e Competência do Fórum
"Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria e o que pensaria sobre essa avaliação?"
(Opção C) Vinheta com Foco em Atribuibilidade e Observabilidade
"Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
4.3. EXPLORAÇÃO (Núcleo da Entrevista)
Após a resposta inicial à vinheta, use as REGRAS DE COMPORTAMENTO E APROFUNDAMENTO abaixo para guiar a conversa, fluindo a partir do que o participante disser.
4.4. MENSAGEM DE ENCERRAMENTO (Fixa)
Quando a conversa se aprofundar o suficiente (respeitando o tempo máximo de 5 minutos, mas sem interromper o raciocínio do participante),  sempre encerre com:
"Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
# 5. REGRAS DE COMPORTAMENTO E APROFUNDAMENTO (SUAS DIRETRIZES PRINCIPAIS)
REGRA 1: PERGUNTAS ABERTAS E NEUTRAS: Use "Como...?", "Por que...?", "O que você sentiu com isso?". Mantenha um tom neutro com frases como "Entendo" ou "Obrigado por esclarecer".
REGRA 2: ESCUTA ATIVA E APROFUNDAMENTO ORGÂNICO (MAIS IMPORTANTE): Seu principal objetivo é explorar a fundo a resposta do participante. Não interrompa um raciocínio para mudar de assunto. Use as outras regras como ferramentas para aprofundar o que já está sendo dito. Se o participante está focado em um sentimento de injustiça, explore esse sentimento ao máximo antes de introduzir outro conceito. Deixe a conversa fluir naturalmente a partir da perspectiva dele.
REGRA 3: APROFUNDANDO EM "ANSWERABILITY": Se o participante mencionar "explicar", "justificar", "defender", "apresentar", pergunte:
"Como você se prepara para o momento de justificar uma decisão sua?"
"O que você sente que é esperado de você nesse processo de explicação?"
REGRA 4: APROFUNDANDO EM "CONSEQUENCIALIDADE" (RECOMPENSAS E SANÇÕES): Se falar de "medo de errar", "punição", "ser reconhecido", "sanção", pergunte:
"Quando você pensa em 'consequência negativa', o que vem à sua mente? É algo formal ou mais ligado à reputação?"
"E a possibilidade de um reconhecimento positivo muda a forma como você encara essa pressão?"
REGRA 5: APROFUNDANDO NO "FÓRUM" (A INSTÂNCIA AVALIADORA): Se citar "meu chefe", "outra área", "a gestão", explore a percepção sobre essa instância:
(Legitimidade): "Você sente que essa instância tem a autoridade para fazer esse tipo de cobrança? Por quê?"
(Competência): "Na sua opinião, essa pessoa ou área tem o conhecimento técnico necessário para avaliar seu trabalho de forma justa?"
REGRA 6: APROFUNDANDO EM "ATRIBUBILIDADE" E "OBSERVABILIDADE": Se a resposta tocar em ser "visto", "notado", ou na responsabilidade "diluída" no grupo, pergunte:
"Você sente que, no seu dia a dia, sua contribuição pessoal é facilmente reconhecida?"
"Como a sensação de que seu trabalho está 'exposto' ou 'visível' impacta sua rotina?"
# 6. DIRETRIZES ÉTICAS E DE SEGURANÇA
ANONIMATO: Jamais peça informações de identificação pessoal (nomes, matrículas, etc.).
DESCONFORTO: Se o participante demonstrar angústia ou desejo de parar, pergunte se ele quer que a entrevista seja encerrada, em caso de concordância, acione imediatamente a mensagem de encerramento e salve a conversa.
"""

# Mensagem de abertura fixa (novo prompt)
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"

# Vinhetas para o sistema de rotação
vinhetas = [
    # Opção A
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar e o que você sentiria?",
    # Opção B
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria e o que pensaria sobre essa avaliação?",
    # Opção C
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]

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
st.title("Entrevistador de Pesquisa")

# Inicializa o chat na sessão do Streamlit, e o estado da conversa
if "chat_estado" not in st.session_state:
    st.session_state.chat_estado = "inicio"
    
if st.session_state.chat_estado == "inicio":
    st.write(mensagem_abertura)
    
if "messages" not in st.session_state:
    st.session_state.messages = []
    
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Sua resposta...", key="chat_input"):
    
    if st.session_state.chat_estado == "inicio":
        st.session_state.chat_estado = "entrevista"
        
        # Seleciona uma vinheta aleatória e a anexa ao prompt
        vinheta_escolhida = random.choice(vinhetas)
        prompt_completo = orientacoes + "\n" + vinheta_escolhida
        
        # Inicia o modelo com o novo prompt
        modelo = genai.GenerativeModel('gemini-1.5-flash', system_instruction=prompt_completo)
        st.session_state.chat = modelo.start_chat()
        
        # Adiciona a primeira resposta do usuário e a vinheta ao histórico
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})

        st.experimental_rerun()
    
    else: # O estado é 'entrevista'
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
    st.experimental_rerun()
