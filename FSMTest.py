#!/usr/bin/env python
# -*- coding: ascii -*-
try:
    import sys, os, re
    import pygame
    from pygame.locals import *
    from transitions import Machine
    import time
    from Queue import Queue
    import logging
    import animation
    import psutil
    from datetime import datetime, timedelta
    from subprocess import PIPE, Popen    
except ImportError, err:
    print "%s Failed to load Module: %s" % (__file__, err)
    sys.exit(1)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
#logging.basicConfig(level=logging.CRITICAL)

#Define RotarySwitch pins
A_PIN  = 17 #wiring=0
B_PIN  = 27 #wiring=2
SW_PIN = 22 #wiring=3


# Define pygame parameters
# set up some usefull colors
ScreenSize = (160,128)
ScrenSaverTime = 120 #in seconds
BLACK  =  (  0,   0,   0)
WHITE  =  (255, 255, 255)
RED    =  (255,   0,   0)
GREEN  =  (  0, 255,   0)
BLUE   =  (  0,   0, 255)
LBLUE  =  (159, 182, 205)
YELLOW =  (255, 255,   0)

# animated gif for loading/processing time delay
BaseDir=os.path.dirname(os.path.realpath(__file__))
LoadingGIF = os.path.join(BaseDir, "res/loading.gif")
fontpath = os.path.join(BaseDir, "res/DejaVuSansMono-Bold.ttf") 

# Define finite state machine
# define state
# 3 main screens A, B, X, one S (for a saver screen) and one "sub-screen B10 for main B, and one exit 'Ad' status in A    
states      = ['A', 'Ad', 'B', 'B01', 'X', 'S']
# define transition between states
#                  event,  from_state, to_state
transitions = [
                   ['R',   'A',   'B'  ],   # turning knob right change from A to B
                   ['R',   'B',   'X'  ],   # turning knob right change from B to X
                   ['R',   'X',   'A'  ],   # turning knob right change from X to A (complete loop)
                   ['L',   'A',   'X'  ],   # turning knob left  change from A to X
                   ['L',   'X',   'B'  ],   # turning knob right change from X to B
                   ['L',   'B',   'A'  ],   # turning knob right change from B to A (complete loop)
                   ['D',   'B',   'B01'],   # pressing knob down in state B switch to B10
                   ['D',   'B01', 'B'  ],   # pressing knob down in state B10 switch to B
                   ['D',   'S',   'A'  ],   # press, turn left, right in screensaver leads always to the A state
                   ['D',   'A',   'Ad' ],   # press down the A state exits to A01 (state wehere the application exits)
                   ['R',   'S',   'A'  ],
                   ['L',   'S',   'A'  ]
                   ]


def pi_version():

# Detect the version of the Raspberry Pi.  Returns either 1, 2 or
# None depending on if it's a Raspberry Pi 1 (model A, B, A+, B+),
# Raspberry Pi 2 (model B+), or not a Raspberry Pi.

