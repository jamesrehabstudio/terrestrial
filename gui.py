from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone
import math
import os

class GUIElement:
	BASE_BG_COLOR = (0,20,100)
	HIGHLIGHT_BG_COLOR = (255,100,0)
	RENDER_ONCE = False
	FONT = 'Pillow/Tests/fonts/FreeMono.ttf'
	
	def __init__(self, size=(1,1), pos=(0,0)):
		self.pos = pos
		self.parent = None
		self.children = []
		self.size = size
		self.img = Image.new("RGBA", self.size)
		self._dirty = True
		self.visible = True
		
	def add_child(self, child):
		if child not in self.children:
			child.parent = self
			self.children.append(child)		
			
	def dirty(self):
		self._dirty = True
		if self.parent is not None:
			self.parent.dirty()
		
	def set_position(pos):
		self.pos = pos
		
	def set_size(self, size):
		self.size = size
		self.img = Image.new("RGBA", self.size)
		self.repaint()
		
	def find(self, t):
		if type(self) is t:
			return self
		for child in self.children:
			a = child.find(t)
			if a is not None:
				return a
		return None
		
	def get_area(self):
		return (
			self.pos[0], 
			self.pos[1], 
			self.pos[0] + self.size[0],
			self.pos[1] + self.size[1]
		)
		
	def update_all(self):
		self.update()
		for child in self.children:
			child.update_all()
	
	def update(self):
		pass
	
	def render(self, g):
		if self._dirty:
			self.set_size(self.size)
			self.repaint()
			self._dirty = False
			
		if self.visible:
			g.paste(self.img, self.get_area(), self.img)
			#for child in self.children:
			#	child.render(self.img)
		
	def repaint(self, force=False):
		if self.RENDER_ONCE and not force:
			return
			
		#clear
		self.img.paste((0,0,0,0), (0,0,self.size[0], self.size[1]))
		self.paint()
		for child in self.children:
			child.render(self.img)
		
	def paint(self):
		self.img.paste(self.BASE_BG_COLOR, (0,0,self.size[0],self.size[1]))

class TextElement(GUIElement):
	def __init__(self, size, pos, text="", font_size=20):
		super().__init__(size, pos)
		self.font = ImageFont.truetype(self.FONT, font_size)
		self.text = text
		
	def paint(self):
		d = ImageDraw.Draw(self.img)
		d.text((0,0), self.text, font=self.font, fill=(255,255,255,255))
		
class ModalElement(GUIElement):
	def __init__(self, size, pos):
		super().__init__(size, pos)
	def paint(self):
		self.img.paste((0,0,0,128), (0,0,self.size[0], self.size[1]))
		
class AppElement(GUIElement):
	def __init__(self, size, pos, chn_arr=[]):
		super().__init__(size, pos)
		self.add_child(InfoElement((size[0],160),(0,0)))
		self.add_child(ScheduleElement((size[0],size[1]-160),(0,160), chn_arr))
		self.add_child(ModalElement(size,(0,0)))

class InfoElement(GUIElement):
	def __init__(self, size, pos, chn_arr=[]):
		super().__init__(size, pos)
		self.add_child(ClockElement((size[1],size[1]),(0,0)))

class ScheduleElement(GUIElement):
	def __init__(self, size, pos, chn_arr=[]):
		super().__init__(size, pos)
		self._next_update = 0
		
		self.add_child(ChannelListElement((64,size[1]),(0,24),chn_arr))
		self.add_child(TimeLineElement((size[0],64),(64,0)))
		self.add_child(ScheduleTableElement(size,(64,24),chn_arr))
		
	def update(self):
		now = int(datetime.now().timestamp())
		if now > self._next_update:
			self.find(TimeLineElement).dirty()
			self.find(ScheduleTableElement).dirty()
			
			self._next_update = now + 12
		
		
class ChannelListElement(GUIElement):
	def __init__(self, size, pos, chn_arr=[]):
		super().__init__(size, pos)
		self.icons = []
		self.icons_org = []
		path = os.path.dirname(__file__)
		for chn in chn_arr:
			img = Image.open(path + chn.icon)
			self.icons_org.append( img )
			self.icons.append( img.resize((size[0],size[0])) )
		
	def paint(self):
		y = 0
		for icon in self.icons:
			self.img.paste(icon, (0,int(y)))
			y += 72

