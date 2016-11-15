## Local user interface via LCD and rotary knob

###Content:
- Complete application to control tvheadserver and oscam servers
- Rotary switch test program
- pygame menu system based on finite-state machine (FSM)

**Note**
>In order to run any of the three above mentioned applications on the Raspberry PI hardware (RPI) it is necessary to install a rotary encoder knob / switch device and/or a LCD screen. [Check the hardware part for details](https://github.com/petervflocke/rpitvheadend).

###Install
as the pi user run

	cd ~
	git clone https://github.com/petervflocke/rotaryencoder_rpi menu

To start the local control app for tvheadend and oscam use command:

	sudo python ~/menu/main.py 
	
This can be started via ssh or directly on RPI

In this repository you can find two modules, which can be easyly resused in other projects.


### Goodies: Interrupt driven rotary encoder class
The [RotaryEncoder.py](https://github.com/petervflocke/rotaryencoder_rpi/blob/master/RotaryEncoder.py) module defines a class to handle operation of a 2-bit quadrature-encoded via interrupts and save the events in a queue to be proccess subsequently by a user application.

Doing this via interrupts with an event queue, dispenses us from a repetive pooling of the current switch status and thus creates less timing requiremnst for the application end user interface loop. Interrupts approach to check the switch status reduce microprocessor load and eventually energy consuption.

In order to test yourown local rotary knob / switch, follow [follow the hadware part - "Prepare rotary switch"](https://github.com/petervflocke/rpitvheadend#prepare-rotary-switch).

If neccessary customize 
