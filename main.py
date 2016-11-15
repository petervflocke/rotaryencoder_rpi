#!/usr/bin/env python
# -*- coding: ascii -*-
try:
    import sys, os
    import pygame
    from pygame.locals import *
    from transitions import Machine
    import time
    from Queue import Queue
    import logging
    import settings
    import animation
    import psutil
    from subprocess import PIPE, Popen
    from datetime import datetime, timedelta
    from pyTextRect import render_textrect
except ImportError, err:
    print "%s Failed to load Module: %s" % (__file__, err)
    sys.exit(1)

#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.CRITICAL)

param = settings.settings()


RotQueue = Queue()  # define global que for events

if param.RPI_Version is not None:
    import RotaryEncoder
    encoder = RotaryEncoder.RotaryEncoderWorker(param.A_PIN, param.B_PIN, param.SW_PIN, RotQueue)
    import relay
    Relay = relay.Relay(param.R_PIN)
    import atexit
    @atexit.register
    def close_gpio():                                                               # close the gpio port at exit time
        encoder.Exit()


def check_process(procname):
    if psutil.version_info[0] < 4:
        return procname in [p.name for p in psutil.process_iter()]
    else:
        return procname in [p.name() for p in psutil.process_iter()]  

class Matter(object):
    def __init__(self):
        self.starttime = 0
        self.running = True
        self.LineToDisplay = 0
    
    def on_enter_A(self, st):
        logging.debug("=> state A")
        st.manager.change(AScreen(st.screen))
    def on_enter_B(self, st):
        logging.debug("=> state B")
        st.manager.change(BScreen(st.screen))
    def on_enter_B10(self, st):
        logging.debug("=> state B10")
        st.manager.change(B10Screen(st.screen))
    def on_enter_B11(self, st):
        logging.debug("=> state B10")
        st.manager.change(B11Screen(st.screen))                
    def on_enter_C(self, st):
        logging.debug("=> state C")
        st.manager.change(CScreen(st.screen))
    def on_enter_D(self, st):
        logging.debug("=> state D")
        st.manager.change(DScreen(st.screen))        
    def on_enter_Bd(self, st):
        logging.debug("=> state Bd")
        self.starttime = time.time()
    def on_enter_Ad(self, st):
        logging.debug("=> state Ad")
        self.running = False
    def on_enter_Dd(self, st):
        logging.debug("=> state Dd")
        self.starttime = time.time()
    def on_enter_Cd(self, st):
        logging.debug("=> state Cd")
        self.starttime = time.time()        
    def on_enter_S(self, st):
        logging.debug("=> state S")
        st.manager.change(ScreenSaver(st.screen))
                
lump = Matter()

# set up some usefull colors
BLACK  =  (  0,   0,   0)
WHITE  =  (255, 255, 255)
RED    =  (255,   0,   0)
GREEN  =  (  0, 255,   0)
BLUE   =  (  0,   0, 255)
LBLUE  =  (159, 182, 205)
YELLOW =  (255, 255,   0)

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

    if param.RPI_Version is not None: # only for RPI point to a new frame buffer display
        os.environ["SDL_FBDEV"] = "/dev/fb1"
        os.environ['SDL_VIDEODRIVER']="fbcon"    
    
    global screen
    pygame.init()
    timer = pygame.time.Clock()
    pygame.mouse.set_visible(0)
    screen = pygame.display.set_mode(param.ScreenSize, 0, 32) # screen size taken from settings
   
    #initiate the FSM with states and transition taken from settings, start in state A   
    machine = Machine(model=lump, states=param.states, transitions=param.transitions, initial='A', ignore_invalid_triggers=True)

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
        
        if param.RPI_Version is not None:
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
        if not(lump.is_S()) and (time.time() - self.ScreenSaverElapsed > param.ScrenSaverTime): # if not already in Screensaver and time to save passed 
            logging.debug(' => screen saver')
            lump.to_S(self)              
                                        
        return True      

