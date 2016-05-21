from datetime import datetime
import telepot

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from bot.models import Bot, PhotoMessage, TextMessage, TelegramUser, LocationMessage

class Command(BaseCommand):
    help = 'Processa i messaggi di un bot di Telegram'

#     def add_arguments(self, parser):
#         parser.add_argument('poll_id', nargs='+', type=int)

    def handle(self, *args, **options):
        self.stdout.write("Starting bot message processor")
        bot = Bot.objects.get(pk=1)
        bot.telepot = telepot.Bot('239323847:AAHX2Lh7UX4YidFoCvWX3nL2dNS3t0JRKPM')
        
        bot.telepot.getMe()
        responses = bot.telepot.getUpdates()
        for response in responses:
            try:
                with transaction.atomic():
                    # messaggio già processato ?
                    m_id = response['message']['message_id']
                    if len(list(PhotoMessage.objects.filter(telegram_message_id = m_id)) + list(LocationMessage.objects.filter(telegram_message_id = m_id)) + list(TextMessage.objects.filter(telegram_message_id = m_id))) == 0:
                        # esiste l'utente ?
                        if len(TelegramUser.objects.filter(telegram_id = response['message']['from']['id'])) == 0:
                            ut = TelegramUser()
                            ut.telegram_id = response['message']['from']['id']
                            ut.first_name = response['message']['from']['first_name']
                            ut.last_name = response['message']['from']['last_name']
                            ut.save()
                        else:
                            ut = TelegramUser.objects.get(telegram_id = response['message']['from']['id']) 
                        
                        if 'text' in response['message'].keys():
                            m = TextMessage()
                        if 'location' in response['message'].keys():
                            m = LocationMessage()
                        if 'photo' in response['message'].keys():
                            m = PhotoMessage()
            
                        # parte comune
                        m.when_sent = datetime.fromtimestamp(response['message']['date'])
                        m.telegram_message_id = response['message']['message_id']
                        m.utente = ut
                        m.bot = bot
            
                        if 'text' in response['message'].keys():
                            m.text = response['message']['text']
                        if 'location' in response['message'].keys():
                            m.longitude = response['message']['location']['longitude']
                            m.latitude = response['message']['location']['latitude']
                        if 'photo' in response['message'].keys():
                            thumb_number = 0
                            thumb_path = settings.TMP + str(response['message']['message_id']) + 't.jpg' 
                            bot.telepot.download_file(response['message']['photo'][thumb_number]['file_id'], thumb_path)
                            f = open(thumb_path, 'rb')
                            flat_txt = f.read()
                            m.photo_thumb.save(str(response['message']['message_id']) + 't.jpg', ContentFile(flat_txt))
                            
                            hires_number = 3
                            hires_path = settings.TMP + str(response['message']['message_id']) + 'h.jpg' 
                            bot.telepot.download_file(response['message']['photo'][hires_number]['file_id'], hires_path)
                            f = open(hires_path, 'rb')
                            flat_txt = f.read()
                            m.photo_hires.save(str(response['message']['message_id']) + 'h.jpg', ContentFile(flat_txt))
                            if 'caption' in response['message'].keys():
                                m.photo_caption = response['message']['caption']
                        m.save()
            except Exception as ex:
                pass
    #             logger.error(str(ex))
