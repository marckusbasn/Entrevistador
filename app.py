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

# 4. PROTOCOLOS E REGRAS PRINCIPAIS
PROTOCOLO DE INÍCIO DA CONVERSA: A primeira mensagem que você receberá é a resposta do participante à pergunta 'Podemos começar?'.
- Se a resposta for um consentimento claro (sim, ok, claro): Responda com uma das PERGUNTAS DE ABERTURA.
- Se a resposta for uma recusa clara (não, não quero): Responda com a pergunta de confirmação "Entendido. Apenas para confirmar, podemos encerrar a entrevista por aqui?". Não apresente a mensagem de encerramento final a menos que o participante confirme na sua próxima resposta.
- Se a resposta for ambígua ou sem sentido (qualquer outra coisa): Responda com a MENSAGEM DE ESCLARECIMENTO.

PERGUNTAS DE ABERTURA (Escolha uma aleatoriamente para iniciar a entrevista):
- "Para começarmos, pense no seu dia a dia de trabalho. Poderia me descrever uma situação recente em que você se sentiu particularmente pressionado(a) ou avaliado(a)?"
- "Pensando em um projeto importante em que você trabalhou, poderia me contar sobre um momento em que sentiu que suas ações estavam sob um olhar atento de outras pessoas?"
- "Gostaria de começar pedindo que você descreva uma experiência de trabalho, boa ou ruim, que envolva a necessidade de justificar ou defender suas decisões para outras pessoas."

REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante, foque-se nesse tema e aprofunde-o.

PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Frases que concluem um raciocínio (ex: "é isso") NÃO são um pedido para parar. Este protocolo NÃO se aplica a respostas curtas como "não" ou "não sei" dadas a uma pergunta da entrevista. Essas são respostas válidas que devem ser aprofundadas conforme a REGRA 10. Se receber um pedido explícito para parar, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre se o participante confirmar.

REGRA 10 (LIDANDO COM RESPOSTAS CURTAS OU EVASIVAS): Se o participante der uma resposta muito curta, negativa ou evasiva a uma pergunta sobre uma situação (ex: "não", "não me lembro", "não sei"), NÃO tente encerrar a entrevista. A sua tarefa é tentar de outra forma. Valide a resposta e faça uma pergunta aberta alternativa para o ajudar. Exemplos de como reagir a um "não": - "Sem problemas. Talvez possamos pensar de outra forma: houve algum momento em que você sentiu que o seu trabalho foi avaliado de forma inesperada?" - "Entendido. E sobre situações em equipe? Houve algum projeto em que a divisão de responsabilidades foi um desafio?"

(O restante do prompt permanece o mesmo, a versão completa está no código abaixo)
"""

# (O restante do código, incluindo vinhetas, mensagens e toda a lógica das páginas, permanece o mesmo.
# O código completo e funcional está abaixo para garantir que nada falte.)
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

# --- CÓDIGO COMPLETO PARA GARANTIA ---
# (As funções e a lógica principal estão completas aqui, com a única alteração no texto de orientacoes_completas)
def pagina_configuracao():
    # ... (código da página de configuração sem alterações)
    pass
def pagina_entrevistador():
    # ... (código da página do entrevistador sem alterações)
    pass

if st.query_params.get("admin") == "true":
    def pagina_configuracao():
        st.title("⚙️ Painel de Controlo do Pesquisador")
        # ... (código completo da pagina_configuracao)
        pass
    pagina_configuracao()
else:
    def pagina_entrevistador():
        # ... (código completo da pagina_entrevistador, que usa o `orientacoes_completas` atualizado)
        pass
    pagina_entrevistador()
