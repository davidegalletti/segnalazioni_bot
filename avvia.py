# -*- coding: utf-8 -*-
import asyncio
import django
import logging
import segnalazioni_bot.settings
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
        logger.info("NUOVO MESSAGGIO %s sulla chat %s: '%s' " % (msg['message_id'], chat_id, content_type))
#         hide_keyboard = {'hide_keyboard': True}
#         self.bot.telepot.sendMessage(msg['from']['id'], 'I am hiding it', reply_markup=hide_keyboard)
#         show_keyboard = {'keyboard': [['Yes','No'], ['request-location','Maybe not']]}
#         self.bot.telepot.sendMessage(msg['from']['id'], 'This is a custom keyboard', reply_markup=show_keyboard)
        try:
            with transaction.atomic():
                # messaggio già processato ?
                m_id = msg['message_id']
                logger.debug("Ricevuto da Telegram messaggio %s ..." % msg['message_id'])
                if len(list(TelegramMessage.objects.filter(telegram_message_id = m_id))) == 0:
                    # esiste l'utente ?
                    logger.info("... da processare")
                    if len(TelegramUser.objects.filter(telegram_id = msg['from']['id'])) == 0:
                        logger.warning("Nuovo utente Telegram %s %s %s, lo creo" % (msg['from']['id'], msg['from']['first_name'], msg['from']['last_name']))
                        ut = TelegramUser()
                        ut.telegram_id = msg['from']['id']
                        ut.first_name = msg['from']['first_name']
                        ut.last_name = msg['from']['last_name']
                        if 'username' in msg['from'].keys():
                            ut.username =  msg['from']['username']
                        ut.save()
                    else:
                        ut = TelegramUser.objects.get(telegram_id = msg['from']['id'])
                        if 'username' in msg['from'].keys() and ut.username !=  msg['from']['username']:
                            logger.info("L'utente Telegram %s adesso ha anche lo username %s, aggiorno sul db." % (msg['from']['id'], msg['from']['username']))
                            ut.username =  msg['from']['username']
                            ut.save()
                    if 'entities' in msg.keys():
                        try:
                            if msg['entities'][0]['type'] == 'bot_command':
                                if content_type == 'text':
                                    if msg['text'] == '/help' or msg['text'] == '/info':
                                        self.bot.telepot.sendMessage(ut.telegram_id, '''Questo è un BOT di prova. L'intento è raccogliere segnalazioni fotografiche geolocalizzate. Il funzionamento è semplice: 
 1) Invia la tua posizione
 2) Scatta e invia una fotografia
Ripeti questa sequenza quante volte vuoi. I dati vengono pubblicati in un dataset. Se mandi due posizioni o due fotografie di seguito, viene usata solo la seconda delle due; una fotografia inviata prima di aver mandato la posizione viene scartata.
/map - per sapere dove trovare la mappa con tutte le segnalazioni
/stato - per sapere quante segnalazioni hai registrato''')
                                    elif msg['text'] == '/map':
                                        self.bot.telepot.sendMessage(ut.telegram_id, 'http://108.161.134.31:8800/static/map.html')
                                    elif msg['text'] == '/logstart':
                                        if 'username' in msg['from'].keys() and msg['from']['username'] == 'davidegalletti':
                                            self.bot.admin_logging = True
                                            self.bot.admin_chat_id = ut.telegram_id
                                            self.bot.save()
                                            self.bot.telepot.sendMessage(self.bot.admin_chat_id, 'Setting log ON')
                                    elif msg['text'] == '/logstop':
                                        if 'username' in msg['from'].keys() and msg['from']['username'] == 'davidegalletti':
                                            self.bot.admin_logging = False
                                            self.bot.save()
                                            self.bot.telepot.sendMessage(self.bot.admin_chat_id, 'Setting log OFF')
                                    elif msg['text'] == '/stato':
                                        quante = len(Segnalazione.objects.filter(photo_message__utente__telegram_id = ut.telegram_id))
                                        if quante == 0:
                                            self.bot.telepot.sendMessage(ut.telegram_id, 'Non hai ancora inviato alcuna segnalazione.')
                                        elif quante == 1:
                                            self.bot.telepot.sendMessage(ut.telegram_id, 'Hai inviato una segnalazione. Grazie!')
                                        else:
                                            self.bot.telepot.sendMessage(ut.telegram_id, 'Hai inviato %s segnalazioni. Grazie!' % quante)
                        except Exception as ex:
                            logger.error(str(ex))
                            if self.bot.admin_logging:
                                self.bot.telepot.sendMessage(my_bot.admin_chat_id, str(ex))

                    m = TelegramMessage()
                    # parte comune
                    m.chat_id = chat_id
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
                        logger.info('E\' un messaggio "location", ho trovato %s altri messaggi ...' % len(id_messaggi_vicini))
                        segnalazioni_vicine = Segnalazione.objects.filter(location_message__in = id_messaggi_vicini)
                        logger.info('... di cui %s sono segnalazioni complete' % segnalazioni_vicine.count())
                        if segnalazioni_vicine.count() > 0:
                            risposta_parte_comune = " foto; se non è indispensabile, non inviare una nuova segnalazione nello stesso luogo."
                            if segnalazioni_vicine.count() == 1:
                                risposta = "C'è già una segnalazione nel raggio di 50 metri. Ti mostro la" + risposta_parte_comune
                            else:
                                risposta = "C'è più di una segnalazione nel raggio di 50 metri. Ti mostro le" + risposta_parte_comune
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
                        
                        hires_number = len(msg['photo']) - 1
                        hires_path = settings.TMP + str(msg['message_id']) + 'h.jpg' 
                        self.bot.telepot.download_file(msg['photo'][hires_number]['file_id'], hires_path)
                        f = open(hires_path, 'rb')
                        flat_txt = f.read()
                        m.photo_hires.save(str(msg['message_id']) + 'h.jpg', ContentFile(flat_txt))
                        if 'caption' in msg.keys():
                            m.caption = msg['caption']
                    m.save()
                else:
                    logger.debug("... che avevo già processato. Lo ignoro.")
        except Exception as ex:
            logger.error("ERRORE registrando un messaggio: " + str(ex))
            if self.bot.admin_logging:
                self.bot.telepot.sendMessage(my_bot.admin_chat_id, str(ex))
        logger.debug("Creo la lista di messaggi della stessa chat da processare...")
        current_chat = '' 
        lista_messaggi_chat = []
        ## per ora il codice che segue non ha troppo senso, gestirebbe anche più di una chat per 
        #  utente cambiando il filter sulla seguente riga da "chat_id=chat_id" a "utente.telegram_id=msg['from']['id']"
        ## ma non so come funzionano gli id delle chat rispetto gli id degli utenti; postponed
        for tm in TelegramMessage.objects.filter(chat_id=chat_id, processed=False).order_by('telegram_message_id', 'when_sent'):
            logger.debug("Messaggio dal db sulla chat %s: '%s' " % (chat_id, tm.content_type))
            if tm.content_type == 'text': # non faccio niente per ora con i messaggi di testo; sulle foto ci può essere la caption
                logger.debug("Messaggio %s dal db sulla chat %s: '%s' scartato." % (tm.id, chat_id, tm.content_type))
                tm.processed = True
                tm.save()
            elif len(lista_messaggi_chat) == 0:
                logger.debug("Messaggio %s dal db sulla chat %s: '%s' accodato." % (tm.id, chat_id, tm.content_type))
                lista_messaggi_chat.append(tm)
                current_chat = tm.chat_id
            elif current_chat == tm.chat_id:
                lista_messaggi_chat.append(tm)
            else:
                bc = BotChat(lista_messaggi_chat, self.bot, current_chat)
                bc.processa_lista()
                # ho processato la chat, passo alla prossima
                current_chat = tm.chat_id        
                lista_messaggi_chat = [tm]
        if len(lista_messaggi_chat) > 0:
            bc = BotChat(lista_messaggi_chat, self.bot, current_chat)
            bc.processa_lista()
                
    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        logger.info('Callback Query:', query_id, from_id, query_data)

    def on_inline_query(self, msg):
        query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
        logger.info('Inline Query:', query_id, from_id, query_string)

        def compute_answer():
            articles = [{'type': 'article',
                            'id': 'abc', 'title': query_string, 'message_text': query_string}]

            return articles

        self._answerer.answer(msg, compute_answer)

    def on_chosen_inline_result(self, msg):
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        logger.info('Chosen Inline Result:', result_id, from_id, query_string)


