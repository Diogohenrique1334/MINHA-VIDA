import uvicorn
import requests
import json
import datetime
from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import func
import traceback
from dotenv import load_dotenv
import os
import pytz

load_dotenv()

API_VERSION = os.getenv("API_VERSION")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

from backend.models import Minha_vida
from backend.dependencies import pegar_sessao
import backend.habitos_repo as habitos_repo
from backend.habitos_repo import CATEGORIAS

app = FastAPI()

FUSO_BRASIL = pytz.timezone('America/Sao_Paulo')

def agora_brasil():
    return datetime.datetime.now(FUSO_BRASIL)

def data_hoje_brasil():
    return agora_brasil().date()

def data_ontem_brasil():
    return data_hoje_brasil() - datetime.timedelta(days=1)

DIAS_SEMANA_PT = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']

def resolver_data(token):
    """Resolve o token de dia que trafega nos payloads em um datetime.date.

    Aceita as datas em formato ISO (AAAA-MM-DD) e mantém compatibilidade com
    os tokens antigos 'hoje'/'ontem' para conversas iniciadas antes do deploy.
    """
    if token == 'hoje':
        return data_hoje_brasil()
    if token == 'ontem':
        return data_ontem_brasil()
    return datetime.date.fromisoformat(token)

def rotulo_dia(data):
    """Rótulo amigável para um datetime.date: 'hoje', 'ontem' ou 'em 05/06 (qua)'."""
    if data == data_hoje_brasil():
        return 'hoje'
    if data == data_ontem_brasil():
        return 'ontem'
    return f"em {data.strftime('%d/%m')} ({DIAS_SEMANA_PT[data.weekday()]})"

def parse_data_usuario(texto):
    """Converte uma data digitada pelo usuário em datetime.date, ou None se inválida.

    Aceita 05/06, 5/6, 05/06/2025, 05/06/25, 05-06. Ano omitido assume o ano atual.
    """
    texto = texto.strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%d/%m', '%d-%m-%Y', '%d-%m'):
        try:
            data = datetime.datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
        if fmt in ('%d/%m', '%d-%m'):
            data = data.replace(year=data_hoje_brasil().year)
        return data
    return None

def send_whatsapp_message(recipient_id, message_text):
    print(f"Tentando enviar '{message_text}' para {recipient_id}")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": recipient_id, "type": "text", "text": {"body": message_text}}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO AO ENVIAR MENSAGEM: {e.response.text if e.response else e} ---")

def send_button_message(recipient_id, question_text, buttons):
    print(f"Tentando enviar pergunta com botões para {recipient_id}")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    action_buttons = [{"type": "reply", "reply": {"id": b["payload"], "title": b["title"]}} for b in buttons]
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": question_text},
            "action": {"buttons": action_buttons}
        }
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO AO ENVIAR BOTÕES: {e.response.text if e.response else e} ---")

def send_list_message(recipient_id, header_text, body_text, button_text, sections):
    print(f"Tentando enviar lista para {recipient_id}")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header_text[:60]},
            "body": {"text": body_text[:1024]},
            "action": {"button": button_text[:20], "sections": sections}
        }
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status: {response.status_code}, Resposta: {response.text}")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO AO ENVIAR LISTA: {e.response.text if e.response else e} ---")

TOPICOS_TEXTO = {
    'nota_humor_inicio': {'coluna': 'nota_humor', 'texto': 'Qual sua nota de humor ao acordar {dia}? (de 0 a 10)', 'tipo': 'nota', 'titulo': 'Humor Início'},
    'hora_acordei': {'coluna': 'data_hora_acordei', 'texto': 'Beleza. E que horas você acordou {dia}? (ex: 07:30)', 'tipo': 'hora', 'titulo': 'Hora Acordar'},
    'hora_dormir': {'coluna': 'data_hora_dormi', 'texto': 'Entendido. E que horas você foi dormir na noite anterior? (ex: 23:30)', 'tipo': 'hora_anterior', 'titulo': 'Hora Dormir'},
    'nota_humor_fim': {'coluna': 'Nota_humor_fim_dia', 'texto': 'Para finalizar, qual sua nota de humor ao ir dormir {dia}? (de 0 a 10)', 'tipo': 'nota', 'titulo': 'Humor Fim'}
}

