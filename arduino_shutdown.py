#!/usr/bin/env python

#########################################################
##### If button on Arduino pin 6 is pressed, reboot #####
#########################################################

############################
##### Import Libraries #####
############################
from signal import signal, SIGTERM
from os import getuid, system
from serial import Serial
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
    board = Serial("/dev/ttyACM0") # Connect to Arduino
    board.timeout = 2
    board.write("Q")

    while True:
        sleep(10) # Sleep for ten seconds
        board.write("h")
        sleep(1)  # Wait a second
        rx_bytes = board.readline()
        if "True" in rx_bytes:
            board.write("h")
            sleep(1) # Wait a second
            rx_bytes = board.readline()
            if "True" in rx_bytes:
                board.write("q") # Flash Leds
                sleep(1)
                board.write("Q")
                sleep(1)
                board.write("q")
                sleep(1)
                board.write("Q")
                sleep(1)
                board.write("q")
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
