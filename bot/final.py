import speech_recognition as sr
import os
import cv2
from ctypes import c_bool
import pickle
import sounddevice as sd
import vosk
import multiprocessing as mp
import queue
import json
import pyttsx3
import random
import time
import sys

AFTER_HOURS = True


def build_persona():
    persona = {}
    for i in range(4):
        persona[i] = {}


    if AFTER_HOURS:
        persona[0][0] = ["Hello, I am sexy off duty detention monitor Ward N. Lemon.",]

        persona[0][1] = ["You get so much hotter every time we break up.",
                            "You remind me so much of my sister.",
                            "I have many penises."]

        persona[0][2] = ["Please talk dirty to me?",]

        persona[1][0] = ["Hot damn that was good.",]

        persona[1][1] = ["Do you have any mouthwash?",
                             "Did you use organic detergent, because if not, I am going to have to leave, because I will have a reaction.",
                             "Are these Walmart panties?"]

        persona[1][2] = ["Please ask me a question so I may talk dirty to you too.",]

        persona[2][0] = ["Was that good for you too?",]
        persona[3][0] = ["You're a super gal, I'll call you. Goodbye!",]

    else:
        persona[0][0] = ["Hello, I am detention monitor Ward N. Lemon.",]

        persona[0][1] = ["Hey, people screw around.  But you got caught.",
                                "Well, well.  Here we are.",
                                "I wonder, is this the first time or the last time that you’ll be here?"]

        persona[0][2] = ["What do you have to say for yourself?",]

        persona[1][0] = ["You have exactly " + str(random.randint(1,19)) + " minutes to gauge the error of your ways. Use this time to your advantage.",
                                "No school is going to give a scholarship to a discipline case. Think about your future next time you wish to misbehave.",
                                "Enjoy your time here. Maybe you'll learn something about yourself."]

        persona[1][1] = ["Do you have a question for me?",]

        persona[1][2] = ["Please ask so I may crush your spirits.",
                         "You may speak now, impertinent child.",
                         "Ask and you will receive some sort of answer.",
                         "I have an IQ of " + str(random.randint(1,10000)) + ". Ask and I may decide to use it."]
        persona[2][0] = ["Does that answer your question?",]
        persona[3][0] = ["I don't really care. Goodbye!",]

    return persona


class SpeechEngine():
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('voice', 'com.apple.speech.synthesis.voice.samantha')
        self.engine.setProperty('rate', 150)

    def respond(self, response, new_text_flag):
        file = open('response', 'wb')
        pickle.dump(response, file)
        file.close()

        new_text_flag.value = True

        print("AI --> ", response)
        self.engine.say(response)
        self.engine.runAndWait()

    def stop(self):
        self.engine.stop()


def ai_loop(new_text_flag, ai_name):
    my_ai = AI(ai_name)
    my_ai.run(new_text_flag)

class AI:
    def __init__(self, ai_name):
        self.ai_name = ai_name

        print("----- starting up", ai_name, "-----")

        self.speech_rec_model = vosk.Model('model')
        
        sd.default.device = [1, 0]

        device_info = sd.query_devices(None, 'input')
        self.samplerate = int(device_info['default_samplerate'])

        self.q = queue.Queue()

        self.speech_engine = SpeechEngine()
        
        if AFTER_HOURS:
            phrases_file = 'sexy_phrases.txt'
        else:
            phrases_file = 'random_phrases.txt'

        self.responses = open(phrases_file, encoding = "ISO-8859-1").read().splitlines()

    def callback(self, indata, frames, time, status):
        # This is called (from a separate thread) for each audio block
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def run(self, new_text_flag):
        persona = build_persona()
        input_text = None
        stage = 0

        stream = sd.RawInputStream(samplerate=self.samplerate,
                                dtype='int16',
                                channels=1,
                                callback=self.callback)

        with stream:
            rec = vosk.KaldiRecognizer(self.speech_rec_model, self.samplerate)

            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    input_text = json.loads(rec.Result())['text'].strip()
                    print("me --> [", input_text, "]")
                    if input_text:
                        stream.stop()
                        if stage == 2:
                            # Generate a response using the loaded ML model
                            self.speech_engine.respond("Thinking...", new_text_flag)
                            time.sleep(random.randint(1, 5))
                            if AFTER_HOURS:
                                response = ''
                                for _ in range(10):
                                    response += (random.choice(self.responses) + '. ')
                            else:
                                response = random.choice(self.responses)
                            self.speech_engine.respond("Got it!", new_text_flag)
                            self.speech_engine.respond(response, new_text_flag)
                            self.speech_engine.respond(random.choice(persona[2][0]), new_text_flag)

                        else:
                            time.sleep(1)
                            # Pre-canned responses
                            for response in persona[stage].values():
                                self.speech_engine.respond(random.choice(response), new_text_flag)
                        stream.start()
                        if stage == 3:
                            stage = 0 # Reset for next time
                        else:
                            stage +=1 # Advance to next stage


def video_loop(new_text_flag):
    my_vid = Video()
    my_vid.run(new_text_flag)

class Video:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX

        self.cap = cv2.VideoCapture('eye.mp4')

        self.width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.fps =  self.cap.get(cv2.CAP_PROP_FPS)

        self.word_duration = int(0.2 * self.fps)

        if AFTER_HOURS:
            self.text_color = (255,0,255)
        else:
            self.text_color = (0,0,191)

    def run(self, new_text_flag):

        sentence_flag = False

        # Read until video is completed
        while(self.cap.isOpened()):

            # Capture frame-by-frame
            ret, frame = self.cap.read()
            if ret:
                if new_text_flag.value:
                    sentence_flag = True
                    frame_count = 0

                    file = open('response', 'rb')
                    response = pickle.load(file)
                    file.close()

                    word_list = response.split()

                    new_text_flag.value = False

                if sentence_flag:
                    frame_count += 1
                    if frame_count >= self.word_duration * len(word_list):
                        sentence_flag = False
                    else:
                        word = word_list[int(frame_count/self.word_duration)]

                        # get boundary of this text
                        textsize = cv2.getTextSize(str(word), self.font, 10, 20)[0]

                        # get coords based on boundary
                        textX = int((self.width - textsize[0]) / 2)
                        textY = int((self.height + textsize[1]) / 2)

                        cv2.putText(frame, word, (textX, textY ), self.font, 10, self.text_color, 20, cv2.LINE_4)

                # Display the resulting frame
                cv2.imshow('Frame', frame)

                # Press Q on keyboard to  exit
                if cv2.waitKey(25) & 0xFF == ord('q'):
                    break
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

        # When everything done, release
        # the video capture object
        self.cap.release()

        # Closes all the frames
        cv2.destroyAllWindows()

        exit()


if __name__ == "__main__":

    mp.set_start_method('forkserver')
    #
    new_text_flag = mp.Value(c_bool, False)

    p1 = mp.Process(target=ai_loop, args=(new_text_flag, 'lemon'))
    p2 = mp.Process(target=video_loop, args=(new_text_flag,))

    p1.start()
    p2.start()

    p1.join()
    p2.join()
