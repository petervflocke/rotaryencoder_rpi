## Local user interface via LCD and rotary knob

###Content:
- Complete application to control tvheadserver and oscam servers
- Rotary switch test program
- pygame menu system based on a finite-state machine (FSM)

**Note**
>In order to run any of the three above mentioned applications on the Raspberry PI hardware (RPI) it is necessary to install a rotary encoder knob / switch device and/or a LCD screen. [Check the hardware part for details](https://github.com/petervflocke/rpitvheadend).

###Install
**Note**
> Assumption you use the newest jessie raspian version.

If not yet done install neccessary python libraries:
- transitions, a lightweight, object-oriented finite state machine implementation in Python
- psutil

	sudo apt-get install build-essential python-dev python-pip
	sudo pip install transitions
	sudo pip instal psutil

as the pi user run:

	cd ~
	clone https github://com.gevent/petervflocke/rotaryencoder_rpi menu

To start the local control app for tvheadend and oscam use command:

	sudo python ~/menu/main.py 
	
This can be started via ssh or directly on RPI

In this repository you can find two modules, which can be easyly resused in other projects.


### Goodies: Interrupt driven rotary encoder class
The [RotaryEncoder.py](https://github.com/petervflocke/rotaryencoder_rpi/blob/master/RotaryEncoder.py) module defines a class to handle operation of a 2-bit quadrature-encoded via interrupts and save the events in a queue to be proccess subsequently by a user application.

Doing this via interrupts with an event queue, dispenses us from a repetive pooling of the current switch status and thus creates less timing requiremnst for the application end user interface loop. Interrupts approach to check the switch status reduce microprocessor load and eventually energy consuption.

In order to test your own rotary knob / switch, [follow the hadware part - "Prepare rotary switch"](https://github.com/petervflocke/rpitvheadend#prepare-rotary-switch).

Assuming that you already cloned this github repository, the code is in `menu`folder, check the code of [RotaryTest.py](https://raw.githubusercontent.com/petervflocke/rotaryencoder_rpi/master/RotaryTest.py) and correct, if neccessary used pins:

```python
A_PIN  = 17 #wiring=0 A pin on rotary
B_PIN  = 27 #wiring=2 B pin on rotary 
SW_PIN = 22 #wiring=3 press pin on rotary
```
**Note**
> Use **GPIO numbers BCM**, not pin numbers or WiringPi numbers.
> For details refer to [Wiring Pi](http://wiringpi.com/pins/) 

In the main loop 
```python
    try:
        while(True):
            print "waiting 5s"
            sleep (5)  # here you can process on RPI whatever you want and operate the rotary knob it won't be missed
            process()  # and check what has happened with rotary
    except KeyboardInterrupt:
        print "broken by keyboard"  
```
during the 5 second sleep you can operate the switch as you like. All events are collected in a queue. The queue content and a respective action(s) can be processed in the `process` function.

```python
def process():
    # this function can be called in order to decide what is happening with the switch
    while not(RotQueue.empty()):
        m=RotQueue.get_nowait()
        if m == RotaryEncoder.EventLeft:
            print "Detected one turn to the left"
            pass # add action for turning one to the left
        elif m == RotaryEncoder.EventRight:
            print "Detected one turn to the right"
            pass # add action for turning one to the left
        elif m == RotaryEncoder.EventDown:
            print "Detected press down"
            pass # add action for turning one to the left
        elif m == RotaryEncoder.EventUp:
            print "Detected release up"
            pass # add action for turning one to the left
            #exit()                   # uncomment to exit by "pressing the knob"
        RotQueue.task_done()
```

### Goodies: pygame menu system based on a finite-state machine (FSM)



Having [RotaryEncoder.py](https://github.com/petervflocke/rotaryencoder_rpi/blob/master/RotaryEncoder.py) and a [LCD Display](https://github.com/petervflocke/rpitvheadend#prepare-display) 


