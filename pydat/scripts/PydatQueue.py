import json
from multiprocessing import Queue, JoinableQueue
import Queue as queue   #required for queue.empty exception
import random
import redis
import sys
from time import sleep

#testing
import logging
logging.basicConfig(filename='es_script_testing.log', level = logging.DEBUG)
logger = logging.getLogger(__name__)

REDIS_LIST_ID_MAX = 100000000000

class PydatQueue:
	
	def factory(type, name= None,  args = None):
		#Testing
		#logger.debug("creating %s queue" % type)
		if type == "python-queue":
			return Queue()
		if type == "python-joinable-queue":
			return JoinableQueue(maxsize= args['maxsize'])
		if type == "redis":
			return RedisQueue(name, **args)
		assert 0, "Bad queue creation: " + type

	factory = staticmethod(factory)

	

'''
interface for redis API

-as redis does not implement a complete queue API, this class serves as 
a wrapper to the redis api in order to provide all queue functionality 
required by the scipt (basically mimic all functionality provided by
python multiprocessing queues)

Arguments are passed via a dictionary. They are:

	'serialize' : True | False (if the item type to be put into the queue is a dict, list, or other object that needs to be serialized; i.e. not a string or number)
	'host' :  IP address of redis instance (direct argument to actual redis api)
	'port' :  port of redis instance (direct argument to actual redis api)
	'db' :    db of the redis instance , if specified (direct argument to actual redis api)
	'unix_socket_path':  unix domain socket path to use for redis instance (direct argument to actual redis api)

'''
class RedisQueue:
	def __init__(self, name = None,  db=0, host='127.0.0.1', port='6379', redis_con_type = 'unix', unix_socket_path = None):
		self.redis_list_id = random.randint(0, REDIS_LIST_ID_MAX)
		self.name  = name
		if redis_con_type =='host':
			self.redis_instance = redis.StrictRedis(host=host, port= port, db=db)
		elif redis_con_type == 'unix':
			self.redis_instance = redis.StrictRedis(unix_socket_path= unix_socket_path)
		else:
			err = "Could not create Redis queue, not enough arguments"
			sys.stdout.write(err)

	'''signal the closing and no longer need for the queue for the
	   calling process

	   redis has no equivalent so no effect
	'''
	def close(self):
		pass


	'''check if queue is empty'''
	def empty(self):
		#Testing
		#logger.debug("calling redis empty()")
		return True if self.redis_instance.llen(self.redis_list_id)==0 else False


	'''blocking queue get call'''
	def get(self, block = True, timeout = 0):
		item = self.redis_instance.brpop([self.redis_list_id], timeout = timeout)
		#Testing
		#logger.debug("Queue %s - %s: get() call:", self.name, self.redis_list_id)
		if item == None:
			#if queue is empty, raise exception that the script is expecting if condition occurs
			raise queue.Empty   
		else:
			#brpop returns a tuple (list_key, item), grab the item
			item= item[1]
			#deserialize item if need be, as script is expecting string, dict or list
			try:
				#Testing
				#logger.debug("   -get() - item returned is of type %s and is: %s", type(item), item)
				item = json.loads(item)
			except ValueError:
				pass
			return item


	'''non-blocking queue get call'''
	def get_nowait(self):	
		item = self.redis_instance.rpop(self.redis_list_id)
		
		#Testing
		#logger.debug("Queue %s-%s: item getting back from get_nowait(): %s ", self.name, self.redis_list_id, item)
		
		if item == None:
			#if queue is empty, raise exception that the script is expecting if condition occurs
			raise queue.Empty   
		else:
			#deserialize item if need be, as script is expecting string, dict or list
			try:
				item = json.loads(item)
			except ValueError:
				pass
			return item

	'''blocking join call'''
	def join(self):
		'''TODO: this is a crude polling hack to mimic join() for redis, try to make better'''
		while self.redis_instance.llen(self.redis_list_id) != 0:
			sleep(.1)
		return


	'''blocking queue put call'''
	def put(self, item):
		#Testing
		#logger.debug("Queue %s - %s: put item " , self.name, self.redis_list_id)
		
		#make all items(inserted into queue) a serialized string
		if type(item) is not str:
			item = json.dumps(item)
		return self.redis_instance.lpush(self.redis_list_id, item)


	'''non-blocking task_done signal call to queue
		
		redis does not have an equivalent so no effect
	'''
	def task_done(self):
		pass





