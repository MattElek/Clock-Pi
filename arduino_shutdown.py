#!/usr/bin/env python

#########################################################
##### If button on Arduino pin 6 is pressed, reboot #####
#########################################################

############################
##### Import Libraries #####
############################
from pyfirmata import Arduino, util
from signal import signal, SIGTERM
from os import getuid, system
from time import sleep

###############################################
##### Exit cleanly if SIGTERM is received #####
###############################################
def sigterm_handler(signal, frame):
    raise SystemExit

#####################
##### Main Loop #####
#####################
def main():

    ######################################
    #### Check if we are run as root #####
    ######################################
    if getuid() != 0:
        raise Exception("Please run script as root")

    ##############################
    ##### Connect to Arduino #####
    ##############################
    global board
    board = Arduino("/dev/ttyACM0")
    it = util.Iterator(board)
    it.start()
    pin_four = board.get_pin("d:4:i")
    pin_four.enable_reporting()
    board.digital[13].write(1)

    while True:
        sleep(10) # Sleep for ten seconds
        button = pin_four.read() # Read button on pin four
        sleep(1)  # Wait a second
        if button == True: # If the button is pressed
            sleep(1) # Wait a second
            button = pin_four.read() # Check button on pin four again to be sure
            if button == True: # If the button is pressed
                board.digital[13].write(0) # Flash Leds
                sleep(1)
                board.digital[13].write(1)
                sleep(1)
                board.digital[13].write(0)
                sleep(1)
                board.digital[13].write(1)
                sleep(1)
                board.digital[13].write(0)
                system("shutdown -r 1")
            	raise SystemExit

try:
    if __name__ == "__main__":
        signal(SIGTERM, sigterm_handler)
        main()

except KeyboardInterrupt:
    print "You pressed CTRL+C"

except SystemExit:
    print "Rebooting!"

except Exception as e:
    print "An error occurred: " + str(e)

finally:
    board.exit()
