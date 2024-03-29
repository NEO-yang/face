from multiprocessing import Process,Queue


import os,time,random
def write(q):
    print("process to write: %s" % os.getpid())
    for value in ["A", "B", "C"]:
        print("put %s to queue..." % value)
        q.put(value)
        time.sleep(10)
  
def read(q):
    print("process to read: %s" % os.getpid())
    while True:
        value = q.get(True)
        print("get %s to queue..." % value)

if __name__=='__main__':
    q=Queue()
    pw=Process(target=write,args=(q,))
    pr=Process(target=read,args=(q,))
    pw.start()
    pr.start()
    pw.join()
    pr.terminate()