# Colunas de métrica (humor/sono) — continuam fixas na tabela minha_vida.
COLUNAS_METRICAS = [v['coluna'] for v in TOPICOS_TEXTO.values()]

def dia_tem_metrica(registro):
    """True se o dia tem ao menos uma métrica (humor/sono) preenchida."""
    return registro is not None and any(
        getattr(registro, coluna) is not None for coluna in COLUNAS_METRICAS
    )

def dia_tem_registro(session, sender_phone, data):
    """True se o dia tem ao menos um hábito lançado ou uma métrica preenchida."""
    registro = buscar_registro(session, data, sender_phone)
    if dia_tem_metrica(registro):
        return True
    return habitos_repo.habitos_lancados_no_dia(session, sender_phone, data) > 0

def send_seletor_de_dia(sender_phone, session, qtd_dias=8):
    """Lista os últimos dias com status (✅ tem algo / ⬜️ vazio) + opção de digitar outra data."""
    hoje = data_hoje_brasil()
    rows = []
    for i in range(qtd_dias):
        dia = hoje - datetime.timedelta(days=i)
        tem_registro = dia_tem_registro(session, sender_phone, dia)
        emoji = "✅" if tem_registro else "⬜️"
        title = f"{emoji} {dia.strftime('%d/%m')} ({DIAS_SEMANA_PT[dia.weekday()]})"
        if i == 0:
            description = "hoje"
        elif i == 1:
            description = "ontem"
        else:
            description = "registrado" if tem_registro else "vazio"
        rows.append({"id": f"escolher_dia_{dia.isoformat()}", "title": title[:24], "description": description[:72]})
    rows.append({"id": "escolher_outra_data", "title": "📅 Outra data"})
    sections = [{"title": "Últimos dias", "rows": rows}]
    send_list_message(sender_phone, "Diário", "Para qual dia você gostaria de registrar?", "Escolher dia", sections)

def send_dynamic_menu(sender_phone, session, registro, category, dia="hoje"):
    """Roteia para o checklist de hábitos (dinâmico) ou o menu de métricas (fixo)."""
    if category == 'habitos':
        send_menu_habitos(sender_phone, session, dia)
        return
    send_menu_metricas(sender_phone, registro, dia)

def send_menu_habitos(sender_phone, session, dia="hoje"):
    """Checklist dos hábitos ativos do dia, montado dinamicamente do banco."""
    habitos_repo.garantir_habitos_padrao(session, sender_phone)
    data_ref = resolver_data(dia)
    dia_texto = rotulo_dia(data_ref)
    habitos = habitos_repo.listar_habitos_ativos(session, sender_phone)
    rows = []
    # Lista do WhatsApp tem no máx. 10 linhas: até 9 hábitos + "Voltar".
    for h in habitos[:9]:
        reg = habitos_repo.buscar_registro_habito(session, h.id, data_ref)
        if reg is None:
            status_emoji, description = "⬜️", "Pendente"
        else:
            status_emoji = "✅" if reg.valor else "❌"
            description = "Sim" if reg.valor else "Não"
        prefixo = f"{h.emoji} " if h.emoji else ""
        row_title = f"{status_emoji} {prefixo}{h.nome}"
        rows.append({"id": f"ask_h{h.id}_{dia}", "title": row_title[:24], "description": description[:72]})
    rows.append({"id": f"show_menu_principal_{dia}", "title": "⬅️ Voltar"})
    sections = [{"title": dia_texto.capitalize()[:24], "rows": rows}]
    send_list_message(sender_phone, f"Hábitos - {dia_texto.capitalize()}", "Toque para marcar/desmarcar", "Hábitos", sections)