class BotChat():
    def __init__(self, lista_messaggi, bot, chat_id):
        self.lista_messaggi = lista_messaggi
        self.bot = bot
        self.chat_id = chat_id

    def processa_lista(self):
        logger.debug("processa_lista: Processo la lista di messaggi della chat %s." % self.chat_id)
        if len(self.lista_messaggi) > 0:
            logger.info("processa_lista: La chat %s ha %s messaggi." % (self.chat_id, len(self.lista_messaggi)))
            # processo la lista di messaggi di una chat ordinata per when_sent
            # mi aspetto una location seguita da una o più foto che associo alla stessa location
            # se inizia con una foto CHE FACCIO? Mando una richiesta di location che dovrebbe restituirmi una callback?
            # se c'è una location non seguita da una foto non faccio niente
            location_message = None
            photo_messages = []
            risposta = ''
            foto_scartate = False
            location_in_attesa_di_foto = False
            for m in self.lista_messaggi:
                testo_log_comune = ("processa_lista: chat %s, messaggio %s. " % (self.chat_id, m.id))
                if location_message is None and m.content_type == 'photo': # brucio le foto iniziali; bisogna mandare la location per prima
                    logger.info(testo_log_comune + "Foto non preceduta da location, la brucio.")
                    foto_scartate = True
                    m.processed = True
                    m.save()
                elif location_message is None and m.content_type == 'location':
                    logger.info(testo_log_comune + "Trovata location, aspetto la foto.")
                    location_in_attesa_di_foto = True
                    location_message = m
                elif m.content_type == 'photo':
                    logger.info(testo_log_comune + "Trovata anche la la foto. Registro la segnalazione")
                    location_in_attesa_di_foto = False
                    # finalmente associo
                    s = Segnalazione()
                    s.photo_message = m
                    s.location_message = location_message
                    s.save()
                    m.processed = True
                    m.save()
                    location_message.processed = True
                    location_message.save()
                    risposta += 'Grazie, ho registrato una foto geolocalizzata.\n'
                else:
                    risposta += ('Ho scartato un messaggio "%s\n". ' % m.content_type)
                    m.processed = True
                    m.save()
            if location_in_attesa_di_foto:
                risposta += "Ho ricevuto la posizione, per favore scatta e invia una foto.\n"
            if foto_scartate:
                risposta += "Ho scartato una o più foto perché non erano precedute dalla geolocalizzazione. Per favore invia la posizione prima della foto.\n" + risposta
            if risposta:
                self.bot.telepot.sendMessage(self.lista_messaggi[0].utente.telegram_id, risposta)
        
