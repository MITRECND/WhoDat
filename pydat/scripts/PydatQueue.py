'''
PydatQueue class - a utility class that serves as an interface to different interprocess communication libraries
					
					solely used by the python script "es_populate_script.py"

					the "es_populate_script.py" script uses this interface to create and utilize 
					1)Multiprocessing.Queue and Multiprocessing.JoinableQueue (python)   or
					2) Redis linked lists

					within "es_populate_script.py", it has the option to be run with 1) or 2). This module
					allows for the script to use 1) or 2) via the same API calls defined in this module.

'''
import json
from multiprocessing import Queue, JoinableQueue
import Queue as queue   #required for queue.empty exception
import random
import redis
import sys

REDIS_LIST_ID_MAX = 100000000000

class PydatQueue:
	def __init__(queue_type, args):
		self.queue_type = queue_type

		if queue_type == "python":
			self.queue = Queue(maxsize = args['maxsize'])
		else if queue_type == "python_joinable":
			self.queue = JoinableQueue(maxsize = args['maxsize'])
		else if queue_type == "redis_list_unix":
			self.redis_instance = redis.StrictRedis(unix_socket_path = args['unix_socket_path'])
			self.redis_list_id = random.randint(0, REDIS_LIST_ID_MAX)
		else if queue_type == "redis_list_tcp":
			self.redis_instance = redis.StrictRedis(host = args['host'], port = args['port'] , db = args['db'])
			self.redis_list_id = random.randint(0, REDIS_LIST_ID_MAX)
	


	'''signal the closing and non longer need for the queue for the calling process

		ONLY for python queues. No effect for calls by redis lists

	'''
	def close(self):
		if "python" in self.queue_type:
			return self.queue.close()
		else if "redis" in self.queue_type:
			return
		else:
			err = "PydatQueue.clean() has no effect for the specified queue type ({0}}. Error: queue type \"{0}\" is not recoginized".format(self.queue_type)
			sys.stdout.write(err)
			return



	'''check if queue is empty

		redis- the correlating API call for a redis list is llen(), thus the request is converted and passed to redis instance

	'''
	def empty(self):
		if "python" in self.queue_type:
			return self.queue.empty()
		else if "redis" in self.queue_type:
			return True if self.queue.llen(self.redis_list_id)==0 else False
		else:
			err = "PydatQueue.empty() has no effect for the specified queue type ({0}}. Error: queue type \"{0}\" is not recoginized".format(self.queue_type)
			sys.stdout.write(err)
			return



	'''blocking queue get call
		
		redis: when a redis list is the queue object, the redis API call is interpreted and converted 
			   to what the es_populate_script is expecting. Specifically, if the queue is empty, 
			   the script is looking for a Queue.Empty exception, we artificially raise it when a 
			   redis list is empty.
	''' 
	def get(self):
		if "python" in self.queue_type:
			return self.queue.get()
		else if "redis" in self.queue_type:
			item = self.redis_instance.rpop(self.redis_list_id)
			if item == "nil":
				#if queue is empty, raise exception that the script is expecting if condition occurs
				raise queue.Empty   
			else:
				#deserialize item, as script is expecting string, dict or list
				return json.loads(item)
		else:
			err = "PydatQueue.get() has no effect for the specified queue type ({0}}. Error: queue type \"{0}\" is not recoginized".format(self.queue_type)
			sys.stdout.write(err)
			return



	'''non-blocking get call
		
		redis: when a redis list is the queue object, the redis API call is interpreted and converted 
			   to what the es_populate_script is expecting. Specifically, if the queue is empty, 
			   the script is looking for a Queue.Empty exception, we artificially raise it when a 
			   redis list is empty.
	''' 
	def get_nowait(self):
		if "python" in self.queue_type:
			return self.queue.get_nowait()
		else if "redis" in self.queue_type:
			item = self.redis_instance.rpop(self.redis_list_id)
			if item == "nil":
				#if queue is empty, raise exception that the script is expecting if condition occurs
				raise queue.Empty   
			else:
				#deserialize item, as script is expecting string, dict or list
				return json.loads(item)
		else:
			err = "PydatQueue.get_nowait() has no effect for the specified queue type ({0}}. Error: queue type \"{0}\" is not recoginized".format(self.queue_type)
			sys.stdout.write(err)
			return



	'''blocking join call

		ONLY FOR Python JoinableQueue and Redis

		redis: since the redis API does not have this method, we mimic a join with a busy-wait 
		until the redis list is empty
	'''
	def join(self):
		if "python_joinable" in self.queue_type:
			return self.queue.join()
		else if "redis" in self.queue_type:
			'''TODO: this is a crude polling hack to mimic join() for redis, try to make better'''
			while self.redis_instance.llen(self.redis_list_id) != 0:
				pass
			return
		else:
			err = "PydatQueue.join() has no effect for the specified queue type ({0}}. join() is not a valid API call for queue type \"{0}\"".format(self.queue_type)
			sys.stdout.write(err)
			return



	'''blocking queue put call

		redis: when a redis list is the queue object, the put call will insert the item
			   into a linked list (from the left) 
	'''
	def put(self, item):
		#python Queue and Joinable Queue API
		if "python" in self.queue_type:
			return self.queue.put(item)
		#redis API
		else if "redis" in self.queue_type:
			#make all items(inserted into queue) a serialized string
			if type(item) is not str:
				item = json.dumps(str)
			return self.redis_instance.lpush(self.redis_list_id, item)
		else:
			err = "PydatQueue.put() has no effect for the specified queue type ({0}}. Error: queue type \"{0}\" is not recoginized".format(self.queue_type)
			sys.stdout.write(err)
			return



	'''non-blocking task_done signal call to queue
		
		ONLY FOR Python Queue and JoinableQueue
	'''
	def task_done(self):
		if "python" in self.queue_type:
			return self.queue.task_done()
		else if "redis" in self.queue_type:
			err = "PydatQueue.task_done() has no effect for the specified queue type({0}). task_done() is not a valid API call for queue type \"{0}\"".format(self.queue_type)
			sys.stdout.write(err)
			return
		else:
			err = "PydatQueue.task_done() has no effect for the specified queue type ({0}}. Error: queue type \"{0}\" is not recoginized".format(self.queue_type)
			sys.stdout.write(err)
			return