def send_menu_metricas(sender_phone, registro, dia="hoje"):
    """Menu de métricas (humor/sono) — colunas fixas em minha_vida."""
    dia_texto = rotulo_dia(resolver_data(dia))
    rows = []
    for key, value in TOPICOS_TEXTO.items():
        resposta = getattr(registro, value['coluna'], None)
        if resposta is None:
            status_emoji = "⬜️"
            description = "Pendente"
        else:
            status_emoji = "⏰" if 'hora' in key else "📊"
            if isinstance(resposta, datetime.datetime):
                description = f"Resposta: {resposta.astimezone(FUSO_BRASIL).strftime('%H:%M')}"
            else:
                description = f"Resposta: {resposta}"
        row_title = f"{status_emoji} {value['titulo']}"
        rows.append({"id": f"ask_{key}_{dia}", "title": row_title[:24], "description": description[:72]})
    rows.append({"id": f"show_menu_principal_{dia}", "title": "⬅️ Voltar"})
    sections = [{"title": dia_texto.capitalize()[:24], "rows": rows}]
    send_list_message(sender_phone, f"Métricas - {dia_texto.capitalize()}", "Métricas", "Opções", sections)

def send_gerenciar_menu(sender_phone, dia="hoje"):
    """Submenu de gestão de hábitos: criar novo ou congelar/reativar."""
    botoes = [
        {"title": "➕ Novo hábito", "payload": f"novo_habito_{dia}"},
        {"title": "❄️ Congelar", "payload": f"congelar_habitos_{dia}"},
        {"title": "⬅️ Voltar", "payload": f"escolher_dia_{dia}"},
    ]
    send_button_message(sender_phone, "Gerenciar hábitos — o que você quer fazer?", botoes)

def send_menu_congelar(sender_phone, session, dia="hoje"):
    """Lista todos os hábitos (ativos e congelados); tocar alterna o estado."""
    habitos = habitos_repo.listar_habitos(session, sender_phone)
    rows = []
    for h in habitos[:9]:
        status_emoji = "✅" if h.ativo else "❄️"
        description = "Ativo" if h.ativo else "Congelado"
        prefixo = f"{h.emoji} " if h.emoji else ""
        row_title = f"{status_emoji} {prefixo}{h.nome}"
        rows.append({"id": f"toggle_habito_{h.id}_{dia}", "title": row_title[:24], "description": description[:72]})
    rows.append({"id": f"gerenciar_habitos_{dia}", "title": "⬅️ Voltar"})
    sections = [{"title": "Ativar/Congelar", "rows": rows}]
    send_list_message(sender_phone, "Congelar hábitos", "Toque para ativar ou congelar", "Hábitos", sections)

def send_seletor_categoria(sender_phone, nome):
    """Lista as 4 hipercategorias para o hábito novo sendo criado."""
    rows = [{"id": f"catnova_{i}", "title": cat[:24]} for i, cat in enumerate(CATEGORIAS)]
    sections = [{"title": "Categorias", "rows": rows}]
    send_list_message(sender_phone, "Nova categoria", f"Em qual categoria entra '{nome}'?", "Categoria", sections)

def limpar_status_conversa(session, sender_phone):
    """Zera o status_conversa de todos os registros do usuário.

    Garante uma única conversa ativa por vez: como o status é guardado por dia,
    sem isso vários dias podem ficar pendentes e o handler de texto (que busca por
    data desc) acabaria gravando a resposta no dia errado.
    """
    pendentes = session.query(Minha_vida).filter(
        Minha_vida.user_phone_number == sender_phone,
        Minha_vida.status_conversa.isnot(None)
    ).all()
    for registro in pendentes:
        registro.status_conversa = None

def buscar_registro(session, data, sender_phone):
    """Busca (sem criar) o registro de um dia para um usuário. Retorna None se não existir."""
    return session.query(Minha_vida).filter(
        func.date(func.timezone('America/Sao_Paulo', Minha_vida.data)) == data,
        Minha_vida.user_phone_number == sender_phone
    ).first()