class ScheduleTableElement(GUIElement):
	def __init__(self, size, pos, chn_arr=[]):
		super().__init__(size, pos)
		self.cursor = 0
		self.channels = []
		
		y = 0
		for chn in chn_arr:
			hl = HListElement((size[0], 70),(0,y),chn)
			y += 72
			self.add_child(hl)
		
		self.set_cursor(0)
			
			
	def repaint(self, force=False):
		super().repaint(force)
		for child in self.children:
			child.repaint(force)
			
	def set_cursor(self, c):
		self.cursor = c
		for i, child in enumerate(self.children):
			self.children[i].selected = i == self.cursor
			self.children[i].dirty()
		
class HListElement(GUIElement):
	def __init__(self, size, pos, chn):
		super().__init__(size, pos)
		self.selected = False
		
		chn.listen(self.set_data)
		self.set_data("", chn)
		
	def set_data(self, event, chn):
		arr = chn.get_schedule()
		now = int(datetime.now().timestamp())
		self.children = []
		print("HLIST update(%s): %s" % (len(arr), event))
		
		for data in arr:
			le = ListingElement(self.size, data)
			x = math.floor( (data["time"] - now) / 12)
			le.pos = (x,0)
			self.add_child(le)
			
		self.dirty()
			
	def repaint(self, force=False):
		now = int(datetime.now().timestamp())
		for child in self.children:
			if type(child) is ListingElement:
				x = math.floor( (child.time - now) / 12)
				child.pos = (x, child.pos[1])
		super().repaint(force)
		
	def paint(self):
		if self.selected:
			self.img.paste(self.HIGHLIGHT_BG_COLOR, (0,0,self.size[0],self.size[1]))
		else:
			self.img.paste(self.BASE_BG_COLOR, (0,0,self.size[0],self.size[1]))
			
class ListingElement(GUIElement):
	def __init__(self, size, data=[]):
		super().__init__(size, (0,0))
		self.title = data["programme"]["name"]
		self.runtime = data["programme"]["episodes"][0]["runtime"]
		self.subtitle = data["programme"]["episodes"][0]["name"]
		self.path = data["programme"]["episodes"][0]["path"]
		self.time = data["time"]
		
		self.backgroundColor = self.BASE_BG_COLOR
		
		self.size = (int(self.runtime / 12), size[1])
		
		self.add_child(TextElement(size, (8,8), self.title, 20))
		self.add_child(TextElement(size, (8,28), self.subtitle, 16))
		
	def paint(self):
		area = (0, 0, self.size[0], self.size[1])
		area_inside = (1, 1, self.size[0]-1, self.size[1]-1)
		self.img.paste((255,255,255,255), area)
		self.img.paste(self.backgroundColor, area_inside)
		#self.img.paste((0,0,0,0), area_inside)
		
class TimeLineElement(GUIElement):
	def __init__(self, size, pos):
		super().__init__(size, pos)
		self.font = ImageFont.truetype(self.FONT, 20)
		
	def paint(self):
		self.img.paste(self.BASE_BG_COLOR, (0,0,self.size[0],self.size[1]))
		
		now = int(datetime.now().timestamp())
		
		d = ImageDraw.Draw(self.img)
		segment = 60 * 30
		
		time = math.ceil(now/segment) * segment
		x = 0
		
		while x < self.size[0]:
			x = int( (time-now) / 12 )
			text = datetime.fromtimestamp(time).strftime("%H:%M")
			d.text((x,0), text, font=self.font, fill=(255,255,255,255))
			self.img.paste((255,255,255,255), (x,0,x+1,self.size[1]))
			time += segment
			
class ClockElement(GUIElement):
	def __init__(self, size, pos):
		super().__init__(size, pos)
		self.font = ImageFont.truetype(self.FONT, 30)
		
	def update(self, force=False):
		self.dirty()
			
	def paint(self):
		super().paint()
		
		text = datetime.now().strftime("%H:%M:%S")
		d = ImageDraw.Draw(self.img)
		twidth, theight = d.textsize(text, font=self.font)
		pos = (int(self.size[0]/2-twidth/2), int(self.size[1]/2-theight/2))
		d.text(pos, text, font=self.font, fill=(255,255,255,255))
		
		