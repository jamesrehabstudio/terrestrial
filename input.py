#!/usr/bin/python
#######################################################################
#Copyright (c) 2009 Tamara Broderick
#All rights reserved.
#
#Redistribution and use in source and binary forms,
# with or without modification, are permitted provided
# that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#    * Neither the name of the <ORGANIZATION> nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#######################################################################

from tkinter import *
import pygame

class Find_Joystick:
    def __init__(self, root):
        self.root = root

        ## initialize pygame and joystick
        pygame.init()
        if(pygame.joystick.get_count() < 1):
            # no joysticks found
            print("Please connect a joystick.\n")
            self.quit()
        else:
            # create a new joystick object from
            # ---the first joystick in the list of joysticks
            Joy0 = pygame.joystick.Joystick(0)
            # tell pygame to record joystick events
            Joy0.init()
            print("Joystick found...")

        ## bind the event I'm defining to a callback function
        self.root.bind("<<JoyFoo>>", self.my_event_callback)

        ## start looking for events
        self.root.after(0, self.find_events)

    def find_events(self):
        ## check everything in the queue of pygame events
        events = pygame.event.get()
        for event in events:
            # event type for pressing any of the joystick buttons down
            if event.type == pygame.JOYBUTTONDOWN:
                # generate the event I've defined
                self.root.event_generate("<<JoyFoo>>")

        ## return to check for more events in a moment
        self.root.after(20, self.find_events)

    def my_event_callback(self, event):
        print("Joystick button press (down) event")

    ## quit out of everything
    def quit(self):
        import sys
        sys.exit()
def main():
    ## Tkinter initialization
    root = Tk()
    app = Find_Joystick(root)
    # get out by closing the window or pressing Control-q
    root.protocol('WM_DELETE_WINDOW', app.quit)
    root.bind('<Control-q>', app.quit)
    root.bind('<Control-Q>', app.quit)
    root.mainloop()

if __name__ == "__main__":
    main()