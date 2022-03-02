import threading
import asyncio

@asyncio.coroutine
def hello():
  print("hello world (%s)" % threading.currentThread())
  yield from asyncio.sleep(2)
  print("hello again (%s)" % threading.currentThread())

@asyncio.coroutine
def hello2():
  print("hello2 world (%s)" % threading.currentThread())
  yield from asyncio.sleep(2)
  print("hello2 again (%s)" % threading.currentThread())

@asyncio.coroutine  
def hello1():
  print("hello1 world (%s)" % threading.currentThread())
  yield from hello2()
  print("hello1 again (%s)" % threading.currentThread())
loop=asyncio.get_event_loop()
tasks=[hello(),hello1()]
loop.run_until_complete(asyncio.wait(tasks))
loop.close()