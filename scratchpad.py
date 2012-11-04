import threading, Queue, time, random

class Tools():

    def __init__(self, foo):
        self.foo = foo

    def add_stuff(self, val_to_add, q):
        print "starting add_stuff"
        while True:
            item = q.get()
            print "got item: ", str(item)
            ts = str(time.time()).split(".")[1]

            time.sleep(random.random())
            item[ts] = self.fooify(val_to_add)
            print "i added ", val_to_add, "to item."
            q.task_done()

    def fooify(self, input):
        return self.foo + str(input)




my_queue = Queue.Queue()
item = {}
tools = Tools("myfoo")

worker = threading.Thread(target=tools.add_stuff, args=(1, my_queue))
worker2= threading.Thread(target=tools.add_stuff, args=(2, my_queue))
worker.start()
worker2.start()
for i in range(1,10):
    my_queue.put(item)

time.sleep(1)
print "done sleeping"
my_queue.join()
print "donezo. here's item: "
print item