# I recommend loading those classes from another
# file/module so you don't die a painful death..

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

        if param.RPI_Version is not None:
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
        self.SmallFont1 = pygame.font.Font(param.fontpath, 12)
        self.SF1Y = self.SmallFont1.size("X")[1]+2
        
        # Render the text
        #self.THeader1 = self.BigFont1.render('   TVHeadEnd Server   ', True, WHITE, LBLUE)
        #self.RHeader1 = self.THeader1.get_rect()
        #self.RHeader1.centerx = self.screen.get_rect().centerx
        #self.RHeader1.y  = 0
                           
    def render(self, screen):
        # Rendering the State
        if time.time() - self.t0 > 4:
            if param.RPI_Version is not None:
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

        self.name = "TVHead"
        self.description = "TVHeadend On/Off"
        logging.debug('B - TVHead')
        
        self.processing = animation.GIFImage(param.LoadingGIF)
        self.TVStatus = check_process(param.TVProcname)
        if self.TVStatus:
            self.screen.blit(param.tvon, (0,0) )
        else:
            self.screen.blit(param.tvoff, (0,0) )
        self.CommandCMD    = None      # to monitor daemon start
        self.ProcessingCMD = False     # to stay in monitoring process
        self.TimeCMD       = 0         # timeout for command CMD

    def render(self, screen):
        if lump.is_Bd():
            if self.ProcessingCMD:
                self.processing.render(screen, (5, 11))
                StatusCMD = self.CommandCMD.poll()
                if time.time()-self.TimeCMD > 240: # 4m timeout 120s for stopping the service
                    if self.TVStatus and (param.RPI_Version is not None): Relay.RelayChange(0)
                    lump.to_B(self)
                elif StatusCMD is not None:
                    logging.debug(param.TVProcname + ' returned ' + str(StatusCMD))
                    if (self.TVStatus) and (param.RPI_Version is not None): Relay.RelayChange(0)
                    lump.to_B(self)
            else:
                if self.TVStatus: # now on then switch it off
                    logging.debug('TVHead - switching OFF'  + param.TVDaemonStop)
                    self.CommandCMD = Popen(param.TVDaemonStop, shell=True)
                else: # now off then switch it on
                    if param.RPI_Version is not None:
                        Relay.RelayChange(1)
                        #time.sleep(1)
                    logging.debug('TVHead - switching ON ' + param.TVDaemonStart)
                    self.CommandCMD = Popen(param.TVDaemonStart, shell=True)
                self.ProcessingCMD = True
                self.TimeCMD = time.time()

    def update(self):
        pass

#    def handle_events(self,events):
#        return handle_all_events(self, events)

class B10Screen(State):
    def __init__(self, screen):
        State.__init__(self, screen)

        logging.debug('TV Head Status Log')

        self.name = "TVHeadStatus"
        self.description = "TVHeadend Status Display"
        logging.debug('B1 - TVHead')
        
        lump.LineToDisplay = 1
        
        screen.fill(BLACK)
        
    def render(self, screen):
        my_font = pygame.font.SysFont(None, 14)
        my_string = "No log data found"
        for line in reversed(open("/var/log/syslog").readlines()):
            if param.TVProcname in line.rstrip().lower():
                my_string = line.rstrip()
                break
        my_rect = pygame.Rect((1, 1, 158, 126))
        rendered_text, noerror = render_textrect(my_string, my_font, my_rect, WHITE, BLACK, 0)
        if rendered_text:
            self.screen.blit(rendered_text, my_rect.topleft)

    def update(self):
        pass
    
