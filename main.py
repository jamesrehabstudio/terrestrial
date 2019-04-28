from control import ControllerInterface, Map
from datetime import datetime
from schedule import ChannelSchedule
import tkinter as tk

from PIL import ImageTk, Image
from gui import AppElement, ScheduleTableElement, ModalElement

import vlc
import time
import glob

#player = vlc.MediaPlayer(r"E:\users\james\movies\The_Hitcher_1986_DVDRip_[scarabey.org].avi")
#player.play()

class Terrestrial(tk.Tk):
	def __init__(self):
		super().__init__()
		self.input = ControllerInterface()
		self.input.listen(self.button_press)
		self.media_player = None
		self.dirty = True
		self.playing = False
		self.playing_channel = -1
		self._precheck = 0
		self.subtitle_track = 0
		
		ins = vlc.Instance()
		self.media_player = ins.media_player_new()
		
		config_list = glob.glob(r"configs/*.json")
		
		now = datetime.now()
		self.lastBuild = datetime(year=now.year, month=now.month, day=now.day+1, hour=now.hour, minute=now.minute)
		
		self.data = []
		for config in config_list:
			print(config)
			self.data.append( ChannelSchedule(config) )
		
		#create GUI elements
		self.gui_bar1 = AppElement((1900,900),(0,0),self.data)
		self.table = self.gui_bar1.find(ScheduleTableElement)
		self.modal = self.gui_bar1.find(ModalElement)
		
		self.modal.visible = False
		self.ctx = Image.new("RGB", (800,800))
		pi = ImageTk.PhotoImage(self.ctx)
		self.main_label = tk.Label(self, image=pi)
		
		self.main_label.pack(fill = "both", expand = "yes")
		
		self.attributes('-fullscreen',True)
		self.bind("<Configure>", self.resize)
		self.mainloop()
		
	def resize(self, event):
		#print((self.winfo_width(),self.winfo_height()))
		self.ctx = Image.new("RGB", (self.winfo_width(),self.winfo_height()))
		
	def get_episode(self):
		now = int(datetime.now().timestamp())
		chn = self.data[self.table.cursor]
		return chn.get_at_time(now)
		
	def play(self):
		sch = self.get_episode()
		
		self.playing_channel = self.table.cursor
		self.modal.visible = self.playing = True
		
		if sch is None:
			return
	
		data = self.data[self.table.cursor]
		epi = sch["programme"]["episodes"][0]
		now = int(datetime.now().timestamp())
		start_time = (now - sch["time"]) * 1000
		

		print(data.update(epi["id"], {
			"date_watched" : int(datetime.now().timestamp())
		}))
		
		self.subtitle_track = 0
		self.media_player.set_mrl(epi["path"])
		self.media_player.set_fullscreen(True)
		self.media_player.play()
		self.media_player.set_time(start_time)
		
		data.save()
		time.sleep(1)
	
	def stop(self):
		if self.media_player is not None and self.playing:
			self.modal.visible = self.playing = False
			self.media_player.stop()
			time.sleep(0.125)
		
	def button_press(self, event):
		if event.code == Map.POV_DOWN:
			self.table.set_cursor( min(self.table.cursor+1, len(self.data)-1) )
		elif event.code == Map.POV_UP:
			self.table.set_cursor( max(self.table.cursor-1, 0) )
		elif event.code == Map.BUTTON_0:
			print("PLAY")
			self.play()
		elif event.code == Map.BUTTON_1: 
			self.stop()
		elif event.code == Map.BUTTON_2: 
			self.data[0].build_schedule(4)
		elif event.code == Map.BUTTON_3: 
			#change subtitles
			count = self.media_player.video_get_spu_count()
			
			self.subtitle_track += 1
			if self.subtitle_track > count:
				self.subtitle_track = -1
				
			self.media_player.video_set_spu(self.subtitle_track)
		elif event.code == Map.BUTTON_SELECT: 
			self.data[0].save()
			
		self.table.dirty()
		
	def mainloop(self):
		try:
			while True:
				self.input.pop_event()
				now = datetime.now()
				
				if self.playing and not self.media_player.is_playing():
					self.play_next_video()
					
				if now >= self.lastBuild:
					self.lastBuild = datetime(year=now.year, month=now.month, day=now.day+1, hour=now.hour, minute=now.minute)
					for data in self.data:
						date.build_schedule(12)
			
				#clear
				self.ctx.paste((0,0,0,0), (0,0,800,800))
				
				if self.dirty:
					self.dirty = False
					self.gui_bar1.repaint(force=True)
				
				self.gui_bar1.update_all()
				self.gui_bar1.render(self.ctx)
				#self.gui_text.render(self.ctx)
				
				#flip buffer
				pi = ImageTk.PhotoImage(self.ctx)
				self.main_label.configure(image=pi)
				self.main_label.image = pi
				
				self.update()

		except KeyboardInterrupt:
			pass
	
	def play_next_video(self):
		now = int(datetime.now().timestamp())
		if now > self._precheck:
			self._precheck = now + 1
			sch = self.get_episode()
			if sch is not None:
				self.play()
		
t = Terrestrial()