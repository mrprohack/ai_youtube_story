SUPPORTED_LANGUAGES = {
    'en': {'name': 'English', 'script_style': 'western'},
    'es': {'name': 'Spanish', 'script_style': 'western'},
    'zh': {'name': 'Chinese', 'script_style': 'asian'},
    'ja': {'name': 'Japanese', 'script_style': 'asian'},
    'ta': {'name': 'Tamil', 'script_style': 'indian'},
    'hi': {'name': 'Hindi', 'script_style': 'indian'}
}

def get_language_config(language_code: str) -> dict:
    return SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES['en'])

def get_script_template(style: str) -> dict:
    templates = {
        'western': {
            'hook': 'Welcome to our channel!',
            'intro': 'Today we will explore...',
            'main_content': 'Let me tell you about...',
            'engagement': 'If you enjoyed this content...',
            'call_to_action': 'Don\'t forget to like and subscribe!',
            'cliffhanger': 'Stay tuned for our next episode...'
        },
        'asian': {
            'hook': 'ようこそ！/ 欢迎！',
            'intro': '今日は... / 今天我们...',
            'main_content': '今から... / 让我告诉你...',
            'engagement': 'もし良かったら... / 如果您喜欢...',
            'call_to_action': 'チャンネル登録お願いします！/ 请订阅我们的频道！',
            'cliffhanger': '次回をお楽しみに！/ 下集再见！'
        },
        'indian': {
            'hook': 'नमस्कार / வணக்கம்!',
            'intro': 'आज हम... / இன்று நாம்...',
            'main_content': 'मैं आपको बताता/बताती हूं... / நான் உங்களுக்கு சொல்கிறேன்...',
            'engagement': 'अगर आपको यह वीडियो पसंद आया... / இந்த வீடியோ பிடித்திருந்தால்...',
            'call_to_action': 'चैनल को सब्सक्राइब करना न भूलें! / எங்கள் சேனலை subscribe செய்யுங்கள்!',
            'cliffhanger': 'अगली एपिसोड का इंतज़ार करें... / அடுத்த எபிசோட்டில் சந்திப்போம்...'
        }
    }
    return templates.get(style, templates['western']) 