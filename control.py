from select import select
from enum import Enum

import threading
import time

path_stick = r"/dev/input/by-id/usb-Sony_PLAYSTATION_R_3_Controller-joystick"
path_event = r"/dev/input/by-id/usb-Sony_PLAYSTATION_R_3_Controller-event-joystick"
name = r"usb-Sony_PLAYSTATION_R_3_Controller-joystick"
name = r"usb-Sony_PLAYSTATION_R_3_Controller-event-joystick"
path_event = r"/dev/input/event8"

#joy = InputDevice(path_event)
#except_codes = [0,1,2,5,59,60,61]
#except_codes = [2,1,5,59,60,61]

class Map(Enum):
	BUTTON_0 = 0
	BUTTON_1 = 1
	BUTTON_2 = 2
	BUTTON_3 = 3
	BUTTON_R1 = 4
	BUTTON_R2 = 5
	BUTTON_L1 = 6
	BUTTON_L2 = 7
	BUTTON_START = 8
	BUTTON_SELECT = 9
	
	POV_UP = 10
	POV_RIGHT = 11
	POV_DOWN = 12
	POV_LEFT = 13
	
	AXIS_L_X = 14
	AXIS_L_Y = 15
	AXIS_R_X = 16
	AXIS_R_Y = 17
	
	BUTTON_R3 = 18
	BUTTON_L3 = 19
	
	

PS3_CONTROLLER_MAP = {
	#1 : {"name":"AXIS_L_Y", "map":Map.BUTTON_0, "type":1},
	#2 : {"name":"AXIS_R_Y", "map":Map.BUTTON_0, "type":1},
	#5 : {"name":"AXIS_R_Y", "map":Map.BUTTON_0, "type":1},
	#48 : {"name":"BUTTON_L2_PRESSURE", "map":Map.BUTTON_0
	#49 : {"name":"BUTTON_L2_PRESSURE", "map":Map.BUTTON_0
	#50 : {"name":"BUTTON_L1_PRESSURE", "map":Map.BUTTON_0
	#51 : {"name":"BUTTON_R1_PRESSURE", "map":Map.BUTTON_0
	#52 : {"name":"BUTTON_TRIANGLE_PRESSURE", "map":Map.BUTTON_0
	#53 : {"name":"BUTTON_CIRCLE_PRESSURE", "map":Map.BUTTON_0
	#55 : {"name":"BUTTON_SQUARE_PRESSURE", "map":Map.BUTTON_0
	#54 : {"name":"BUTTON_X_PRESSURE", "map":Map.BUTTON_0

	#4 : {"name":"CHANGE_STATE", "map":Map.BUTTON_0,
	58 : {"name":"BUTTON_SELECT", "map":Map.BUTTON_SELECT, "type":0},
	61 : {"name":"BUTTON_L3", "map":Map.BUTTON_L3, "type":0},
	62 : {"name":"BUTTON_R3", "map":Map.BUTTON_R3, "type":0},
	59 : {"name":"BUTTON_START", "map":Map.BUTTON_START, "type":0},
	32 : {"name":"BUTTON_POV_UP", "map":Map.POV_UP, "type":0},
	35 : {"name":"BUTTON_POV_RIGHT", "map":Map.POV_RIGHT, "type":0},
	33 : {"name":"BUTTON_POV_DOWN", "map":Map.POV_DOWN, "type":0},
	34 : {"name":"BUTTON_POV_LEFT", "map":Map.POV_LEFT, "type":0},
	56 : {"name":"BUTTON_L2", "map":Map.BUTTON_L2, "type":0},
	57 : {"name":"BUTTON_R2", "map":Map.BUTTON_R2, "type":0},
	54 : {"name":"BUTTON_L1", "map":Map.BUTTON_L1, "type":0},
	55 : {"name":"BUTTON_R1", "map":Map.BUTTON_R1, "type":0},
	51 : {"name":"BUTTON_TRIANGLE", "map":Map.BUTTON_3, "type":0},
	49 : {"name":"BUTTON_CIRCLE", "map":Map.BUTTON_1, "type":0},
	48 : {"name":"BUTTON_X", "map":Map.BUTTON_0, "type":0},
	52 : {"name":"BUTTON_SQUARE", "map":Map.BUTTON_2, "type":0},
}

class ControllerInterface:
	MAX_CONTROLLERS = 4
	def __init__(self):
		self.alive = True
		self._listeners = []
		
		self.states = []
		self.events = []
		self.map = []
		for c in range(self.MAX_CONTROLLERS):
			s = {}
			self._listeners.append([])
			self.events.append([])
			self.map.append(None)
			for i in Map:
				s[i.value] = 0
			self.states.append(s)
			
			if(c == 0):
				t = threading.Thread(target=ControllerInterface.manage_input, args=(self,c))
				t.start()
			
	def listen(self, callback_down, callback_up=None, port=0):
		self._listeners[port].append(
			(callback_down, callback_up)
		)
		print(self._listeners)
		
	def stop(self):
		self.alive = False
		
	def pop_event(self):
		"""Call when you want to pop all events from queue"""
		for index in range(self.MAX_CONTROLLERS):
			if len(self.events[index]) > 0:
				event = self.events[index].pop()
				for cb in self._listeners[index]:
					if event.state == ControllerEvent.DOWN:
						if callable(cb[0]):
							cb[0](event)
					elif event.state == ControllerEvent.UP:
						if callable(cb[1]):
							cb[1](event)
			
	def manage_input(self, index):
		state = self.states[index]
		events = self.events[index]
		map = PS3_CONTROLLER_MAP
		
		#path_event = r"/dev/input/event8"
		path_event = r"/dev/input/by-id/usb-Sony_PLAYSTATION_R_3_Controller-event-joystick"
		joy = None
		
		
		byte_buff = []
		joy = []
		inFile = None
		while self.alive:
			while inFile is None:
				try:
					inFile = open(path_event, "rb")
					print(path_event)
				except:
					inFile = None
					time.sleep(0.5)
					
			
			try:
				joy = []
				line = inFile.readline()
				if line:
					for b in line:
						byte_buff.append(b)
						if len(byte_buff) >= 16:
							joy.append(InputEvent(byte_buff))
							byte_buff = []
			
				for event in joy:
					if event.code in map:
						m = map[event.code]
						if m["type"] == 0:
							#button
							if event.value == 0:
								events.append( ControllerEvent(
									m["map"],
									ControllerEvent.UP,
									m["name"],
									index
								))
							elif event.value == 1:
								events.append( ControllerEvent(
									m["map"],
									ControllerEvent.DOWN,
									m["name"],
									index
								))
			except OSError:
				inFile = None
				print("Controller %s disconnected" % index)
							
	#		if len(self.events[index]) > 0:
	#			event = self.events[index].pop()
	#			for cb in self._listeners[index]:
	#				if event.state == ControllerEvent.DOWN:
	#					if callable(cb[0]):
	#						cb[0](event)
	#				elif event.state == ControllerEvent.UP:
	#					if callable(cb[1]):
	#						cb[1](event)
	
class InputEvent:
	def __init__(self, buff):
		self.iterator = buff[0]
		self.code = buff[10]
		self.value = buff[12]
		
		self._raw = buff
		
	def __str__(self):
		return "iterator %s, value: %s, code: %s" % (self.iterator, self.value,self.code)
							
class ControllerEvent:
	UP = 0
	DOWN = 1
	def __init__(self, code, state, name, port):
		self.code = code
		self.state = state
		self.name = name
		self.port = port
		
	def __str__(self):
		return "%s <%s>" % ( str(self.code), str(self.state) )