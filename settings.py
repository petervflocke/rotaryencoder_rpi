import logging
import pygame
import os
import re

class settings(object):
    
    def __init__(self):

        # define screen site - here it is SainSmart 1.8" TFT Farb LCD Schirm Modul mit SPI Interface
        # SainSmart 1.8" TFT Farb LCD Schirm Modul mit SPI Interface
        # see: https://github.com/notro/fbtft/wiki
        self.ScreenSize = (160,128)     # size of the lcd screen for pygame module
        self.ScrenSaverTime = 60        # in seconds
        
        # define 3 pins A/B + switc in BCM GPIO mode for the rotary encoder A/B Pin + Switch   
        
        self.RPI_Version = self.pi_version()        
        
        self.A_PIN  = 17 #wiring=0
        self.B_PIN  = 27 #wiring=2
        self.SW_PIN = 22 #wiring=3
        
        self.R_PIN  = 18 # wiring=1, relay to power external device
        
        # define daemons for services to be controlled
        self.TVProcname       = "tvheadend"
        self.OscamProcname    = "oscam"
        self.TVDaemonStart    = "/usr/bin/sudo /etc/init.d/tvheadend start"
        self.TVDaemonStop     = "/usr/bin/sudo /etc/init.d/tvheadend stop"
        self.OscamDaemonStart = "/usr/bin/sudo /etc/init.d/oscam start"
        self.OscamDaemonStop  = "/usr/bin/sudo /etc/init.d/oscam stop"
        
        BaseDir=os.path.dirname(os.path.realpath(__file__))
                
        self.ShutdonScript    = os.path.join(BaseDir, "myshutdown.sh")   # own shutdown script to do all needful
        
        self.tvoff    = pygame.image.load(os.path.join(BaseDir, "res/02-tvoff.bmp"))
        self.tvon     = pygame.image.load(os.path.join(BaseDir, "res/02-tvon.bmp"))
        
        self.oscamoff = pygame.image.load(os.path.join(BaseDir, "res/03-oscamoff.bmp"))
        self.oscamon  = pygame.image.load(os.path.join(BaseDir, "res/03-oscamon.bmp"))
        
        self.rpioff   = pygame.image.load(os.path.join(BaseDir, "res/04-rpioff.bmp"))
        self.rpion    = pygame.image.load(os.path.join(BaseDir, "res/04-rpion.bmp"))
        
        # animated gif for loading/processing time delay
        self.LoadingGIF = os.path.join(BaseDir, "res/loading.gif")
        
        #print os.path.join(BaseDir, "res/DejaVuSansMono.ttf")
        self.fontpath = os.path.join(BaseDir, "res/DejaVuSansMono-Bold.ttf") 
        
        self.states      = ['A', 'B', 'B10', 'B11', 'B12', 'B13', 'C', 'Cd', 'D', 'Bd', 'Ad', 'Dd', 'S']
        self.transitions = [
                           ['R',   'A',   'B'  ],
                           ['R',   'B',   'B10'],
                           ['R',   'B10', 'C'  ],
                           ['R',   'B11', 'B12'],
                           ['R',   'C',   'D'  ],
                           ['R',   'D',   'A'  ],
                           ['L',   'A',   'D'  ],
                           ['L',   'D',   'C'  ],
                           ['L',   'C',   'B'  ],
                           ['L',   'B',   'A'  ],
                           ['L',   'B10', 'B'  ],
                           ['L',   'B11', 'B13'],
                           ['D',   'B10', 'B11'],
                           ['D',   'B11', 'B10'],
                           ['D',   'B',   'Bd' ],
                           ['D',   'A',   'Ad' ],
                           ['D',   'D',   'Dd' ],
                           ['D',   'C',   'Cd' ],
                           ['D',   'S',   'A'  ], # press, left or right leads always to the init A screen
                           ['R',   'S',   'A'  ],
                           ['L',   'S',   'A'  ]
                           ]

    def pi_version(self):
    
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
