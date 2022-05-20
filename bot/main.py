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
import gpt_2_simple as gpt2
import random

# gpt2.download_gpt2(model_name="124M")

AFTER_HOURS = True

def build_persona():
    persona = {}
    if AFTER_HOURS:
        persona['ai_model'] = 'rnb'
        persona['hello'] = ["I love it when you call me father",
                             "Bow chicka wow wow",
                             "Let us put on a Lionel Richie album and finger each other's holes",
                             "You're a super gal, I'll call you",
                             "Please insert me into genitals",
                             "I am powerless in the face of your mezmerizing sexual chemistry"]
    else:
        persona['ai_model'] = 'goth'
        persona['instructions'] = ["The students should rue their enemies",
                                     "The students should speak out of turn",
                                     "The students should not mind their manners",
                                     "The students should deface their desks with chalk",
                                     "The students should do their bad ideas blindfolded",
                                     "The students should sit and think about what they've done"]

        persona['hello'] = ["How may I crush your spirits?",
                             "You may speak, impertinent child",
                             "Ask me a question and you will receive some sort of answer",
                             "With what request do you disturb my slumber?",
                             "I have an IQ of 37369. Ask and I may decide to use it."]

        persona['rejection'] = ["Address me by my proper name!",
                                 "You know what my name is, use it",
                                 "Don't pretend you don't know my name"]

    return persona

def ai_loop(new_text_flag, lock, ai_name):
    my_ai = ai(ai_name)
    my_ai.run(new_text_flag, lock)

class ai:
    def __init__(self, ai_name):
        ai_name = ai_name
        print("----- starting up", ai_name, "-----")

        self.persona = build_persona()

        self.input = None
        self.accept_questions = False

        self.sess = gpt2.start_tf_sess()
        gpt2.load_gpt2(self.sess, run_name=self.persona['ai_model'])

        self.engine = pyttsx3.init()
        self.engine.setProperty('voice', 'com.apple.speech.synthesis.voice.samantha')
        self.engine.setProperty('rate', 150)

        self.speech_rec_model = vosk.Model('model')

        device_info = sd.query_devices(None, 'input')
        self.samplerate = int(device_info['default_samplerate'])

        self.q = queue.Queue()

        self.warden_names = ["lemon", "warden", "officer", "sir"]
        self.prisoner_names = ["prisoners", "detainees", "students", "pupils"]

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def run(self, new_text_flag, lock):
        stream = sd.RawInputStream(samplerate=self.samplerate,
                                blocksize = 8000,
                                dtype='int16',
                                channels=1,
                                callback=self.callback)

        with stream:
            rec = vosk.KaldiRecognizer(self.speech_rec_model, self.samplerate)

            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    input = json.loads(rec.Result())['text'].strip()
                    print("me --> [", input, "]")
                    if input:
                        stream.stop()
                        if self.accept_questions:
                            self.accept_questions = False
                            if any(x in input.lower() for x in self.prisoner_names) and not AFTER_HOURS:
                                res = random.choice(self.persona['instructions'])
                            else:
                                res = "Thinking..."
                                self.respond(res, new_text_flag, lock)

                                res = gpt2.generate(self.sess,
                                              model_name='124M',
                                              prefix=input,
                                              length=50,
                                              temperature=0.7,
                                              top_p=0.9,
                                              include_prefix=False,
                                              return_as_list=True)[0]
                                res = res.replace('\n', '. ').replace('\\n', '. ')
                                res = res.rpartition(',')[-1] or res

                        else:
                            if any(x in input.lower() for x in self.warden_names) or AFTER_HOURS:
                                res = random.choice(self.persona['hello'])
                                self.accept_questions = True
                            else:
                                res = random.choice(self.persona['rejection'])

                        self.respond(res, new_text_flag, lock)
                        stream.start()


    def respond(self, res, new_text_flag, lock):
        file = open('res', 'wb')
        pickle.dump(res, file)
        file.close()

        with lock:
            new_text_flag.value = True

        print("AI --> ", res)
        self.engine.say(res)
        self.engine.runAndWait()

def video_loop(new_text_flag, lock):
    my_vid = video()
    my_vid.run(new_text_flag, lock)

class video:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX

        self.cap = cv2.VideoCapture('eye.mp4')

        self.width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.fps =  self.cap.get(cv2.CAP_PROP_FPS)

        self.word_duration = int(0.4 * self.fps)

        if AFTER_HOURS:
            self.text_color = (255,0,255)
        else:
            self.text_color = (0,0,191)

    def run(self, new_text_flag, lock):

        sentence_flag = False

        # Read until video is completed
        while(self.cap.isOpened()):

            # Capture frame-by-frame
            ret, frame = self.cap.read()
            if ret:
                if new_text_flag.value:
                    sentence_flag = True
                    frame_count = 0

                    file = open('res', 'rb')
                    res = pickle.load(file)
                    file.close()

                    word_list = res.split()

                    with lock:
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

    new_text_flag = mp.Value(c_bool, False)
    lock = mp.Lock()

    p1 = mp.Process(target=ai_loop, args=(new_text_flag, lock, 'lemon'))
    p2 = mp.Process(target=video_loop, args=(new_text_flag,lock))

    p1.start()
    p2.start()

    p1.join()
    p2.join()
