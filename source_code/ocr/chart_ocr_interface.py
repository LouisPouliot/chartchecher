import requests
import os
from matplotlib import image 
from matplotlib import pyplot as plt 
from matplotlib.patches import Rectangle
import json
import itertools

DEFAULT_PATH = 'example_images\Pie_5.jpg'
backend_url = "https://0c80-34-82-26-36.ngrok-free.app/"

CLRS = ["blue","orange","green","red","purple","brown","pink","gray","olive","cyan"]
api_adress = backend_url + "/analyze/"

def send_request(img_path=DEFAULT_PATH, save_output=True):
  '''
  Sends a POST request to the backend with the image at img_path.
  If save_output is True, the response is saved to a file called "Output.json".
  response: The response from the backend
    data = {
    'msg': api response message
    'type': chart type (0: bar chart, 1: line chart, 2: pie chart)
    'data_raw': raw image coordinates of key elements depending on chart type
    'data_value': value of each element in the chart in percentage of the interval between min and max value 
    'bounding_boxes': bounding boxes of the chart elements with following numbers:
        0: Legend
        1: Y-axis label
        2: Chart title
        3: X-axis label
        4: Plot Area
        5: Inner Plot Area
    'labels': labels of the chart elements with following numbers:
        1: Y-axis label
        2: Chart title
        3: X-axis label
    'min_value': lowest value of the y-axis
    'max_value': highest value of the y-axis
    }
  return: The response from the backend
  '''
  with open(img_path, 'rb') as img:
    files= {'image': img }
    with requests.Session() as s:
      r = s.post(api_adress,files=files)
      results = json.loads(r.content.decode("utf-8"))
      print(r.status_code, results['msg'])
      if save_output:
        with open("Output.json", "w") as text_file:
          text_file.write(r.content.decode("utf-8"))
      return results
      
def generate_visualization(data, img_path=DEFAULT_PATH):
  '''
  Proof of concept function.
  Generates a visualization of the data from the response.
  '''
  img = image.imread(img_path)

  # if bar chart
  if data["type"] == 0:
    print("bar chart")
    print(data["data_raw"])
    print(data["data_value"])
    values = list(itertools.chain.from_iterable(data["data_value"]))
    i = 0
    fig, ax = plt.subplots()
    for bar in data["data_raw"]:
      delta = data["max_value"] - data["min_value"]
      width = bar[2]-bar[0]
      height = bar[1]-bar[3]
      ax.add_patch(Rectangle((bar[0], bar[3]), width, height,
                    edgecolor=CLRS[i],
                    fill=False))
      plt.plot(bar[0], bar[1], marker='v', color=CLRS[i])
      plt.plot(bar[2], bar[3], marker='v', color=CLRS[i])
      plt.text(bar[0]+(width/2),
              bar[3]+(height/2),
              round(data["min_value"] + (delta * values[i]), 2),
              color=CLRS[i],
              ha='center')
      i= i+1

  # if line chart
  if data["type"] == 1:
    print("line chart")
    print(data["data_value"])
    print(data['min_value'])
    print(data['max_value'])
    #data["max_value"] = 0.06
    #data["min_value"] = 0
    delta = data["max_value"] - data["min_value"]
    
    i = 0
    for line in data["data_raw"]:
      print("line:", i)
      j = 0

      for p in line:
        plt.plot(p[0], p[1], marker='v', color=CLRS[i])
        plt.text(p[0],p[1],
              round(data["min_value"] + (delta * data["data_value"][0][j]), 2),
              color=CLRS[i],
              ha='center',
              va='bottom')
        j = j + 1

      i= i+1

  plt.axis('off') 
  plt.imshow(img) 
  plt.savefig(os.path.basename(img_path)+'.pdf')
  plt.show() 

def set_url(url):
  '''
  Set the backend_url to url
  '''
  global backend_url
  backend_url = url
  global api_adress
  api_adress = backend_url + "/analyze/"


if __name__ == "__main__":

  # example usage of the send_request function with data visualization

  data = send_request()

  generate_visualization(data)
  

      