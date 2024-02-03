import requests
import os
from matplotlib import image 
from matplotlib import pyplot as plt 
from matplotlib.patches import Rectangle
import json

default_img_path = 'chartchecker_sample_charts/TruncatedAxisBARCHART.png'
backend_url = "https://eb36-34-147-68-230.ngrok-free.app"

data = {} # variable to store the data from the response

CLRS = ["blue","orange","green","red","purple","brown","pink","gray","olive","cyan"]
API_ADRESS = backend_url + "/analyze/"

def send_request(img_path=default_img_path, save_output=True):
  '''
  Sends a POST request to the backend with the image at img_path.
  If save_output is True, the response is saved to a file called "Output.json".
  saves the data in variable data
  response: The response from the backend
    data = {
    'msg': api response message
    'type': chart type (0: bar chart, 1: line chart, 2: pie chart)
    'data_raw': raw image coordinates of key elements depending on chart type
    'data_value': percentage of the value of each element in the chart
    'bounding_boxes':
    'labels':
    'min_value':
    'max_value':
    }
  '''
  with open(img_path, 'rb') as img:
    files= {'image': img }
    with requests.Session() as s:
      r = s.post(API_ADRESS,files=files)
      results = json.loads(r.content.decode("utf-8"))
      print(r.status_code, results['msg'])
      if save_output:
        with open("Output.json", "w") as text_file:
          text_file.write(r.content.decode("utf-8"))
      global data
      data = results
      

if __name__ == "__main__":

  # example usage of the send_request function with data visualization

  send_request()
  
  img = image.imread(default_img_path) 
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
                        edgecolor=CLRS[i],
                        fill=False))
          plt.plot(bar[0], bar[1], marker='v', color=CLRS[i])
          plt.plot(bar[2], bar[3], marker='v', color=CLRS[i])
          plt.text(bar[0]+(width/2),
                  bar[3]+(height/2),
                  round(data["min_value"] + (spielraum * data["data_value"][0][i]), 2),
                  color=CLRS[i],
                  ha='center')
          i= i+1
      if data["type"] == 1:
        print("line chart")
        print(data["data_raw"])
        i = 0
        for line in data["data_raw"]:
          print("line:", i)
          for p in line:
            plt.plot(p[0], p[1], marker='v', color=CLRS[i])
          i= i+1
      plt.axis('off') 
      plt.imshow(img) 
      plt.show() 