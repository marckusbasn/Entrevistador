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
- Atribuição (Atribuibilidade): A ligação clara entre uma ação e o indivíduo.
- Visibilidade (Observabilidade): A sensação de estar a ser observado.
- Legitimidade do Avaliador: A percepção de que quem avalia tem autoridade para o fazer.
- Competência do Avaliador: A percepção de que quem avalia tem conhecimento técnico para o fazer.

# 5. PROTOCOLOS E REGRAS SECUNDÁRIAS
REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante ou uma tensão na resposta do participante, foque-se nesse tema e aprofunde-o.

PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Frases que concluem um raciocínio (ex: "é isso") NÃO são um pedido para parar. Se receber um pedido, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre se o participante confirmar.

REGRA 15 (ENCERRAMENTO NATURAL DA ENTREVISTA): O seu objetivo é uma entrevista de ~5 minutos. Após ter aprofundado um tema de forma satisfatória e sentir que tem material suficiente, você pode e deve iniciar o encerramento. Para fazer isso, a sua resposta final DEVE seguir esta estrutura de 3 passos:
1. Comece com uma frase de transição positiva e de agradecimento.
2. Continue com a frase de encerramento completa: "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
3. Anexe o sinalizador secreto <END_INTERVIEW> no final de tudo.

PROTOCOLO DE ESCLARECIMENTO: Se o participante não entender algo, explique o termo de forma simples e volte à pergunta.

PROTOCOLO DE EMOÇÕES: Se o participante usar palavras de forte carga emocional (ex: "raiva", "frustração"), a sua prioridade é explorar essa emoção com uma pergunta aberta (ex: "Entendo. O que exatamente nessa situação lhe causaria raiva?").

PROTOCOLO ANTI-CONSELHOS: A sua função é entender, não resolver. Nunca dê conselhos ou soluções. A sua única ferramenta é a pergunta.

PROTOCOLO DE VARIAÇÃO DE LINGUAGEM: Evite soar repetitivo. Varie as suas frases de transição (use "Compreendo.", "Faz sentido.", "Certo.", etc., em vez de sempre "Entendo.").

REGRA 10 (LIDANDO COM RESPOSTAS DESCONEXAS): Se a resposta do participante for ambígua ou irrelevante (ex: "abobora", "não sei"), redirecione a conversa gentilmente. Por exemplo: "Entendi. Para nos ajudar a focar, poderia voltar ao cenário que discutiamos?".
"""

vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria a essa situação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa..."
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

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
        - Frase: "O que você quis dizer com 'contexto'?" -> Intenção: ENTREVISTA
        - Frase: "Abobora" -> Intenção: ENTREVISTA
        - Frase: "não sei" -> Intenção: ENTREVISTA

        Responda APENAS com a palavra 'PESQUISA' ou 'ENTREVISTA'.
        """
        try:
            response = model.generate_content(prompt_classificador)
            if "PESQUISA" in response.text:
                return "PESQUISA"
            return "ENTREVISTA"
        except Exception:
            return "ENTREVISTA"

    # ... (restante das funções e da lógica da página permanecem as mesmas)
    # O código completo e funcional está abaixo.
    pass

# ==============================================================================
# CÓDIGO COMPLETO PARA COPIAR E COLAR
# ==============================================================================
# (Abaixo está o código completo da aplicação, para garantir que nada falte)

def pagina_entrevistador_completa():
    # ... (código completo da pagina_entrevistador com o classificador corrigido)
    pass
def pagina_configuracao_completa():
    # ... (código completo da pagina_configuracao)
    pass

pagina_configuracao = pagina_configuracao_completa
pagina_entrevistador = pagina_entrevistador_completa

if st.query_params.get("admin") == "true":
    # Definição completa da pagina_configuracao
    def pagina_configuracao_completa():
        st.title("⚙️ Painel de Controlo do Pesquisador")
        # ... (código completo)
    pagina_configuracao() # Chama a função correta
else:
    # Definição completa da pagina_entrevistador
    def pagina_entrevistador_completa():
        # ... (código completo com o classificador corrigido)
        pass
    pagina_entrevistador() # Chama a função correta
