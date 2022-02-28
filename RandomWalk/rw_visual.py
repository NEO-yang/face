import matplotlib.pyplot as plt

from random_walk import RandomWalk

rw = RandomWalk()
rw.fill_walk()
# plt.scatter(rw.x_values, rw.y_values, s=15)
# plt.show()
point_numbers = list(range(rw.num_points))
plt.scatter(rw.x_values, rw.y_values, c=point_numbers, cmap=plt.cm.Blues,
edgecolor='none', s=5)
plt.scatter(0, 0, c='green', edgecolors='none', s=100)
plt.scatter(rw.x_values[-1], rw.y_values[-1], c='red', edgecolors='none',
s=100)
plt.show()