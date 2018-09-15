from data_loader import DataLoader
from matplotlib import pyplot as plt
from collections import OrderedDict
import heapq


##################################
# --------Initialisation-------- #
##################################

test = DataLoader('messages')
data = test.message_dict

new = {}
for key in data.keys():
    new[key] = len(data[key]['messages'])

largest = heapq.nlargest(50, new, key=new.get)

x = []
y = []
for key in largest:
    x.append(key)
    y.append(new[key])

#######################
# --------Run-------- #
#######################

print(largest)

plt.bar(range(len(x)), list(map(float, y)))
plt.xticks(range(len(x)), x, rotation=90)
plt.show()