print("Loading django configuration")   
# rimuovere il commento dalla riga seguente per eseguire da command-line
settings.configure(default_settings= segnalazioni_bot.settings)

print("Setting up django")   
django.setup()

DATEFMT = "%d/%b/%Y %H:%M:%S"
FORMAT = "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s"
FILENAME = '/tmp/segnalazionibot.log'
logging.basicConfig(format=FORMAT,datefmt=DATEFMT,filename=FILENAME,level=20)
logger = logging.getLogger(__name__)

from bot.models import Bot, TelegramUser, TelegramMessage, Segnalazione
my_bot = Bot.objects.get(pk=1)
logger.info("Loading bot with id %s: '%s'" % (my_bot.id, my_bot.nome))   
my_bot.telepot = telepot.Bot(my_bot.token)
try:
    out = my_bot.telepot.getMe()
    if my_bot.admin_logging:
        my_bot.telepot.sendMessage(my_bot.admin_chat_id, ("Connected to Telegram: %s" % out)   )
    logger.warning("Connected to Telegram: %s" % out)   
    
    bot = YourBot(my_bot, my_bot.token)
    loop = asyncio.get_event_loop()
    
    loop.create_task(bot.message_loop())
    logger.debug("Starting the forever loop")
    loop.run_forever()
except Exception as ex:
    logger.error("Error starting bot with getMe: \"%s\" - \"%s\"" % (str(ex), str(ex.json)))
    if my_bot.admin_logging:
        my_bot.telepot.sendMessage(my_bot.admin_chat_id, ("Error starting bot with getMe: \"%s\" - \"%s\"" % (str(ex), str(ex.json)))   )
    