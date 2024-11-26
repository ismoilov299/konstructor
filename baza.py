import speech_recognition as sr
import moviepy.editor as mp

# Video faylni yuklang
video_path = '1161180912_An8TKuCkzl5KB8ReaIGHVwFnTCRyzbDIlkGuiWUPJSpNMasbqYgHqt.mp4'
video = mp.VideoFileClip(video_path)

# Audioni chiqarib oling
audio_path = 'audio.wav'
video.audio.write_audiofile(audio_path, codec='pcm_s16le')

# Tanib olish uchun recognizer ob'yektini oling
recognizer = sr.Recognizer()

# Audioni yuklang va ovozni matnga aylantiring
with sr.AudioFile(audio_path) as source:
    audio = recognizer.record(source)
    text = recognizer.recognize_google(audio, language="uz-UZ")
    print("Transkripsiya:", text)
