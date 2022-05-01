import speech_recognition as sr
from gtts import gTTS
import os

# Beginning of the AI
class ChatBot():
    def __init__(self, name):
        print("----- starting up", name, "-----")
        self.name = name

    def speech_to_text(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as mic:
             print("listening...")
             audio = recognizer.listen(mic)
        try:
             self.text = recognizer.recognize_google(audio)
             print("me --> ", self.text)
        except:
             print("me -->  ERROR")

    def wake_up(self, text):
        if self.name in text.lower():
            return True
        else:
            return False

    @staticmethod
    def text_to_speech(text):
        if text:
            print("AI --> ", text)
            speaker = gTTS(text=text, lang="en", slow=False)
            speaker.save("res.mp3")
            os.system("afplay res.mp3")  #if you have a macbook->afplay or for windows use->start
            os.remove("res.mp3")


# Execute the AI
if __name__ == "__main__":
     ai = ChatBot(name="frankie")
     res = None
     while True:
         ai.speech_to_text()
         ## wake up
         if ai.wake_up(ai.text) is True:
             res = "Hello I am FRANKIE, how may I crush your spirits?"

         ai.text_to_speech(res)
