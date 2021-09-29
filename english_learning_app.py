from flask import Flask, request, abort

from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *
import json
import tempfile, os

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from azure.cognitiveservices.speech import AudioDataStream
import azure.cognitiveservices.speech as speechsdk
import requests,uuid


app = Flask(__name__)

# secretFile = json.load(open("secretFile.txt",'r'))
channelAccessToken = 'qcNg2PlvJ34v5xEASp/jtVG/mrT7yRWaVsxRfTTlVlF0YNu2p44kWAcvjJvuR96+zOO3OHdF2AzTs4v3OzbZcF9ENtj6HxpiqamqJmpBGaFDisrRozj0QNpKXZhqkPz0+9CdziyLDu/3GCxGA5I0jwdB04t89/1O/w1cDnyilFU='
channelSecret = '4f14ed18d582cec2a024aaf7f29bff7e'

# static_tmp_path = os.path.join( 'static', 'tmp')

line_bot_api = LineBotApi(channelAccessToken)
handler = WebhookHandler(channelSecret)

static_tmp_path = os.path.join( 'static', 'tmp')

@app.route("/", methods=['GET', 'POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=(ImageMessage, TextMessage))
def handle_message(event):
    SendMessages = list()
    textlist=[]
    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
        message_content = line_bot_api.get_message_content(event.message.id)
        with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            tempfile_path = tf.name

        dist_path = tempfile_path + '.' + ext
        dist_name = os.path.basename(dist_path)
        os.rename(tempfile_path, dist_path)
        try:
  
            path = os.path.join('static', 'tmp', dist_name)
            print(path) 

        except:
            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(text=' yoyo'),
                    TextSendMessage(text='請傳一張圖片給我')
                ])
            return 0

        # 圖片敘述 API key.
        subscription_key = '18c2a6ec72e7457e8000bc292cef7a31'

        # 圖片敘述 API endpoint.
        endpoint = 'https://wendycv.cognitiveservices.azure.com/'

        # Call API
        computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))

        # 指定圖檔
        # local_image_path = os.getcwd() + '/static/tmp/{}'.format(path.split('/')[-1])
        local_image_path = os.getcwd() + '\\static\\tmp\\{}'.format(path.split('\\')[-1])

        # 讀取圖片
        local_image = open(local_image_path, "rb")

        print("===== Describe an image - remote =====")
        # Call API
        description_results = computervision_client.describe_image_in_stream(local_image)
        # Get the captions (descriptions) from the response, with confidence level
        print("Description of remote image: ")
        if (len(description_results.captions) == 0):
            print("No description detected.")
        else:
            for caption in description_results.captions:
                print("'{}' with confidence {:.2f}%".format(caption.text, caption.confidence * 100))
                textlist.append(caption.text)
                
        #抓取關鍵字 api
        key = "f662a163d9a84249a6052dd829e04279"
        #抓取關鍵字 endpoint
        endpoint = "https://wendytext.cognitiveservices.azure.com/"

        text_analytics_client = TextAnalyticsClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        documents = ['{}'.format(caption.text)]

        result = text_analytics_client.extract_key_phrases(documents)
        for doc in result:
            if not doc.is_error:
                print(doc.key_phrases)
                for docc in doc.key_phrases:
                    textlist.append(docc)
                    
                
                
            if doc.is_error:
                print(doc.id, doc.error)
        
        
        #中翻英api key
        subscription_key = '234df0e3c8c346129437ae5f3f759253' 
        #中翻英api endpoint
        endpoint = 'https://api.cognitive.microsofttranslator.com/'
        path = '/translate?api-version=3.0'


        params = '&to=de&to=zh-Hant'
        constructed_url = endpoint + path + params

        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        
        wee=[]
        for text in textlist:
            arug={'text': "{}".format(text)}
            wee.append(arug)
            

        body = wee

        request = requests.post(constructed_url, headers=headers, json=body)
        response = request.json()
        print(response)
        wcl=[]
        for n ,i in  enumerate (response):
            
            wcl.append(response[n]['translations'][1]['text'])
        ett=wcl[0]
        print(wcl)
        print(ett)
        wew=[]
        for u, docc in enumerate(doc.key_phrases):
            r=str(docc+'->'+wcl[u+1])
            wew.append(r)

        awew= ",".join(wew)
        staa="""描述：{}\n翻譯：{}\n單字：{}""".format(caption.text,ett,awew)
        
        # #google語音
        # stream_url = 'https://translate.google.com/translate_tts?ie=UTF-8&tl=en-US&client=tw-ob&ttsspeed=1&q={}'.format(caption.text)
        # stream_url=stream_url.replace(' ','%20')

        #azure語音
        # Replace with your own subscription key and region identifier from here: https://aka.ms/speech/sdkregion
        speech_key, service_region = "11bb7bcd02184684aa802044d58e5842", "westus2"
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)

        # Creates an audio configuration that points to an audio file.
        # Replace with your own audio filename.
        audio_filename = "speech.mp3"
        audio_output = speechsdk.audio.AudioOutputConfig(filename=audio_filename)

        # Creates a synthesizer with the given settings
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_output)

        # Synthesizes the text to speech.
        # Replace with your own text.
        text = caption.text
        result = speech_synthesizer.speak_text_async(text).get()
        stream = AudioDataStream(result)
        stream.save_to_wav_file(os.getcwd() + '/static/audio/speech.mp3')


        NGROK_URL='https://8def086f9163.ngrok.io'

        # SendMessages.append(AudioSendMessage(original_content_url=stream_url, duration=3000))
        SendMessages.append(AudioSendMessage(original_content_url='%s/static/audio/speech.mp3'%NGROK_URL, duration=3000))
        SendMessages.append(TextSendMessage(text = staa))
        line_bot_api.reply_message(event.reply_token,SendMessages)
        
if __name__ == "__main__":
    app.run(host='0.0.0.0')
