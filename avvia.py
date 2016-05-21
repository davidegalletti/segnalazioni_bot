import asyncio
import django
import segnalazioni_bot.settings
import sys
import telepot
import telepot.async

from datetime import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

class YourBot(telepot.async.Bot):
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        super(YourBot, self).__init__(*args, **kwargs)
        self._answerer = telepot.async.helper.Answerer(self)

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
#         hide_keyboard = {'hide_keyboard': True}
#         self.bot.telepot.sendMessage(msg['from']['id'], 'I am hiding it', reply_markup=hide_keyboard)
#         show_keyboard = {'keyboard': [['Yes','No'], ['request-location','Maybe not']]}
#         self.bot.telepot.sendMessage(msg['from']['id'], 'This is a custom keyboard', reply_markup=show_keyboard)
        try:
            with transaction.atomic():
                # messaggio già processato ?
                m_id = msg['message_id']
                if len(list(TelegramMessage.objects.filter(telegram_message_id = m_id))) == 0:
                    # esiste l'utente ?
                    if len(TelegramUser.objects.filter(telegram_id = msg['from']['id'])) == 0:
                        ut = TelegramUser()
                        ut.telegram_id = msg['from']['id']
                        ut.first_name = msg['from']['first_name']
                        ut.last_name = msg['from']['last_name']
                        ut.save()
                    else:
                        ut = TelegramUser.objects.get(telegram_id = msg['from']['id'])
                        if 'username' in msg['from'].keys() and ut.username !=  msg['from']['username']:
                            ut.username =  msg['from']['username']
                            ut.save()
                    m = TelegramMessage()
                    # parte comune
                    m.when_sent = datetime.fromtimestamp(msg['date'])
                    m.telegram_message_id = msg['message_id']
                    m.utente = ut
                    m.bot = self.bot
                    m.content_type = content_type
                     
                    if content_type == 'text':
                        m.text = msg['text']
                    if content_type == 'location':
                        m.longitude = msg['location']['longitude']
                        m.latitude = msg['location']['latitude']
                        # cerco le location entro i 50 metri (con calcolo approssimativo per fare query efficente:
                        # 0.0002 di latitudine o longitudine sono 22.263 metri = 22 metri e 263 mm )
                        # COME FILTRO QUELLI CHE SONO IN UNA SEGNALAZIONE ??
                        # prendo al max 5 
                        id_messaggi_vicini = list(tm.id for tm in TelegramMessage.objects.filter(content_type='location').extra(where=[("ABS(longitude-%s)<0.0002 AND ABS(latitude-%s)<0.0002") % (m.longitude, m.latitude)])[:5])
                        segnalazioni_vicine = Segnalazione.objects.filter(location_message__in = id_messaggi_vicini)
                        if segnalazioni_vicine.count() > 0:
                            if segnalazioni_vicine.count() == 1:
                                risposta = "C'è già una segnalazione nel raggio di 50 metri. Ti mostro la foto; se non è necessario, non inviare una nuova segnalazione nello stesso luogo."
                            else:
                                risposta = "C'è più di una segnalazione nel raggio di 50 metri. Ti mostro le foto; se non è necessario, non inviare una nuova segnalazione nello stesso luogo."
                            self.bot.telepot.sendMessage(ut.telegram_id, risposta)
                            for s in segnalazioni_vicine:
                                self.bot.telepot.sendLocation(ut.telegram_id, s.location_message.latitude, s.location_message.longitude)
                                f = open(s.photo_message.photo_thumb.path, 'rb')  # some file on local disk
                                response = self.bot.telepot.sendPhoto(ut.telegram_id, f)
                    if content_type == 'photo':
                        thumb_number = 0
                        thumb_path = settings.TMP + str(msg['message_id']) + 't.jpg' 
                        self.bot.telepot.download_file(msg['photo'][thumb_number]['file_id'], thumb_path)
                        f = open(thumb_path, 'rb')
                        flat_txt = f.read()
                        m.photo_thumb.save(str(msg['message_id']) + 't.jpg', ContentFile(flat_txt))
                        
                        hires_number = 3
                        hires_path = settings.TMP + str(msg['message_id']) + 'h.jpg' 
                        self.bot.telepot.download_file(msg['photo'][hires_number]['file_id'], hires_path)
                        f = open(hires_path, 'rb')
                        flat_txt = f.read()
                        m.photo_hires.save(str(msg['message_id']) + 'h.jpg', ContentFile(flat_txt))
                        if 'caption' in msg.keys():
                            m.caption = msg['caption']
                    m.save()
        except Exception as ex:
            pass
