# import matplotlib.pyplot as plt

# data = [1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 4, 4, 5, 6, 7, 8, 8, 8, 8, 8, 8, 9]
# # lis = set(data)
# for i in data:
#     if data.count(i) > 1:
#         print('data数组中重复的元素是%d，它的个数是%d个' % (i, data.count(i)))
# x = [i for i in range(len(data))]
# plt.scatter(x, data, c = data, cmap = plt.cm.Blues,)
# plt.show()
# a = (3,4)
# b = [9,0]
# shh = "aSUnaa"
# for i, j in enumerate(b,start=2):
#     print (i,  "is true")
#     print ("%s是第%d个" % (shh,i))
a = "1"
b = None
li = [a,b or ""] 
aa = "-".join(li)
print (aa)