# Check /proc/cpuinfo for the Hardware field value.
# 2708 is pi 1
# 2709 is pi 2
# Anything else is not a pi.
    with open('/proc/cpuinfo', 'r') as infile:
        cpuinfo = infile.read()
    # Match a line like 'Hardware   : BCM2709'
    match = re.search('^Hardware\s+:\s+(\w+)$', cpuinfo, flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        # Couldn't find the hardware, assume it isn't a pi.
        return None
    if match.group(1) == 'BCM2708':
        # Pi 1
        logging.debug('RPI: ' + match.group(1))
        return 1
    elif match.group(1) == 'BCM2709':
        # Pi 2
        logging.debug('RPI: ' + match.group(1))
        return 2
    else:
        # Something else, not a pi.
        return None

#save the pi_function results results into global variable 
RPI_Version = pi_version()


#Define queue for the RotarySwitch events
RotQueue = Queue()  # define global queue for events

if RPI_Version is not None:
    import RotaryEncoder
    # create rotary encoder / switch object
    encoder = RotaryEncoder.RotaryEncoderWorker(A_PIN, B_PIN, SW_PIN, RotQueue)
    # close the gpio port at extit time    
    import atexit
    @atexit.register
    def close_gpio():                                                               
        encoder.Exit()

class Matter(object):
    def __init__(self):
        self.starttime = 0
        self.running = True
        self.LineToDisplay = 0
    
# Define changing the pygame state manager based on the above finite state machine
       
    def on_enter_A(self, st):
        logging.debug("=> state A")
        st.manager.change(AScreen(st.screen))
    def on_enter_B(self, st):
        logging.debug("=> state B")
        st.manager.change(BScreen(st.screen))
    def on_enter_B10(self, st):
        logging.debug("=> state B10")
        # no pygame screen chnage we stay here at screen B
        # and the action has to be handle by the B screen
    def on_enter_X(self, st):
        logging.debug("=> state C")
        st.manager.change(XScreen(st.screen))
    def on_enter_S(self, st):
        logging.debug("=> state S")
        st.manager.change(ScreenSaver(st.screen))
                
lump = Matter()

def get_cpu_temperature():
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
    output, _error = process.communicate()
    return float(output[output.index('=') + 1:output.rindex("'")])

def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9.8 K'
    >>> bytes2human(100001221)
    '95.4 M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.0f %s' % (value, s)
    return '%.02f B' % (n)


def main():

    if RPI_Version is not None: # only for RPI point to a new frame buffer display
        os.environ["SDL_FBDEV"] = "/dev/fb1"
        os.environ['SDL_VIDEODRIVER']="fbcon"    
    
    pygame.init()
    timer = pygame.time.Clock()
    pygame.mouse.set_visible(0)
    screen = pygame.display.set_mode(ScreenSize, 0, 32) # screen size taken from settings
   
    #initiate the FSM with states and transition taken from settings, start in state A   
    machine = Machine(model=lump, states=states, transitions=transitions, initial='A', ignore_invalid_triggers=True)
    manager = StateMananger(screen)

    while lump.running:
        timer.tick(50)

        # running is False if handle_events is False (Quit etc)
        lump.running = manager.state.handle_events(pygame.event.get())

        #update and render the managers active state
        manager.update()
        manager.render(screen)

        pygame.display.flip()

    # Say goodbye before you quit
    logging.debug('... Quitting')
    pygame.quit()

class StateMananger(object):
    """
    The idea of the pygame state management concept is taken from one of the internet articles, nut I don't know where it comes from, any more.
    If am Author can recognize its code, please contact me, it is my pleasure to add him here 
    """
    
    # Statemanager manages States, loads the first state in the
    # constructor and has a option to print things out
    def __init__(self, screen):
        # on constructions change to our first state
        logging.debug('Init StateManager')
        self.change(AScreen(screen))

    def change(self, state):
        # the new self.state is our passed state
        old_state_name = 'None'
        try: 
            self.state
            old_state_name = self.get_name()
        except: 
            old_state_name = 'None'

        logging.debug('From '+ old_state_name)
        self.state = state
        self.state.manager = self
        logging.debug('changed to '+self.get_name())

    def update(self):
        self.state.update()

    def render(self, screen):
        self.state.render(screen)

    def get_name(self):
        return self.state.name

    def get_descr(self):
        return self.state.description
    
class State(object):
    # a superclass for our States so we dont have to write things
    # over and over if we want to do sth. in every state we construct.
    def __init__(self, screen):
        logging.debug('Init State')
        self.screen = screen
        self.name = None
        self.description = None
        self.ScreenSaverElapsed = time.time() # in seconds

    def __str__(self):
        return str(self.name) + str(self.description)
 
    def handle_events(self, events):
        # every State can have its own event management or can use this ones 
        
        if RPI_Version is not None:
            if not(RotQueue.empty()):
                m=RotQueue.get_nowait()
                logging.debug('Processed ' + m)
                if m == RotaryEncoder.EventLeft:
                    lump.L(self)
                elif m == RotaryEncoder.EventRight:
                    lump.R(self)
                elif m == RotaryEncoder.EventDown:
                    lump.D(self)
                elif m == RotaryEncoder.EventUp:
                    logging.debug('Done ' + m)                    
                RotQueue.task_done()
                self.ScreenSaverElapsed = time.time()
        
        for e in events:
            if e.type == QUIT:
                logging.debug('Pressed Quit (in a window mode)')
                return False
    
            elif e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    logging.debug('Pressed ESC for quitting')
                    return False
                # change State if user presses "2"
                elif e.key == K_LEFT:
                    #st.manager.change(AScreen(st.screen))
                    lump.L(self)
                elif e.key == K_RIGHT:
                    #st.manager.change(BScreen(st.screen))
                    lump.R(self)
                elif e.key == K_DOWN:
                    #st.manager.change(BScreen(st.screen))
                    lump.D(self)
                self.ScreenSaverElapsed = time.time()
        if not(lump.is_S()) and (time.time() - self.ScreenSaverElapsed > ScrenSaverTime): # if not already in Screensaver and time to save passed 
            logging.debug(' => screen saver')
            lump.to_S(self)              
                                        
        return True      

# I recommend loading those classes from another
# file/module so you don't die a painful death... but for the sake of example let keep all in one file

class AScreen(State):

    def __init__(self, screen):
        State.__init__(self, screen)

        self.name = "Status"
        self.description = "Status Screen"
        logging.debug('A - Status Screen')

        #Font size, for testing
        self.TSize1  = 18
        self.XOffset =  5
        self.YOffset =  4

        self.cur_sent = 0
        self.cur_recv = 0
        self.tot = psutil.net_io_counters()

        self.t0 = time.time()

        if RPI_Version is not None:
            self.cpu_temperature = get_cpu_temperature()
        else:
            self.cpu_temperature = 0.0

        self.cpu_usage = psutil.cpu_percent()
        self.ram = psutil.virtual_memory()
        self.disk = psutil.disk_usage('/')
        self.cur_sent = 0 
        self.cur_recv = 0 
        
        # draw on the surface object
        #self.screen.fill(BLACK)

        # A whole Block just to display the Text ...
        #self.SmallFont1 = pygame.font.SysFont(None, self.TSize1)
        self.SmallFont1 = pygame.font.Font(fontpath, 12)
        self.SF1Y = self.SmallFont1.size("X")[1]+2
        
        # Render the text
        #self.THeader1 = self.BigFont1.render('   TVHeadEnd Server   ', True, WHITE, LBLUE)
        #self.RHeader1 = self.THeader1.get_rect()
        #self.RHeader1.centerx = self.screen.get_rect().centerx
        #self.RHeader1.y  = 0
                           
    def render(self, screen):
        # Rendering the State
        if time.time() - self.t0 > 4:
            if RPI_Version is not None:
                self.cpu_temperature = get_cpu_temperature()
            else:
                self.cpu_temperature = 0.0
            self.cpu_usage = psutil.cpu_percent()
            self.ram = psutil.virtual_memory()
            self.disk = psutil.disk_usage('/')
            #swap = psutil.swap_memory()
            #print ("SWAP {:.2f}".format(bytes2human(swap.used)))
            net = psutil.net_io_counters()
            t1 = time.time()
            self.cur_sent = ((net.bytes_sent - self.tot.bytes_sent) / (t1-self.t0)) 
            self.cur_recv = ((net.bytes_recv - self.tot.bytes_recv) / (t1-self.t0)) 
            self.t0 = t1
            self.tot = net
        
        screen.fill(BLACK)
        pygame.draw.rect(screen, YELLOW, (0,0,160,128), 1)
        
        try:
            uptime = datetime(1,1,1) + timedelta(seconds=int(time.time()-psutil.boot_time()))
        except:
            uptime = datetime(1,1,1) + timedelta(seconds=int(time.time()))        
        TDate = self.SmallFont1.render  (time.strftime("%d.%m.%Y",time.gmtime()) +"  "+ time.strftime("%H:%M:%S",time.gmtime()), True, WHITE)
        TUpTi = self.SmallFont1.render("UpTime {:d}:{:0>2d}:{:0>2d}:{:0>2d}".format(uptime.day-1, uptime.hour, uptime.minute, uptime.second), True, WHITE)
        TCPU  = self.SmallFont1.render("CPU {:3.0f}% @{:3.0f}*C".format(self.cpu_usage, self.cpu_temperature), True, WHITE, BLACK)
        TMEM  = self.SmallFont1.render('RAM {:3.0f}%  F {:>6s}'.format(self.ram.percent, bytes2human(self.ram.free)),   True, WHITE, BLACK)
        THDD  = self.SmallFont1.render('HDD {:3.0f}%  F {:>6s}'.format(self.disk.percent, bytes2human(self.disk.free)), True, WHITE, BLACK)
        TNES  = self.SmallFont1.render('NET-S {:>8s}'.format(bytes2human(self.cur_sent)), True, WHITE, BLACK)
        TNER  = self.SmallFont1.render('NET-R {:>8s}'.format(bytes2human(self.cur_recv)), True, WHITE, BLACK)

        RDate = TDate.get_rect()
        RUpTi = TUpTi.get_rect()
        RCPU  = TCPU.get_rect()
        RMEM  = TMEM.get_rect()
        RHDD  = THDD.get_rect()
        RNES  = TNES.get_rect()     
        RNER  = TNER.get_rect()

        RDate.x = self.XOffset
        RDate.y = self.YOffset + self.SF1Y*0
        RUpTi.x = self.XOffset
        RUpTi.y = self.YOffset + self.SF1Y*1
        RCPU.x  = self.XOffset
        RCPU.y  = self.YOffset + self.SF1Y*2
        RMEM.x  = self.XOffset
        RMEM.y  = self.YOffset + self.SF1Y*3
        RHDD.x  = self.XOffset
        RHDD.y  = self.YOffset + self.SF1Y*4
        RNES.x  = self.XOffset
        RNES.y  = self.YOffset + self.SF1Y*5
        RNER.x  = self.XOffset
        RNER.y  = self.YOffset + self.SF1Y*6            
        
        self.screen.blit(TDate, RDate)
        self.screen.blit(TUpTi, RUpTi)
        self.screen.blit(TCPU,  RCPU)
        self.screen.blit(TMEM,  RMEM)
        self.screen.blit(THDD,  RHDD)
        self.screen.blit(TNES,  RNES)
        self.screen.blit(TNER,  RNER)

        if lump.is_Ad():
            lump.running = False
    
    def update(self):
        pass

class BScreen(State):
    def __init__(self, screen):
        State.__init__(self, screen)

        logging.debug('Init Bscreen')

        self.name = "Second Screen B"
        self.description = "Second Screen"
        logging.debug('Second B Screen Entered')

        self.font = pygame.font.SysFont("", 20)
        self.text1 = self.font.render('Press Knob', True, BLACK, YELLOW)
        self.text1Rect = self.text1.get_rect()
        self.text1Rect.centerx = self.screen.get_rect().centerx
        self.text1Rect.centery = self.screen.get_rect().centery-20
        self.text2 = self.font.render('Press again', True,  YELLOW, BLACK)
        self.text1Rect = self.text1.get_rect()
        self.text2Rect = self.text2.get_rect()
        self.text1Rect.centerx = self.screen.get_rect().centerx
        self.text1Rect.centery = self.screen.get_rect().centery-20
        self.text2Rect.centerx = 120
        self.text2Rect.centery = 100        

        self.processing = animation.GIFImage(LoadingGIF)

    def render(self, screen):
        # check if the finite state machine is in B01 state
        if lump.is_B01():
            screen.fill(RED)
            self.processing.render(screen, (30, 10))
            self.screen.blit(self.text2, self.text2Rect)
        else: # standard B state
            screen.fill(LBLUE)
            self.screen.blit(self.text1, self.text1Rect)

    def update(self):
        pass

class ScreenSaver(State):
    # Gamestate - run your stuff inside here (maybe another manager?
    # for your levelmanagment?)
    def __init__(self, screen):
        State.__init__(self, screen)

        self.name = "screensaver"
        self.description = "after given time switch everything to black"
        logging.debug('0 - Screen Saver')        

        self.screen.fill(BLACK)
        
    def render(self, screen):
        pass

    def update(self):
        pass


class XScreen(State):
    # Our first state
    def __init__(self, screen):
        State.__init__(self, screen)

        self.name = "Screen Example"
        self.description = "whatsoever"
        logging.debug('Screen Example')

        # A whole Block just to display the Text ...
        self.font1 = pygame.font.SysFont("Monospaced", 28)
        self.font2 = pygame.font.SysFont("Monospaced", 30)
        # Render the text
        self.text1 = self.font1.render(self.name, True, WHITE, BLACK)
        self.text2 = self.font2.render(self.description, True, WHITE, RED)
        # Create Text-rectangles
        self.text1Rect = self.text1.get_rect()
        self.text2Rect = self.text2.get_rect()

        # Center the Text-rectangles
        self.text1Rect.centerx = self.screen.get_rect().centerx
        self.text1Rect.centery = self.screen.get_rect().centery-20

        self.text2Rect.centerx = self.screen.get_rect().centerx
        self.text2Rect.centery = self.screen.get_rect().centery+10

    def render(self, screen):
        # Rendering the State
        pygame.display.set_caption(self.name +"  "+self.description)
        screen.fill((20, 20, 20))

        self.screen.blit(self.text1, self.text1Rect)
        self.screen.blit(self.text2, self.text2Rect)


    def update(self):
        pass

# Events can be also handled locally if needed - this differs from the Screen A and B !!!
    def handle_events(self,events):
        # every State has its own eventmanagment

        if RPI_Version is not None:
            if not(RotQueue.empty()):
                m=RotQueue.get_nowait()
                logging.debug('Processed ' + m)
                if m == RotaryEncoder.EventLeft:
                    lump.L(self)
                elif m == RotaryEncoder.EventRight:
                    lump.R(self)
                elif m == RotaryEncoder.EventDown:
                    lump.D(self)
                elif m == RotaryEncoder.EventUp:
                    logging.debug('Done ' + m)                    
                RotQueue.task_done()
                self.ScreenSaverElapsed = time.time()
        
        for e in events:
            if e.type == QUIT:
                print ("Pressed Quit (Window)")
                return False

            elif e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    print ("Pressed Quit (Esc)")
                    return False
                elif e.key == K_LEFT:  lump.L(self)
                elif e.key == K_RIGHT: lump.R(self)
        return True


# Run the main function
if __name__ == "__main__":
    main()
