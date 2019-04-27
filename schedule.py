from random import randint
from datetime import datetime
import json
import threading
import time
import os
import glob
import hashlib
import subprocess

class ChannelSchedule:
	supported_extensions = [
		"3gp", "asf", "wmv", "asf", "wmv","au","avi","flv","mov","mp4","ogm", "ogg","mkv", "mka",
		"ts", "mpeg","mpg", "mp3", "mp2", "nsc", "nsv", "nut", "ra", "ram", "rm", "rv", "rmbv",
		"a52", "dts", "aac", "flac", "dv", "vid", "tta", "tac", "ty", "wav", "dts","xa"
	]
	seconds_in_minute = 60
	seconds_in_hour = 3600
	seconds_in_day = 86400
	
	
	def __init__(self, channel_data_file):
		self.config_filename = channel_data_file
		
		config = json.loads(open(self.config_filename,"r").read())
		self.name = config["name"]
		self.icon = config["icon"]
		self.path = config["path"]
		self.rules = config["rules"]
		
		self.store_id = md5(self.config_filename)
		self.store_filename = "store/%s.json" % self.store_id
		self.schedule_filename = "store/%s_schedule.json" % self.store_id
		
		try:
			self.programme_data = json.loads(open(self.store_filename,"r").read())
		except:
			self.programme_data = []
			
		try:
			self.schedule_data = json.loads(open(self.schedule_filename,"r").read())
		except:
			self.schedule_data = []
		
		
		
		self.poll = True
		
		self.subscribers = []
		
		#self.programme_data["schedule"] = [] #XXX DELETE
		
		self.lock = threading.Lock()
		thread = threading.Thread(target=self.poll_files)
		thread.start()
		
	def listen(self, cbfunc):
		print("LISTEN %s" % cbfunc)
		self.subscribers.append(cbfunc)
		
	def trigger(self, event):
		print("TRIGGER %s" % event)
		for s in self.subscribers:
			s(event, self)
			
	def get_schedule(self):
		output = []
		#self.lock.acquire()
		for sch in self.schedule_data:
			programmes = self.find({"episode":{"id":sch["episode_id"]}})
			if len(programmes) > 0:
				output.append({"time":sch["start"], "programme":programmes[0]})
		#self.lock.release()
		return output
		
	def get_at_time(self, time):
		for sch in self.schedule_data:
			if sch["start"] <= time and sch["end"] >= time:
				programmes = self.find({"episode":{"id":sch["episode_id"]}})
				if len(programmes) > 0:
					return {"time":sch["start"], "programme":programmes[0]}
		return None
		
	def update(self, id, updates):
		self.lock.acquire()
		for programme in self.programme_data:
			if programme["id"] == id:
				programme = {**programme, **updates}
				self.lock.release()
				return programme
			else:
				for i, episode in enumerate(programme["episodes"]):
					if episode["id"] == id:
						programme["episodes"][i] = {**episode, **updates}
						self.lock.release()
						return episode
						
		self.lock.release()
		return None
		
	def find(self, query, programme_limit=0, collection=None):
		"""Uses query to return a list of episodes"""
		if collection is None:
			selection = clone(self.programme_data)
		else:
			selection = clone(collection)
		
		#Apply programme filter
		if "programme" in query:
			delete_keys = []
			for q in query["programme"]:
				key = strip_operators(q)
				for programme in selection:
					if key in programme:
						if match_key(key, programme[key], query["programme"][q]):
							pass
						else:
							delete_keys.append(programme)
					else:
						delete_keys.append(programme)
					
			for delete in delete_keys:
				selection.remove(delete)
				
		#Apply episode filter
		if "episode" in query:
			for q in query["episode"]:
				key = strip_operators(q)
				for programme in selection:
					delete_keys = []
					for episode in programme["episodes"]:
						if key in episode:
							if not match_key(q, episode[key], query["episode"][q]):
								delete_keys.append(episode)
						else:
							delete_keys.append(episode)
					
					for delete in delete_keys:
						programme["episodes"].remove(delete)
						
		#Limit programme count
		if programme_limit > 0 and len(selection) >= programme_limit:
			sel_limit = []
			tries = 0
			while len(sel_limit) < programme_limit and tries < 256:
				tries += 1
				p = randlist(selection)
				if not p in sel_limit and len(p["episodes"]) > 0:
					sel_limit.append(p)
			selection = sel_limit
			
		#Remove programmes with no episodes
		delete_keys = []
		for programme in selection:
			if len(programme["episodes"]) <= 0:
				delete_keys.append(programme)
		for delete in delete_keys:
			selection.remove(delete)
				
		return selection
		
	def get_episode(self, query={"next":"series","query":{}}, max_length=1, collection=None, exclusion=[]):
		if collection is None:
			collection = self.find(query["query"])
			
		episodes = self.flatten(collection)

		output = None
		
		if query["next"] == "series":
			next = None
			for episode in episodes:
				if episode["id"] in exclusion:
					pass
				elif episode["date_watched"] == 0:
					next = episode
					break
				elif next is None or episode["date_watched"] < next["date_watched"]:
					next = episode
			if next is not None:
				output = next
		if query["next"] == "random":
			if len(episodes) > 0:
				output = episodes[randint(0, len(episodes)-1)]
				
		return output
					
	def build_schedule(self, count=8):
		self.clean_schedule()
	
		segment = 900 #15 minutes
		maxrange = 60*60*48 #Can only plan for two days
		now = int( datetime.now().timestamp() )
		#self.lock.acquire()
		
		#self.schedule_data = [] #clears whole schedule for debugging
		schedule = self.schedule_data
		
		ids = []
		for s in schedule:
			ids.append(s)
			
		for rule in self.rules:
			time = ChannelSchedule.nearest_date_from_string(rule["when"]["day"], rule["when"]["time"])
			if time > now + maxrange:
				continue
			
			programmes = self.find(rule["query"], programme_limit=1)
			episode = self.get_episode(query={"next":rule["next"],"query":{}},collection=programmes, exclusion=ids)
			if episode is not None:
				sch = {"episode_id":episode["id"], "start":time,"end":time+episode["runtime"],"name":episode["name"]}
				if self.schedule_free(sch):
					schedule.append(sch)
					ids.append(sch["episode_id"])

		
		
		#add random programmes
		for i in range(count):
			curr = now - (now % segment)
			programmes = self.find({}, programme_limit=1)
			episode = self.get_episode(collection=programmes, exclusion=ids)
			if episode is not None:
				sch = {"episode_id":episode["id"], "start":curr,"end":curr+episode["runtime"],"name":episode["name"]}
				added = False
				while not added:
					sch["start"] = curr
					sch["end"] = curr + episode["runtime"]
					
					if self.schedule_free(sch):
						schedule.append(sch)
						ids.append(sch["episode_id"])
						added = True
						curr = sch["end"] + segment
						curr = curr - (curr % segment)
					elif curr > now + maxrange:
						print("Exceeded time limit!")
						break
					else:
						curr += segment
						
		#self.lock.release()
		self.trigger("schedule.update")
		print("Schedule updated!")
		return schedule
			
	def clean_schedule(self):
		"""Removes all scheduled programmes before now"""
		now = int( datetime.now().timestamp() )
		delete_keys = []
		for sch in self.schedule_data:
			if sch["end"] < now:
				delete_keys.append(sch)
			if len(self.find(query={"episode":{"id" : sch["episode_id"]} })) <= 0:
				delete_keys.append(sch)
				
		for delete in delete_keys:
			self.schedule_data.remove(delete)
			
	def schedule_free(self, c):
		for s in self.schedule_data:
			if (
				s["start"] >= c["start"] and
				s["start"] < c["end"]
			) or (
				c["start"] >= s["start"] and
				c["start"] < s["end"]
			):
				return False
		return True
			
		
	def save(self):
		self.lock.acquire()
		try:
			file1 = open(self.store_filename,"w")
			file1.write(json.dumps(self.programme_data, indent=4,))
			file1.close()
		except:
			print("Unable to write to file %s" % self.store_filename)
			
		try:
			file2 = open(self.schedule_filename,"w")
			file2.write(json.dumps(self.schedule_data, indent=4,))
			file2.close()
		except:
			print("Unable to write to file %s" % self.schedule_data)
		
		self.lock.release()
			
	def poll_files(self):
		if self.poll:
	
			file_list = glob.glob(r"%s/*" % glob.escape(self.path))
			
			def find_episode_from_list(list, path):
				for ep in list:
					if ep["path"] == path:
						return ep
				return None
			
			collection = []
			
			for filename in file_list:
				if os.path.isdir(filename):
					#get files inside
					vid_files = glob.glob(r"%s/**/*" % glob.escape(filename)) + glob.glob(r"%s/*" % glob.escape(filename))
					programmes = self.find({"programme":{"path":filename}},programme_limit=1)
					programme = None
					preexisting_eps = []
					if len(programmes) > 0:
						programme = clone(programmes[0])
						preexisting_eps = programme["episodes"]
						programme["episodes"] = []
					else:
						programme = self.create_programme(filename, get_name_from_path(filename))
					
					for s in vid_files:
						if self.is_supported_format(s):
							ep = find_episode_from_list(preexisting_eps, s)
							if ep is None:
								ep = self.create_episode(path=s, name=get_name_from_path(s))
								if ep["runtime"] >= 300:
									print("Adding Episode (%4i) %s" % (ep["runtime"], s))
								
							if ep["runtime"] >= 300:
								programme["episodes"].append(clone(ep))
								
					if len(programme["episodes"]) <= 1:
						programme["type"] = 1
							
					#if len(programme["episodes"]) > 0:
					collection.append(programme)
				else:
					#solo file
					programmes = self.find({"episode":{"path":filename}},programme_limit=1)
					if len(programmes) <= 0:
						programme = self.create_programme(filename, get_name_from_path(filename),type=1)
						ep = self.create_episode(path=filename, name=get_name_from_path(filename))
						if ep["runtime"] >= 300:
							programme["episodes"].append(ep)
							collection.append(programme)
						
			#self.lock.acquire()
			self.programme_data = collection
			#self.lock.release()
			
			self.trigger("schedule.poll")
		
		self.build_schedule()
		
		self.save()
				
	@staticmethod
	def create_programme(path="", name="", desc="", type=0 ):
		date = int(datetime.now().timestamp())
		hash = "%s_%s" % (path, date)
		id = hashlib.md5(hash.encode("utf-8")).hexdigest()
		
		return {
			"id": id,
			"path": path,
            "name": name,
			"desc": desc,
			"type": type,
			"date_added": date,
			"watched_count": 0,
            "episodes": [],
            "tags": [],
            "average_runtime": 3600,
            "date_watched": 0,
			"last_watched_id": "",
			"average_runtime": 3600,
			"date_watched": 0
		}
		
	@staticmethod
	def create_episode(path="", name="", desc="",):
		date = int(datetime.now().timestamp())
		hash = "%s_%s" % (path, date)
		id = hashlib.md5(hash.encode("utf-8")).hexdigest()
		runtime = get_video_duration(path)
		
		return {
			"id": id,
			"path": path,
			"name": name,
			"desc": desc,
			"date_added": date,
			"runtime": runtime,
			"watched_count": 0,
			"date_watched": 10,
		}
		
	@staticmethod
	def is_supported_format(path):
		path = path.lower()
		if "sample" in path:
			return False
			
		for ext in ChannelSchedule.supported_extensions:
			if path.endswith(ext):
				return True
		return False
		
	@staticmethod
	def flatten(selection):
		output = []
		for programme in selection:
			output += programme["episodes"]
		return output
		
	@staticmethod
	def nearest_date_from_string(s, time="00:00"):
		now = datetime.now()
		time_over = int(datetime(year=now.year, month=now.month, day=now.day).timestamp())
		w = now.weekday()
		if s == "all":
			pass
		if s == "weekday":
			time_over += max(w - 4, 0) * ChannelSchedule.seconds_in_day
		elif s == "weekend":
			time_over += max(5 - w, 0) * ChannelSchedule.seconds_in_day
		elif s == "monday":
			time_over += (w-0) % 7 * ChannelSchedule.seconds_in_day
		elif s == "tuesday":
			time_over += (w-1) % 7 * ChannelSchedule.seconds_in_day
		elif s == "wednesday":
			time_over += (w-2) % 7 * ChannelSchedule.seconds_in_day
		elif s == "thursday":
			time_over += (w-3) % 7 * ChannelSchedule.seconds_in_day
		elif s == "friday":
			time_over += (w-4) % 7 * ChannelSchedule.seconds_in_day
		elif s == "saturday":
			time_over += (w-5) % 7 * ChannelSchedule.seconds_in_day
		elif s == "sunday":
			time_over += (w-6) % 7 * ChannelSchedule.seconds_in_day
			
		hour, minute = time.split(":")
		time_over += int(hour) * ChannelSchedule.seconds_in_hour
		time_over += int(minute) * ChannelSchedule.seconds_in_minute
		
		return time_over
		
		
