from totalimpact.tiqueue import Queue
from nose.tools import assert_equals

# needs updated tests

FAKE_ITEM = { "_id": "IAmTheMockYouAreLookingFor"}

class TestQueue():
	def setUp(self):
		Queue.init_queue("aliases")
		Queue.clear()

	def test_enqueue(self):
		Queue.clear()
		Queue.enqueue("aliases", FAKE_ITEM)
		assert_equals(len(Queue.queued_items["aliases"]), 1)
		item_on_queue = Queue.queued_items["aliases"][0]
		assert_equals(item_on_queue["_id"], 'IAmTheMockYouAreLookingFor')

	def test_clear(self):
	    Queue.enqueue("aliases", FAKE_ITEM)
	    Queue.clear()
	    assert_equals(len(Queue.queued_items["aliases"]), 0)

	def test_dequeue(self):
		Queue.clear()
		print "before", Queue.queued_items
		Queue.enqueue("aliases", FAKE_ITEM)
		print "1 ", Queue.queued_items
		item = Queue("aliases").dequeue()
		print "2 ", Queue.queued_items
		assert_equals(item["_id"], "IAmTheMockYouAreLookingFor")
		assert_equals(len(Queue.queued_items["aliases"]), 0)