#             logger.error(str(ex))
        # processo i messaggi nella stessa chat per cercare di mettere insieme
        current_chat = '' 
        lista_messaggi_chat = []
        for tm in TelegramMessage.objects.filter(processed=False).order_by('telegram_message_id', 'when_sent'):
            if tm.content_type == 'text': # non faccio niente per ora con i messaggi di testo; sulle foto ci può essere la caption
                tm.processed = True
                tm.save()
            elif len(lista_messaggi_chat) == 0:
                lista_messaggi_chat.append(tm)
                current_chat = tm.utente.telegram_id
            elif current_chat == tm.utente.telegram_id:
                lista_messaggi_chat.append(tm)
            else:
                bc = BotChat(lista_messaggi_chat)
                bc.processa_lista()
                # ho processato la chat, passo alla prossima
                current_chat = tm.utente.telegram_id        
                lista_messaggi_chat = [tm]
        if len(lista_messaggi_chat) > 0:
            bc = BotChat(lista_messaggi_chat, self.bot)
            bc.processa_lista()
                
    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        print('Callback Query:', query_id, from_id, query_data)

    def on_inline_query(self, msg):
        query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
        print('Inline Query:', query_id, from_id, query_string)

        def compute_answer():
            articles = [{'type': 'article',
                            'id': 'abc', 'title': query_string, 'message_text': query_string}]

            return articles

        self._answerer.answer(msg, compute_answer)

    def on_chosen_inline_result(self, msg):
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        print('Chosen Inline Result:', result_id, from_id, query_string)


class BotChat():
    def __init__(self, lista_messaggi, bot):
        self.lista_messaggi = lista_messaggi
        self.bot = bot

    def processa_lista(self):
        if len(self.lista_messaggi) > 0:
            # processo la lista di messaggi di una chat ordinata per when_sent
            # mi aspetto una location seguita da una o più foto che associo alla stessa location
            # se inizia con una foto CHE FACCIO? Mando una richiesta di location che dovrebbe restituirmi una callback?
            # se c'è una location non seguita da una foto non faccio niente
            location_message = None
            photo_messages = []
            risposta = ''
            foto_scartate = False
            for m in self.lista_messaggi:
                if location_message is None and m.content_type == 'photo': # brucio le foto iniziali; bisogna mandare la location per prima
                    foto_scartate = True
                    m.processed = True
                    m.save()
                elif location_message is None and m.content_type == 'location':
                    location_message = m
                elif m.content_type == 'photo':
                    # finalmente associo
                    s = Segnalazione()
                    s.photo_message = m
                    s.location_message = location_message
                    s.save()
                    m.processed = True
                    m.save()
                    location_message.processed = True
                    location_message.save()
                    risposta += 'Grazie, ho registrato una foto geolocalizzata. '
                else:
                    risposta += ('Ho scartato un messaggio "%s". ' % m.content_type)
                    m.processed = True
                    m.save()
            if foto_scartate:
                risposta = "Ho scartato una o più foto perché non erano precedute dalla geolocalizzazione. Per favore invia la posizione prima della foto. " + risposta
            if risposta:
                self.bot.telepot.sendMessage(self.lista_messaggi[0].utente.telegram_id, risposta)
        
# rimuovere il commento dalla riga seguente per eseguire da command-line
# settings.configure(default_settings= segnalazioni_bot)   
django.setup()

from bot.models import Bot, TelegramUser, TelegramMessage, Segnalazione
my_bot = Bot.objects.get(pk=1)
my_bot.telepot = telepot.Bot(my_bot.token)
my_bot.telepot.getMe()

bot = YourBot(my_bot, my_bot.token)
loop = asyncio.get_event_loop()

loop.create_task(bot.message_loop())

loop.run_forever()