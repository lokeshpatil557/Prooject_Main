from googletrans import Translator
from langdetect import detect, LangDetectException

SUPPORTED_LANGUAGES = ['en', 'es', 'zh-cn', 'zh-tw']

def detect_language_safe(text):
    try:
        lang = detect(text)
        if lang in SUPPORTED_LANGUAGES:
            return lang
        else:
            return 'unsupported'
    except LangDetectException:
        return 'en'  

def translate_text(text, target_lang='en'):
    try:
        translator = Translator()
        translated = translator.translate(text, dest=target_lang)
        return translated.text
    except Exception as e:
        return f"Translation error: {e}"



