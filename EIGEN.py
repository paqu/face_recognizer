#!/usr/bin/python
import cv2, os
import numpy as np
import logging
import inotify.adapters
import re
import json
import requests
import sys

from time import sleep
from PIL  import Image

LOGGER = logging.getLogger(__name__)

SIZE = (135,135)

def getId(path):
    _id = int(os.path.split(path)[1]
        .split(".")[0]
        .replace("subject", ""))

    return _id

def preparePic(path):
    image_pil = Image.open(path).convert('L')
    image = np.array(image_pil, 'uint8')
    equ = cv2.equalizeHist(image)

    return equ; 


def lookForFaces(pic, face_cascade):
    
    faces = face_cascade.detectMultiScale(pic)

    return faces


def getTrainingSet(path, cascade):
    image_paths = [os.path.join(path, f) for f in os.listdir(path)]

    images = []
    labels = []

    for image_path in image_paths:
        
        person_id    = getId(image_path)
        prepared_pic = preparePic(image_path)
        faces        = lookForFaces(prepared_pic, cascade)

        for (x, y, w, h) in faces:
            resized = cv2.resize(prepared_pic[y: y + h, x: x + w],SIZE)
            images.append(resized)
            labels.append(person_id)

    return images, labels


def checkArgs(args):
    if len(sys.argv) != 3:
        print "Pass all arguments !!!"
        print "./{} face_database_path faces_to_recognize".format(sys.argv[0])
        sys.exit()


def configInit(args):
    config = {
            "faces_database"     : args[1],
            "faces_to_recognize" : args[2],
            "treshold"           : 80,
            "server_url"         : 'http://127.0.0.1:1234/api/wanted'
            }

    return config

def getFaceCascade():
    cascadePath = "haarcascade_frontalface_default.xml"

    return cv2.CascadeClassifier(cascadePath)

def traingPhase(images, labels):
    recognizer  = cv2.face.createEigenFaceRecognizer()
    recognizer.train(images, np.array(labels))
    print("END TRANING PHASE");

    return recognizer

def getPayload(person_id, chanel, date, time):
    payload = {
           'recognized_person':person_id,
           'chanel':chanel,
           'date':date,
           'time':time
            }

    return payload

def prepareDataToSend(person_id, chanel, date, time):
    payload = getPayload(person_id, chanel, date, time)
    
    print("send to server:")
    print(payload);

    return json.dumps(payload)

def getHeader(): 
    header = {
        'Content-type': 'application/json',
        'Accept': 'text/plain'
        }
    return header 


def watcherInit(path_to_watch):
    i = inotify.adapters.Inotify()
    i.add_watch(path_to_watch)
    
    return i

def isRecognized(treshold, nbr_predicted, confidence):
    print("Recognized:{} with confidence {} ".format(
        nbr_predicted, confidence))

    if (confidence > treshold):
        nbr_predicted = 'not_recognized'

    return nbr_predicted


if __name__ == '__main__':

    checkArgs(sys.argv)

    config         = configInit(sys.argv)
    face_cascade   = getFaceCascade()
    images, labels = getTrainingSet(config["faces_database"], face_cascade)
    recognizer     = traingPhase(images,labels)
    watcher        = watcherInit(config["faces_to_recognize"])

    try:
        for event in watcher.event_gen():
            if event is not None:
                (header, type_names, watch_path, filename) = event

                if (re.match(r'(.*)jpg$',filename.decode('utf-8'))
                    and type_names == ["IN_CREATE"]):

                    image_path = watch_path.decode('utf-8') + '/' 
                    image_path += filename.decode('utf-8')

                    tmp = os.path.split(image_path)[1].split('.')
                    sleep(0.1)
                    try:
                        prepared_pic = preparePic(image_path)
                        faces        = lookForFaces(prepared_pic, face_cascade)

                        for (x, y, w, h) in faces:
                            resized = cv2.resize(prepared_pic[y: y + h, x: x + w],SIZE)
                            nbr_predicted, confidence = recognizer.predict(
                                    resized)

                            person_id  = isRecognized(config["treshold"],
                                    nbr_predicted,
                                    confidence)

                            url     = config['server_url']
                            headers = getHeader()
                            data    = prepareDataToSend(person_id, tmp[0], tmp[1], tmp[2]) 

                            r = requests.post(url, headers=headers, data=data)
                        try:
                            os.remove(image_path)
                        except OSError as oserr:
                            print("OS error: {0}".format(oserr))
                    except IOError as ioerr:
                        print("OS error: {0}".format(ioerr))

    finally:
        watcher.remove_watch(config['faces_to_recognize'])
