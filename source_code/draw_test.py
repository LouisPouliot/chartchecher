from matplotlib import image 
from matplotlib import pyplot as plt 
import json
  
# to read the image stored in the working directory 
img = image.imread('chartchecker_sample_charts/InconsistentAxisExample1.png') 
  
# to draw first line from (100,400) to (500,100) 
# to draw second line from (150,100) to (450,400) 
with open("Output.json") as data:
    data = json.loads(data.read())
    points = data["chart_data"][0]
    i = 0
    for p in points:
        print(i)
        i= i+1
        plt.plot(p[0], p[1], marker='v', color="black")
    plt.axis('off') 
    plt.imshow(img) 
    plt.show() 