class B11Screen(State):
    def __init__(self, screen):
        State.__init__(self, screen)

        logging.debug('TV Head Status Log')

        self.name = "TVHeadStatusScroll"
        self.description = "TVHeadend Status Display in scroll"
        logging.debug('B11 - TVHead')
        
    def render(self, screen):
        my_font = pygame.font.SysFont(None, 14)
        my_string = "No more log found"
        i = 0
        for line in reversed(open("/var/log/syslog").readlines()):
            if param.TVProcname in line.rstrip().lower():
                i += 1
                if i == lump.LineToDisplay:
                    my_string = line.rstrip()
                    break
        if i < lump.LineToDisplay: my_string = "No more log found"
        my_rect = pygame.Rect((1, 1, 158, 126))
        rendered_text, noerror = render_textrect(my_string, my_font, my_rect, WHITE, BLACK, 0)
        if rendered_text:
            if noerror:
                pygame.draw.rect(screen, YELLOW, (0,0,160,128), 1)                    
            else:
                pygame.draw.rect(screen, RED, (0,0,160,128), 1)                    
            self.screen.blit(rendered_text, my_rect.topleft)

    def update(self):
        if  lump.is_B12():
            lump.LineToDisplay += 1      # display next line from log
            lump.to_B11(self)
        elif lump.is_B13():
            lump.LineToDisplay -= 1      # display next line from log
            if lump.LineToDisplay < 1: lump.LineToDisplay = 1
            lump.to_B11(self)        
    
    
class CScreen(State):
    # Gamestate - run your stuff inside here (maybe another manager?
    # for your levelmanagment?)
    def __init__(self, screen):
        State.__init__(self, screen)

        self.name = "oscam"
        self.description = "oscam On/Off"
        logging.debug('B - oscam')        

        self.processing = animation.GIFImage(param.LoadingGIF)
        self.OscamStatus = check_process(param.OscamProcname)
        if self.OscamStatus:
            self.screen.blit(param.oscamon, (0,0) )
        else:
            self.screen.blit(param.oscamoff, (0,0) )
        self.CommandCMD    = None      # to monitor daemon start
        self.ProcessingCMD = False     # to stay in monitoring process
        self.TimeCMD       = 0         # timeout for command CMD

    def render(self, screen):
        if lump.is_Cd():
            if self.ProcessingCMD:
                self.processing.render(screen, (5, 11))
                StatusCMD = self.CommandCMD.poll()
                if time.time()-self.TimeCMD > 240: # 4m timeout 120s for stopping the service
                    lump.to_C(self)
                elif StatusCMD is not None:
                    logging.debug(param.OscamProcname + ' returned ' + str(StatusCMD))
                    lump.to_C(self)
            else:
                if self.OscamStatus: # now on then switch it off
                    logging.debug('Oscam - switching OFF'  + param.OscamDaemonStop)
                    self.CommandCMD = Popen(param.OscamDaemonStop, shell=True)
                else: # now off then switch it on
                    logging.debug('Oscam - switching ON ' + param.OscamDaemonStart)
                    self.CommandCMD = Popen(param.OscamDaemonStart, shell=True)
                self.ProcessingCMD = True
                self.TimeCMD = time.time()

    def update(self):
        pass

class DScreen(State):
    # Our first state
    def __init__(self, screen):
        State.__init__(self, screen)

        self.name = "RPI"
        self.description = "RPI On/Off"
        logging.debug('D - RPI')        
        
        self.processing = animation.GIFImage(param.LoadingGIF)
        self.screen.blit(param.rpion, (0,0) )

    def render(self, screen):
        if lump.is_Dd():
            self.screen.blit(param.rpioff, (0,0) )
            if time.time()-lump.starttime < 3: #wait 3 seconds before exiting/shutdowning            
                self.processing.render(screen, (5, 11))
            else:
                if param.RPI_Version is not None: #shutdown only for RPI
                    command = Popen(param.ShutdonScript)
                lump.running = False # and exit from teh app


    def update(self):
        pass

#    def handle_events(self,events):
#        #return handle_all_events(self, events)
#        return super(AScreen, self).handle_events(events)

'''
    def handle_events(self,events):
        # every State has its own eventmanagment
        for e in events:
            if e.type == QUIT:
                logging.debug('Pressed Quit (Window)')
                return False

            elif e.type == KEYDOWN:

                if e.key == K_ESCAPE:
                    logging.debug('Pressed Quit (Esc)')
                    return False
                # change State if user presses "1"
                if e.key == K_1:
                    self.manager.change(IntroState(self.screen))
                # change State if user presses "3"
                if e.key == K_3:
                    self.manager.change(GameState(self.screen))
        return True
'''

 #   def handle_events(self,events):
 #       return handle_all_events(self, events)


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




# Run the main function
if __name__ == "__main__":
    main()