def get_video_duration(path):
	try:
		import io
		import re
		shutup = open(os.devnull, 'w')
		capture = subprocess.run(["ffprobe", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		#print(capture.stderr)
		
		out = capture.stdout.decode("utf-8")
		if len(out) <= 0:
			out = capture.stderr.decode("utf-8")
			
		lines = capture.stderr.decode("utf-8").split("\n")
		
		for line in lines:
			match = re.match(".*Duration\:\s*(\d\d)\:(\d\d):(\d\d).*", line)
			if match is not None:
				return int(match.group(1))*3600+int(match.group(2))*60+int(match.group(3))
	except Exception as ex:
		print(ex)
	return 0
		
		
def match_key(key, value, match):
	if type(match) is str:
		matches = match.split(",")
	elif type(match) is list:
		matches = match
	else:
		matches = [match]
		
	output = False
	for m in matches:
		if type(value) is list:
			output |= m in value
		if ">=" in key:
			output |= value >= match
		elif "<=" in key:
			output |= value <= match
		elif ">" in key:
			output |= value > match
		elif "<" in key:
			output |= value < match
		else:
			output |= value == match
	return output
		
def strip_operators(s):
	ops = [">","<","=","!"]
	for op in ops:
		s = s.replace(op, "")
	return s
	
def randlist(l):
	if len(l) > 0:
		return l[randint(0, len(l)-1)]
	return None
	
def clone(p):
	out = p
	if type(p) is list:
		out = []
		for i in p:
			out.append(clone(i))
	elif type(p) is dict:
		out = {}
		for i in p:
			out[i] = clone(p[i])
	return out

def get_name_from_path(p):
	return p[len(os.path.dirname(p))+1:]

def md5(s):
	return hashlib.md5(s.encode("utf-8")).hexdigest()
		

#c = ChannelSchedule("store/channel0.json")
#print(len(c.programme_data["programmes"]))