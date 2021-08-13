import pyttsx3
tts = pyttsx3.init()
for voice in tts.getProperty('voices'):
    tts.setProperty('voice', voice.id)
    print(voice.name)
    tts.say("Hello World")
    tts.runAndWait()