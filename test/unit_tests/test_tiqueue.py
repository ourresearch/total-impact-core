from totalimpact.tiqueue import tiQueue
from nose.tools import assert_equals

# needs updated tests

FAKE_ITEM = { "_id": "IAmTheMockYouAreLookingFor"}

class TestQueue():
	def setUp(self):
		tiQueue.init_queue("aliases")
		tiQueue.clear()

	def test_enqueue(self):
		tiQueue.clear()
		tiQueue.enqueue("aliases", FAKE_ITEM)
		assert_equals(len(tiQueue.queued_items["aliases"]), 1)
		item_on_queue = tiQueue.queued_items["aliases"][0]
		assert_equals(item_on_queue["_id"], 'IAmTheMockYouAreLookingFor')

	def test_clear(self):
	    tiQueue.enqueue("aliases", FAKE_ITEM)
	    tiQueue.clear()
	    assert_equals(len(tiQueue.queued_items["aliases"]), 0)

	def test_dequeue(self):
		tiQueue.clear()
		print "before", tiQueue.queued_items
		tiQueue.enqueue("aliases", FAKE_ITEM)
		print "1 ", tiQueue.queued_items
		item = tiQueue("aliases").dequeue()
		print "2 ", tiQueue.queued_items
		assert_equals(item["_id"], "IAmTheMockYouAreLookingFor")
		assert_equals(len(tiQueue.queued_items["aliases"]), 0)

