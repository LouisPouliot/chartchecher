import requests
import os
from matplotlib import image 
from matplotlib import pyplot as plt 
from matplotlib.patches import Rectangle
import json

path_img = 'chartchecker_sample_charts/TruncatedAxisBARCHART.png'
url = "https://eb36-34-147-68-230.ngrok-free.app"+"/analyze/"

with open(path_img, 'rb') as img:
  name_img= os.path.basename(path_img)
  files= {'image': img }
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
    if data["type"] == 0:
      print("bar chart")
      print(data["data_raw"])
      print(data["data_value"])
      i = 0
      fig, ax = plt.subplots()
      for bar in data["data_raw"]:
        spielraum = data["max_value"] - data["min_value"]
        width = bar[2]-bar[0]
        height = bar[1]-bar[3]
        ax.add_patch(Rectangle((bar[0], bar[3]), width, height,
                      edgecolor=clrs[i],
                      fill=False))
        plt.plot(bar[0], bar[1], marker='v', color=clrs[i])
        plt.plot(bar[2], bar[3], marker='v', color=clrs[i])
        plt.text(bar[0]+(width/2),
                 bar[3]+(height/2),
                 round(data["min_value"] + (spielraum * data["data_value"][0][i]), 2),
                 color=clrs[i],
                 ha='center')
        i= i+1
    if data["type"] == 1:
      print("line chart")
      print(data["data_raw"])
      i = 0
      for line in data["data_raw"]:
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
