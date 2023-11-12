import requests
import os
from matplotlib import image 
from matplotlib import pyplot as plt 
import json
import base64
from io import StringIO
import PIL.Image
import cv2

def encode_img(img_path):
  img = cv2.imread(img_path)
  jpg_img = cv2.imencode('.jpg', img)
  b64_string = base64.b64encode(jpg_img[1]).decode('utf-8')
  return b64_string

path_img = 'chartchecker_sample_charts/stand_your_ground.jpg'
url = "https://e2b0-34-87-78-118.ngrok-free.app/"+"/analyze/"

#with open(path_img, 'rb') as img:
name_img = os.path.basename(path_img)
img_base64 = encode_img(path_img)

files= {'image': img_base64 }
print(type(files['image']))
with requests.Session() as s:
  r = s.post(url,files=files)
  results = json.loads(r.content.decode("utf-8"))
  print(r.status_code, results['msg'])
  # print(results)
  with open("Output.json", "w") as text_file:
    text_file.write(r.content.decode("utf-8"))

clrs = ["blue","orange","green","red","purple","brown","pink","gray","olive","cyan"]
img = image.imread(path_img) 
with open("Output.json") as data:
    data = json.loads(data.read())
    if data["chart_type"] == 1:
      i = 0
      for line in data["chart_data"]:
        print("line:", i)
        for p in line:
          plt.plot(p[0], p[1], marker='v', color=clrs[i])
        i= i+1
    plt.axis('off') 
    plt.imshow(img) 
    plt.show() 

#response1 = requests.get(url)
#response2 = requests.post(url, files=files)
#print(response1.text, response2.text)

# And done.
#if response.status_code == 200:
#    print("POST request successful:", response.text)
#elif response.status_code == 400:
#    print("POST request failed with 400 Bad Request:", response.text)
#else:
#    print("POST request failed with status code:", response.status_code)
