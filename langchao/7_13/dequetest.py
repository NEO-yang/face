from collections import deque

q = deque(['a','b','c'])
q.append('x')
q.appendleft('m')
print(q)