def get_registro_por_data(session, data, sender_phone):
    """Busca o registro do dia; cria uma linha vazia se ainda não existir."""
    registro = buscar_registro(session, data, sender_phone)
    if not registro:
        data_inicio = FUSO_BRASIL.localize(datetime.datetime.combine(data, datetime.time(0, 0)))
        novo_registro = Minha_vida(data=data_inicio, user_phone_number=sender_phone)
        session.add(novo_registro)
        session.commit()
        registro = buscar_registro(session, data, sender_phone)
    return registro

@app.get("/")
def root(): return {"status": "API online"}

@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK VERIFICADO!")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token inválido")

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    print(f"\n--- Webhook Recebido ---\n{json.dumps(data, indent=2)}\n-----------------------\n")
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            message_info = value["messages"][0]
            sender_phone = message_info["from"]
            with pegar_sessao() as session:
                if message_info["type"] == "text" and message_info["text"]["body"].lower().strip() in ["iniciar", "oi", "diario", "menu"]:
                    send_seletor_de_dia(sender_phone, session)
                    return {"status": "ok"}

                elif message_info["type"] == "interactive":
                    interactive_type = message_info["interactive"]["type"]
                    payload = message_info["interactive"][interactive_type]["id"]

                    if payload == 'escolher_outra_data':
                        registro = get_registro_por_data(session, data_hoje_brasil(), sender_phone)
                        limpar_status_conversa(session, sender_phone)
                        registro.status_conversa = "aguardando_data_livre"
                        session.commit()
                        send_whatsapp_message(sender_phone, "Digite a data que você quer registrar (ex: 05/06 ou 05/06/2025):")
                        return {"status": "ok"}

                    if payload.startswith('escolher_dia_'):
                        dia_escolhido = payload.replace('escolher_dia_', '')
                        data_referencia = resolver_data(dia_escolhido)
                        registro = get_registro_por_data(session, data_referencia, sender_phone)
                        texto = f"Você selecionou {rotulo_dia(data_referencia)}. O que você gostaria de fazer?"
                        botoes = [
                            {"title": "💪 Hábitos", "payload": f"show_menu_habitos_{dia_escolhido}"},
                            {"title": "📊 Métricas", "payload": f"show_menu_metricas_{dia_escolhido}"},
                            {"title": "⚙️ Gerenciar", "payload": f"gerenciar_habitos_{dia_escolhido}"}
                        ]
                        send_button_message(sender_phone, texto, botoes)
                        return {"status": "ok"}

                    if payload.startswith('show_menu_'):
                        parts = payload.split('_')
                        category = parts[2] if len(parts) > 2 else 'principal'
                        dia_escolhido = parts[3] if len(parts) > 3 else 'hoje'
                        data_referencia = resolver_data(dia_escolhido)
                        registro = get_registro_por_data(session, data_referencia, sender_phone)
                        if category == 'principal':
                            send_seletor_de_dia(sender_phone, session)
                        else:
                            send_dynamic_menu(sender_phone, session, registro, category, dia_escolhido)
                        return {"status": "ok"}

                    if payload.startswith('gerenciar_habitos_'):
                        dia_escolhido = payload[len('gerenciar_habitos_'):]
                        send_gerenciar_menu(sender_phone, dia_escolhido)
                        return {"status": "ok"}

                    if payload.startswith('congelar_habitos_'):
                        dia_escolhido = payload[len('congelar_habitos_'):]
                        send_menu_congelar(sender_phone, session, dia_escolhido)
                        return {"status": "ok"}

                    if payload.startswith('toggle_habito_'):
                        rest = payload[len('toggle_habito_'):]
                        habito_id_str, dia_escolhido = rest.rsplit('_', 1)
                        habito = habitos_repo.buscar_habito(session, int(habito_id_str))
                        if habito is not None:
                            novo_ativo = not habito.ativo
                            habitos_repo.set_ativo(session, habito.id, novo_ativo)
                            estado = "reativado" if novo_ativo else "congelado"
                            send_whatsapp_message(sender_phone, f"{'✅' if novo_ativo else '❄️'} '{habito.nome}' {estado}!")
                        send_menu_congelar(sender_phone, session, dia_escolhido)
                        return {"status": "ok"}

                    if payload.startswith('novo_habito_'):
                        dia_escolhido = payload[len('novo_habito_'):]
                        registro = get_registro_por_data(session, data_hoje_brasil(), sender_phone)
                        limpar_status_conversa(session, sender_phone)
                        registro.status_conversa = f"novohabito_nome:{dia_escolhido}"
                        session.commit()
                        send_whatsapp_message(sender_phone, "Qual o nome do novo hábito? (ex: Meditar, Beber chá...)")
                        return {"status": "ok"}

                    if payload.startswith('catnova_'):
                        idx = int(payload[len('catnova_'):])
                        registro = session.query(Minha_vida).filter(
                            Minha_vida.user_phone_number == sender_phone,
                            Minha_vida.status_conversa.like('novohabito_cat:%')
                        ).order_by(Minha_vida.data.desc()).first()
                        if registro and 0 <= idx < len(CATEGORIAS):
                            _, dia_escolhido, nome = registro.status_conversa.split(':', 2)
                            categoria = CATEGORIAS[idx]
                            habito, criado = habitos_repo.criar_habito(session, sender_phone, nome, categoria)
                            registro.status_conversa = None
                            session.commit()
                            msg = (f"✅ Hábito '{habito.nome}' criado em {categoria}!" if criado
                                   else f"♻️ '{habito.nome}' já existia e foi reativado!")
                            send_whatsapp_message(sender_phone, msg)
                            send_menu_habitos(sender_phone, session, dia_escolhido)
                        return {"status": "ok"}

                    if payload.startswith('ask_'):
                        rest = payload[len('ask_'):]
                        try:
                            topic_key, dia_escolhido = rest.rsplit('_', 1)
                        except ValueError:
                            topic_key = rest
                            dia_escolhido = 'hoje'
                        data_referencia = resolver_data(dia_escolhido)
                        if topic_key.startswith('h') and topic_key[1:].isdigit():
                            habito_id = int(topic_key[1:])
                            novo_valor = habitos_repo.alternar_valor(session, habito_id, data_referencia)
                            habito = habitos_repo.buscar_habito(session, habito_id)
                            nome = habito.nome if habito else "Hábito"
                            acao = "marcado como feito ✅" if novo_valor else "marcado como não feito ❌"
                            send_whatsapp_message(sender_phone, f"'{nome}' {acao}")
                            send_menu_habitos(sender_phone, session, dia_escolhido)
                        elif topic_key in TOPICOS_TEXTO:
                            topic_info = TOPICOS_TEXTO[topic_key]
                            registro = get_registro_por_data(session, data_referencia, sender_phone)
                            texto_pergunta = topic_info['texto'].format(dia=rotulo_dia(data_referencia))
                            limpar_status_conversa(session, sender_phone)
                            registro.status_conversa = f"aguardando_{topic_key}_{dia_escolhido}"
                            session.commit()
                            send_whatsapp_message(sender_phone, texto_pergunta)
                        return {"status": "ok"}

                elif message_info["type"] == "text":
                    registro = session.query(Minha_vida).filter(
                        Minha_vida.user_phone_number == sender_phone,
                        Minha_vida.status_conversa.isnot(None)
                    ).order_by(Minha_vida.data.desc()).first()
                    if registro and registro.status_conversa:
                        texto_usuario = message_info["text"]["body"]
                        status = registro.status_conversa
                        if status == "aguardando_data_livre":
                            registro.status_conversa = None
                            session.commit()
                            data_alvo = parse_data_usuario(texto_usuario)
                            if data_alvo is None:
                                send_whatsapp_message(sender_phone, "Não entendi a data. Tente no formato 05/06 ou 05/06/2025.")
                                return {"status": "ok"}
                            if data_alvo > data_hoje_brasil():
                                send_whatsapp_message(sender_phone, "Essa data ainda não chegou. 😅 Escolha hoje ou um dia passado.")
                                return {"status": "ok"}
                            get_registro_por_data(session, data_alvo, sender_phone)
                            dia_iso = data_alvo.isoformat()
                            texto = f"Você selecionou {rotulo_dia(data_alvo)}. O que você gostaria de fazer?"
                            botoes = [
                                {"title": "💪 Hábitos", "payload": f"show_menu_habitos_{dia_iso}"},
                                {"title": "📊 Métricas", "payload": f"show_menu_metricas_{dia_iso}"},
                                {"title": "⚙️ Gerenciar", "payload": f"gerenciar_habitos_{dia_iso}"}
                            ]
                            send_button_message(sender_phone, texto, botoes)
                            return {"status": "ok"}
                        if status.startswith("novohabito_nome:"):
                            dia_escolhido = status.split(':', 1)[1]
                            nome = texto_usuario.strip()
                            if not nome or len(nome) > 40:
                                send_whatsapp_message(sender_phone, "Nome inválido. Envie um nome curto (até 40 caracteres).")
                                return {"status": "ok"}
                            registro.status_conversa = f"novohabito_cat:{dia_escolhido}:{nome}"
                            session.commit()
                            send_seletor_categoria(sender_phone, nome)
                            return {"status": "ok"}
                        if status.startswith("aguardando_"):
                            rest = status[len("aguardando_"):]
                            try:
                                topic_key, dia_escolhido = rest.rsplit('_', 1)
                            except ValueError:
                                topic_key = rest
                                dia_escolhido = 'hoje'
                        else:
                            topic_key = None
                            dia_escolhido = 'hoje'
                        data_referencia = resolver_data(dia_escolhido)
                        registro = get_registro_por_data(session, data_referencia, sender_phone)
                        if topic_key in TOPICOS_TEXTO:
                            topic_info = TOPICOS_TEXTO[topic_key]
                            coluna = topic_info['coluna']
                            try:
                                if topic_info['tipo'] == 'nota':
                                    nota = float(texto_usuario.replace(',', '.'))
                                    if not (0 <= nota <= 10):
                                        raise ValueError("Nota fora do intervalo")
                                    setattr(registro, coluna, nota)
                                elif topic_info['tipo'] == 'hora':
                                    hora_obj = datetime.datetime.strptime(texto_usuario, '%H:%M').time()
                                    data_completa = datetime.datetime.combine(data_referencia, hora_obj)
                                    data_completa_brasil = FUSO_BRASIL.localize(data_completa)
                                    setattr(registro, coluna, data_completa_brasil)
                                elif topic_info['tipo'] == 'hora_anterior':
                                    hora_obj = datetime.datetime.strptime(texto_usuario, '%H:%M').time()
                                    data_anterior = data_referencia - datetime.timedelta(days=1)
                                    data_completa = datetime.datetime.combine(data_anterior, hora_obj)
                                    data_completa_brasil = FUSO_BRASIL.localize(data_completa)
                                    setattr(registro, coluna, data_completa_brasil)
                                registro.status_conversa = None
                                session.commit()
                                send_whatsapp_message(sender_phone, "Anotado! ✅")
                                send_dynamic_menu(sender_phone, session, registro, 'metricas', dia_escolhido)
                            except ValueError:
                                send_whatsapp_message(sender_phone, "Resposta inválida. Por favor, tente novamente.")
                                send_whatsapp_message(sender_phone, topic_info['texto'].format(dia=rotulo_dia(data_referencia)))
                        return {"status": "ok"}
    except Exception as e:
        print(f"!!!!!!!!!! ERRO CRÍTICO NO WEBHOOK !!!!!!!!!!!")
        print(f"Erro: {e}")
        traceback.print_exc()
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
