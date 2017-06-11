#!/usr/bin/env python

#######################################################
##### The main script of more-than-an-alarm-clock #####
#######################################################


#######################
##### User Config #####
#######################
# Alarm File location (Needs to be .wav file)
alarm_file = "/home/pi/Clock-Pi/Clock/Air_Horn.wav"
alarm_volume_level = 80 # How loud should the alarm be (%)

# Pin names (No longer than 6 characters)
pin_twelve_name = "Pin 12"
pin_eleven_name = "Pin 11" # Speaker relay pin
pin_ten_name = "Pin 10"
pin_nine_name = "Pin 9" # This pin can turn off with a timer

############################
##### Import Libraries #####
############################
from psutil import cpu_percent, virtual_memory
from datetime import datetime, timedelta
from os import getuid, listdir, system
from subprocess import check_output
from signal import signal, SIGTERM
from random import choice, randint
from papirus import Papirus
from requests import head
from PIL import ImageDraw
from PIL import ImageFont
import RPi.GPIO as GPIO
from smbus import SMBus
from time import sleep
from PIL import Image
import pygame.mixer

########################################
##### Define class to get CPU temp #####
########################################
class CPUTemp:
    def __init__(self, tempfilename = "/sys/class/thermal/thermal_zone0/temp"):
        self.tempfilename = tempfilename

    def __enter__(self):
        self.open()
        return self

    def open(self):
        self.tempfile = open(self.tempfilename, "r")

    def read(self):
        self.tempfile.seek(0)
        return self.tempfile.read().rstrip()

    def get_temperature(self):
        return self.get_temperature_in_c()

    def get_temperature_in_c(self):
        tempraw = self.read()
        return float(tempraw[:-3] + "." + tempraw[-3:])

    def get_temperature_in_f(self):
        return self.convert_c_to_f(self.get_temperature_in_c())

    def convert_c_to_f(self, c):
        return c * 9.0 / 5.0 + 32.0

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self.tempfile.close()

#########################################
##### Define class to get LM75 temp #####
#########################################
LM75_ADDRESS = 0x48
LM75_TEMP_REGISTER = 0
LM75_CONF_REGISTER = 1
LM75_THYST_REGISTER = 2
LM75_TOS_REGISTER = 3
LM75_CONF_SHUTDOWN = 0
LM75_CONF_OS_COMP_INT = 1
LM75_CONF_OS_POL = 2
LM75_CONF_OS_F_QUE = 3

class LM75(object):
	def __init__(self, mode=LM75_CONF_OS_COMP_INT, address=LM75_ADDRESS, busnum=1):
		self._mode = mode
		self._address = address
		self._bus = SMBus(busnum)

	def regdata2float (self, regdata):
		return (regdata / 32.0) / 8.0
	def toFah(self, temp):
		return (temp * (9.0/5.0)) + 32.0

	def getTemp(self):
		raw = self._bus.read_word_data(self._address, LM75_TEMP_REGISTER) & 0xFFFF
		raw = ((raw << 8) & 0xFF00) + (raw >> 8)
		return self.toFah(self.regdata2float(raw))

	def getTempC(self):
		raw = self._bus.read_word_data(self._address, LM75_TEMP_REGISTER) & 0xFFFF
		raw = ((raw << 8) & 0xFF00) + (raw >> 8)
		return self.regdata2float(raw)

######################################
##### Define class to get uptime #####
######################################
def get_up_stats():
    try:
        s = check_output(["uptime"])
        load_split = s.split("load average: ")
        load_five = float(load_split[1].split(",")[1])
        up = load_split[0]
        up_pos = up.rfind(",",0,len(up)-4)
        up = up[:up_pos].split("up ")[1]
        return ( up , load_five )
    except:
        return 0

########################
##### Main program #####
########################
def main():

    ######################################
    #### Check if we are run as root #####
    ######################################
    if getuid() != 0:
        raise Exception("Please run script as root")

    #################################
    ##### Create and read files #####
    #################################
    with open("/home/pi/Clock-Pi/alarm_data.csv", "r") as f: # Read alarm file
        text = f.read()
        words = text.split(",")
        alarm_hour = int(words[0])
        alarm_min = int(words[1])
        alarm_set = bool(int(words[2]))

    #######################################
    ##### Start and connect to things #####
    #######################################
    global papirus
    papirus = Papirus() # Connect to Papirus E-Ink Dislay
    sensor = LM75() # Connect to LM75 Temperature sensor
    papirus.clear() # Clear Papirus E-Ink Display

    ###################################
    ##### Define button GPIO pins #####
    ###################################
    global SW4
    SW1 = 16
    SW2 = 26
    SW3 = 20
    SW4 = 21

    ####################
    ##### Set GPIO #####
    ####################
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SW1, GPIO.IN)
    GPIO.setup(SW2, GPIO.IN)
    GPIO.setup(SW3, GPIO.IN)
    GPIO.setup(SW4, GPIO.IN)

    #######################################
    ##### Setup Papirus E-Ink Display #####
    #######################################
    global WHITE
    global BLACK
    global draw
    global width
    global height
    global clock_font
    global menu_font
    global date_font
    WHITE = 1 # Define the color White
    BLACK = 0 # Define the color Black
    image = Image.new("1", papirus.size, WHITE) # Create a blank display
    draw = ImageDraw.Draw(image)
    width, height = image.size
    FONT_FILE = "/usr/share/fonts/truetype/freefont/FreeMono.ttf" # Define font file location
    clock_font = ImageFont.truetype(FONT_FILE, 52) # Create fonts
    menu_font = ImageFont.truetype(FONT_FILE, 15)
    date_font = ImageFont.truetype(FONT_FILE, 25)

    ####################################
    ##### Define additional values #####
    ####################################
    lastMin = "00" # Create variable to store previous minute
    timer = False # Create pin 9 timer variable
    speakers_timer = False # Create speaker timer variable

    system("amixer cset numid=1 80% > /dev/null 2>&1") # Set volume level
    volume_level = 80


    #####################
    ##### Main loop #####
    #####################
    while True:
        # Wait one second
        sleep(1)

        # Get current time
        now = datetime.now()
        check_time = now.strftime("%-H%-M")
        alt_check_time = now.strftime("%H%M")
        thisMin = now.strftime("%-M")

        ###############################
        ##### Alarm functionality #####
        ###############################
        if alarm_set == True: # Is alarm set
            if (check_time == str(alarm_hour) + str(alarm_min)) or (alt_check_time == str(alarm_hour) + str(alarm_min)): # Is it time for the alarm to go off
                speakers_timer = False
                lastMin = "00" # Update display
                ten_mins = 11 # Yes, eleven because we update display and subtract one immediately
                pin_change(12, "on") # Turn lights on
                pin_change(11, "on")
                pin_change(10, "on") # Turn speaker on
                pin_change(9, "off")
                try:
                    pygame.mixer.init() # Start pygame.mixer (Audio)
                    pygame.mixer.music.load(alarm_file) # Load alarm sound
                except pygame.error:
                    pin_change(11, "off")
                    display_time()
                    draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                    draw.text((4, 40), "Incorrect/missing audio file", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    break

                system("amixer cset numid=1 " + str(alarm_volume_level) + "% > /dev/null 2>&1") # Set volume level
                while ten_mins != 0:
                    now = datetime.now()
                    thisMin = now.strftime("%-M")

                    # Update display
                    if thisMin != lastMin:
                        ten_mins -= 1
                        display_time()
                        draw.text((2, 10), " Off    Snooze", fill=BLACK, font=menu_font)
                        draw.text((4, 40), "TURN OFF THE ALARM", fill=BLACK, font=menu_font)
                        papirus.display(image)
                        lastMin = thisMin
                        papirus.update()

                    # If sound stopped, start playing
                    if pygame.mixer.music.get_busy() == False:
                        pygame.mixer.music.play()

                    # If alarm turned off, stop playing audio and exit
                    if GPIO.input(SW4) == False:
                        pygame.mixer.music.stop()
                        pygame.mixer.quit()
                        display_time()
                        draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                        draw.text((4, 40), "Alarm turned off", fill=BLACK, font=menu_font)
                        papirus.display(image)
                        papirus.update()
                        system("amixer cset numid=1 " + str(volume_level) + "% > /dev/null 2>&1")
                        break

                    # If snoozed, stop playing audio and wait five minutes
                    if GPIO.input(SW3) == False:
                        pygame.mixer.music.stop()
                        five_mins = 5
                        lastMin = 0

                        while five_mins != 0:
                            now = datetime.now()
                            thisMin = now.strftime("%-M")

                            if thisMin != lastMin:
                                five_mins -= 1
                                display_time()
                                draw.text((2, 10), " Back", fill=BLACK, font=menu_font)
                                draw.text((4, 40), "Alarm snoozed", fill=BLACK, font=menu_font)
                                papirus.display(image)
                                lastMin = thisMin
                                if "0" in thisMin:
                                    papirus.update()
                                else:
                                    papirus.partial_update()

                            # If back pressed, exit snooze
                            if GPIO.input(SW4) == False:
                                display_time()
                                draw.text((2, 10), " Off    Snooze", fill=BLACK, font=menu_font)
                                draw.text((4, 40), "TURN OFF THE ALARM", fill=BLACK, font=menu_font)
                                papirus.display(image)
                                lastMin = thisMin
                                papirus.update()
                                break

                            sleep(1)

                        lastMin = 0


        ###############################
        ##### Timer functionality #####
        ###############################
        if timer == True:
            if check_time == turn_off_led:
                pin_change(9, "off")
                timer = False

        if speakers_timer == True:
            if check_time == turn_off_speakers:
                pin_change(11, "off")
                speakers_timer = False

        ##########################
        ##### Update display #####
        ##########################
        if thisMin != lastMin:
            display_time()
            draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
            papirus.display(image)
            lastMin = thisMin
            if "0" in thisMin:
                papirus.update()
            else:
                papirus.partial_update()

            if "30" == thisMin:
                with open("/home/pi/Clock-Pi/alarm_data.csv", "r") as f:
                    text = f.read()
                    words = text.split(",")
                    alarm_hour = int(words[0])
                    alarm_min = int(words[1])
                    alarm_set = bool(int(words[2]))

        ################################
        ##### Button functionality #####
        ################################

        ########################################################################
        ##### Menu #####
        ################
        if GPIO.input(SW4) == False:
            display_time()
            draw.text((2, 10), " Back  Alarm  Power", fill=BLACK, font=menu_font)
            papirus.display(image)
            papirus.update()
            count = 0
            while (count < 30):

                ################
                ##### Back #####
                ################
                if GPIO.input(SW4) == False:
                    display_time()
                    draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    break

                #################
                ##### Alarm #####
                #################
                if GPIO.input(SW3) == False:
                    display_time()
                    draw.text((2, 10), " Back   Toggle   Status", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    count = 0
                    while (count < 30):

                        ################
                        ##### Back #####
                        ################
                        if GPIO.input(SW4) == False:
                            display_time()
                            draw.text((2, 10), " Back  Alarm  Power", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ##################
                        ##### Toggle #####
                        ##################
                        if GPIO.input(SW3) == False:
                            display_time()
                            draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                            if alarm_set == True:
                                alarm_set = False
                                with open("/home/pi/Clock-Pi/alarm_data.csv", "w") as f:
                                    f.seek(0)
                                    new_text = str(alarm_hour) + "," + str(alarm_min) + ",0"
                                    f.write(new_text)
                                draw.text((4, 40), "Alarm off at " + str(alarm_hour) + ":" + str(alarm_min), fill=BLACK, font=menu_font)
                            elif alarm_set == False:
                                alarm_set = True
                                with open("/home/pi/Clock-Pi/alarm_data.csv", "w") as f:
                                    f.seek(0)
                                    new_text = str(alarm_hour) + "," + str(alarm_min) + ",1"
                                    f.write(new_text)
                                draw.text((4, 40), "Alarm on at " + str(alarm_hour) + ":" + str(alarm_min), fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ##################
                        ##### Reload #####
                        ##################
                        if GPIO.input(SW2) == False:
                            with open("/home/pi/Clock-Pi/alarm_data.csv", "r") as f:
                                text = f.read()
                                words = text.split(",")
                                alarm_hour = int(words[0])
                                alarm_min = int(words[1])
                                alarm_set = bool(int(words[2]))
                            display_time()
                            draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                            if alarm_set == True:
                                draw.text((4, 40), "Alarm on at " + str(alarm_hour) + ":" + str(alarm_min), fill=BLACK, font=menu_font)
                            elif alarm_set == False:
                                draw.text((4, 40), "Alarm off at " + str(alarm_hour) + ":" + str(alarm_min), fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        sleep(1)
                        count = count + 1
                ###################
                ###### Power ######
                ###################
                if GPIO.input(SW2) == False:
                    display_time()
                    draw.text((2, 10), " Back   Shutdown   Reboot", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    count = 0
                    while (count < 30):

                        ################
                        ##### Back #####
                        ################
                        if GPIO.input(SW4) == False:
                            display_time()
                            draw.text((2, 10), " Back  Alarm  Power  Reload", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ####################
                        ##### Shutdown #####
                        ####################
                        if GPIO.input(SW3) == False:
                            draw.rectangle((0, 0, width, height), fill=WHITE, outline=WHITE)
                            draw.text((10, 70), "Shutting Down!", fill=BLACK, font=date_font)
                            papirus.display(image)
                            papirus.update()
                            system("shutdown -h 1") # Shutdown
                            raise SystemExit

                        ##################
                        ##### Reboot #####
                        ##################
                        if GPIO.input(SW2) == False:
                            draw.rectangle((0, 0, width, height), fill=WHITE, outline=WHITE)
                            draw.text((10, 70), "Rebooting!", fill=BLACK, font=date_font)
                            papirus.display(image)
                            papirus.update()
                            system("shutdown -r 1") # Reboot
                            raise SystemExit

                        sleep(1)
                        count = count + 1

                sleep(1)
                count = count + 1

        ########################################################################
        ##### Info #####
        ################
        if GPIO.input(SW3) == False:
            display_time()
            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
            papirus.display(image)
            papirus.update()
            count = 0
            while (count < 30):

                ################
                ##### Back #####
                ################
                if GPIO.input(SW4) == False:
                    display_time()
                    draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    break

                ################
                ##### More #####
                ################
                if GPIO.input(SW3) == False:
                    display_time()
                    draw.text((2, 10), " Back  CPU  RAM  Uptime", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    count = 0
                    while (count < 30):

                        ################
                        ##### Back #####
                        ################
                        if GPIO.input(SW4) == False:
                            display_time()
                            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        #####################
                        ##### CPU Usage #####
                        #####################
                        if GPIO.input(SW3) == False:
                            display_time()
                            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
                            draw.text((4, 40), "CPU Usage: "+ str(cpu_percent()) + "%", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ############################
                        ##### RAM/Memory usage #####
                        ############################
                        if GPIO.input(SW2) == False:
                            display_time()
                            memory = virtual_memory() # Get virtual memory usage
                            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
                            draw.text((4, 40), "RAM Usage: " + str(memory.percent) + "%", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ##################
                        ##### Uptime #####
                        ##################
                        if GPIO.input(SW1) == False:
                            display_time()
                            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
                            draw.text((4, 40), "Uptime: " + get_up_stats()[0], fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        sleep(1)
                        count = count + 1

                ################
                ##### Temp #####
                ################
                if GPIO.input(SW2) == False:
                    display_time()
                    draw.text((2, 10), " Back  LM75  CPU  EST.", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    count = 0
                    while (count < 30):

                        ################
                        ##### Back #####
                        ################
                        if GPIO.input(SW4) == False:
                            display_time()
                            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        #####################
                        ##### LM75 Temp #####
                        #####################
                        if GPIO.input(SW3) == False:
                            display_time()
                            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
                            draw.text((4, 40), "LM75 Sensor temp: " + str(sensor.getTemp()) + "F", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ####################
                        ##### CPU Temp #####
                        ####################
                        if GPIO.input(SW2) == False:
                            # Get temperature data
                            with CPUTemp() as cpu_temp:
                                cpu_temp_F = cpu_temp.get_temperature_in_f() # Get CPU Temp in Fahrenheit
                            display_time()
                            draw.text((2, 10), " Back   More   Temp", fill=BLACK, font=menu_font)
                            draw.text((4, 40), "CPU Temp: " + str(cpu_temp_F) + "F", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        sleep(1)
                        count = count + 1

                sleep(1)
                count = count + 1

        ########################################################################
        ##### Stuff #####
        #################
        if GPIO.input(SW2) == False:
            display_time()
            draw.text((2, 10), " Back   GOL   Volume   Music", fill=BLACK, font=menu_font)
            papirus.display(image)
            papirus.update()
            count = 0
            while (count < 30):

                ################
                ##### Back #####
                ################
                if GPIO.input(SW4) == False:
                    display_time()
                    draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    break

                ########################
                ##### Game Of Life #####
                ########################
                if GPIO.input(SW3) == False:
                    display_time()
                    draw.text((2, 10), " Back   Random   Gosper   R", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    count = 0
                    while (count < 30):

                        ################
                        ##### Back #####
                        ################
                        if GPIO.input(SW4) == False:
                            display_time()
                            draw.text((2, 10), " Back   GOL   Volume   Music", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        if GPIO.input(SW3) == False:
                            papirus_gol("random") # Random

                        if GPIO.input(SW2) == False:
                            papirus_gol("Gosper") # Gosper Glider Gun

                        if GPIO.input(SW1) == False: # R-Pentomino
                            papirus_gol("R-pentomino")

                        sleep(1)
                        count = count + 1

                ##################
                ##### Volume #####
                ##################
                if GPIO.input(SW2) == False:
                    display_time()
                    draw.text((2, 10), " Back   Test   Up   Down", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    count = 0
                    while (count < 60):

                        ################
                        ##### Back #####
                        ################
                        if GPIO.input(SW4) == False:
                            display_time()
                            draw.text((2, 10), " Back   GOL   Volume   Music", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ######################
                        ##### Test Alarm #####
                        ######################
                        if GPIO.input(SW3) == False:
                            speakers_timer = False
                            lastMin = "00" # Update display
                            ten_mins = 11 # Yes, eleven because we update display and subtract one immediately
                            pin_change(12, "on") # Turn lights on
                            pin_change(11, "on")
                            pin_change(10, "on") # Turn speaker on
                            pin_change(9, "off")
                            try:
                                pygame.mixer.init() # Start pygame.mixer (Audio)
                                pygame.mixer.music.load(alarm_file) # Load alarm sound
                            except pygame.error:
                                pin_change(11, "off")
                                display_time()
                                draw.text((2, 10), " Back   Test   Up   Down", fill=BLACK, font=menu_font)
                                draw.text((4, 40), "Incorrect/missing audio file", fill=BLACK, font=menu_font)
                                papirus.display(image)
                                papirus.update()
                                break

                            system("amixer cset numid=1 " + str(alarm_volume_level) + "% > /dev/null 2>&1") # Set volume level
                            while ten_mins != 0:
                                now = datetime.now()
                                thisMin = now.strftime("%-M")

                                # Update display
                                if thisMin != lastMin:
                                    ten_mins -= 1
                                    display_time()
                                    draw.text((2, 10), " Off    Snooze", fill=BLACK, font=menu_font)
                                    draw.text((4, 40), "TURN OFF THE ALARM", fill=BLACK, font=menu_font)
                                    papirus.display(image)
                                    lastMin = thisMin
                                    papirus.update()

                                # If sound stopped, start playing
                                if pygame.mixer.music.get_busy() == False:
                                    pygame.mixer.music.play()

                                # If alarm turned off, stop playing audio and exit
                                if GPIO.input(SW4) == False:
                                    pygame.mixer.music.stop()
                                    pygame.mixer.quit()
                                    display_time()
                                    draw.text((2, 10), " Back   Test   Up   Down", fill=BLACK, font=menu_font)
                                    draw.text((4, 40), "Alarm turned off", fill=BLACK, font=menu_font)
                                    papirus.display(image)
                                    papirus.update()
                                    system("amixer cset numid=1 " + str(volume_level) + "% > /dev/null 2>&1")
                                    break

                                # If snoozed, stop playing audio and wait five minutes
                                if GPIO.input(SW3) == False:
                                    pygame.mixer.music.stop()
                                    five_mins = 5
                                    lastMin = 0

                                    while five_mins != 0:
                                        now = datetime.now()
                                        thisMin = now.strftime("%-M")

                                        if thisMin != lastMin:
                                            five_mins -= 1
                                            display_time()
                                            draw.text((2, 10), " Back", fill=BLACK, font=menu_font)
                                            draw.text((4, 40), "Alarm snoozed", fill=BLACK, font=menu_font)
                                            papirus.display(image)
                                            lastMin = thisMin
                                            if "0" in thisMin:
                                                papirus.update()
                                            else:
                                                papirus.partial_update()

                                        # If back pressed, exit snooze
                                        if GPIO.input(SW4) == False:
                                            display_time()
                                            draw.text((2, 10), " Off    Snooze", fill=BLACK, font=menu_font)
                                            draw.text((4, 40), "TURN OFF THE ALARM", fill=BLACK, font=menu_font)
                                            papirus.display(image)
                                            lastMin = thisMin
                                            papirus.update()
                                            break

                                        sleep(1)

                                    lastMin = 0

                        #####################
                        ##### Volume Up #####
                        #####################
                        if GPIO.input(SW2) == False:
                            count = 0
                            volume_level = volume_level + 2
                            if volume_level > 100:
                                volume_level = 100
                            system("amixer cset numid=1 " + str(volume_level) + "% > /dev/null 2>&1")
                            volume_level_string = "Volume: " + str(volume_level) + "%"
                            display_time()
                            draw.text((2, 10), " Back   Test   Up   Down", fill=BLACK, font=menu_font)
                            draw.text((4, 40), volume_level_string, fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.partial_update()

                        #######################
                        ##### Volume Down #####
                        #######################
                        if GPIO.input(SW1) == False:
                            count = 0
                            volume_level = volume_level - 2
                            if volume_level < 0:
                                volume_level = 0
                            system("amixer cset numid=1 " + str(volume_level) + "% > /dev/null 2>&1")
                            volume_level_string = "Volume: " + str(volume_level) + "%"
                            display_time()
                            draw.text((2, 10), " Back   Test   Up   Down", fill=BLACK, font=menu_font)
                            draw.text((4, 40), volume_level_string, fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.partial_update()

                        sleep(0.5)
                        count = count + 1

                #################
                ##### Music #####
                #################
                if GPIO.input(SW1) == False:
                    speakers_timer = False
                    pin_change(11, "on") # Turn speaker on
                    audio_file = "Loading..."
                    lastMin = "00" # Update display
                    pygame.mixer.init() # Start pygame.mixer (Audio)
                    while True:
                        now = datetime.now()
                        thisMin = now.strftime("%-M")
                        if thisMin != lastMin:
                            display_time()
                            draw.text((2, 10), " Off    Skip    Up    Down", fill=BLACK, font=menu_font)
                            song_name = str(audio_file.split(".wav")[0])
                            draw.text((4, 40), "Song: " + song_name, fill=BLACK, font=menu_font)
                            papirus.display(image)
                            lastMin = thisMin
                            papirus.update()
                            sleep(0.5)

                        # If sound stopped, start playing
                        if pygame.mixer.music.get_busy() == False:
                            sleep(1)
                            try:
                                audio_file = choice(listdir("/home/pi/Clock-Pi/Music/"))
                                random_audio_file = "/home/pi/Clock-Pi/Music/" + audio_file
                                pygame.mixer.music.load(random_audio_file)
                            except pygame.error:
                                pin_change(11, "off")
                                display_time()
                                draw.text((2, 10), " Back   GOL   Volume   Music", fill=BLACK, font=menu_font)
                                draw.text((4, 40), "Incorrect/missing audio file", fill=BLACK, font=menu_font)
                                papirus.display(image)
                                papirus.update()
                                break
                            pygame.mixer.music.play()
                            lastMin = "00"

                        # If sound turned off, stop playing audio and exit
                        if GPIO.input(SW4) == False:
                            pin_change(11, "off")
                            pygame.mixer.music.stop()
                            pygame.mixer.quit()
                            display_time()
                            draw.text((2, 10), " Back   GOL   Volume   Music", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        # Skip song
                        if GPIO.input(SW3) == False:
                            pygame.mixer.music.stop()
                            audio_file = choice(listdir("/home/pi/Clock-Pi/Music/"))
                            random_audio_file = "/home/pi/Clock-Pi/Music/" + audio_file
                            pygame.mixer.music.load(random_audio_file)
                            pygame.mixer.music.play()
                            lastMin = "00"

                        # Volume Up
                        if GPIO.input(SW2) == False:
                            volume_level = volume_level + 2
                            if volume_level > 100:
                                volume_level = 100
                            system("amixer cset numid=1 " + str(volume_level) + "% > /dev/null 2>&1")
                            volume_level_string = "Volume: " + str(volume_level) + "%"
                            display_time()
                            draw.text((2, 10), " Off    Skip    Up    Down", fill=BLACK, font=menu_font)
                            draw.text((4, 40), volume_level_string, fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.partial_update()

                        # Volume Down
                        if GPIO.input(SW1) == False:
                            volume_level = volume_level - 2
                            if volume_level < 0:
                                volume_level = 0
                            system("amixer cset numid=1 " + str(volume_level) + "% > /dev/null 2>&1")
                            volume_level_string = "Volume: " + str(volume_level) + "%"
                            display_time()
                            draw.text((2, 10), " Off    Skip    Up    Down", fill=BLACK, font=menu_font)
                            draw.text((4, 40), volume_level_string, fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.partial_update()

                sleep(1)
                count = count + 1

        ########################################################################
        ##### Lights #####
        ##################
        if GPIO.input(SW1) == False:
            display_time()
            draw.text((2, 10), " Back  More  " + pin_ten_name + "   " +  pin_nine_name, fill=BLACK, font=menu_font)
            papirus.display(image)
            papirus.update()
            count = 0
            while (count < 30):

                ################
                ##### Back #####
                ################
                if GPIO.input(SW4) == False:
                    display_time()
                    draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    break

                ################
                ##### More #####
                ################
                if GPIO.input(SW3) == False:
                    display_time()
                    draw.text((2, 10), " Back  " + pin_eleven_name + "  " + pin_twelve_name + "   Off", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    count = 0
                    while (count < 30):

                        ################
                        ##### Back #####
                        ################
                        if GPIO.input(SW4) == False:
                            display_time()
                            draw.text((2, 10), " Back  More  " + pin_ten_name + "   " +  pin_nine_name, fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            break

                        ######################
                        ##### Pin Eleven #####
                        ######################
                        if GPIO.input(SW3) == False:
                            display_time()
                            draw.text((2, 10), " Back " + pin_eleven_name + " 1-Hour 2-Hours", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            count = 0
                            while (count < 30):

                                ################
                                ##### Back #####
                                ################
                                if GPIO.input(SW4) == False:
                                    display_time()
                                    draw.text((2, 10), " Back  " + pin_eleven_name + "  " + pin_twelve_name + "   Off", fill=BLACK, font=menu_font)
                                    papirus.display(image)
                                    papirus.update()
                                    break

                                #############################
                                ##### Pin eleven toggle #####
                                #############################
                                if GPIO.input(SW3) == False:
                                    display_time()
                                    draw.text((2, 10), " Back  " + pin_eleven_name + "  " + pin_twelve_name + "   Off", fill=BLACK, font=menu_font)
                                    draw.text((4, 40), pin_eleven_name + " toggled", fill=BLACK, font=menu_font)
                                    papirus.display(image)
                                    papirus.update()
                                    timer = False
                                    pin_change(11, "toggle")
                                    break

                                ##########################
                                ##### One-hour timer #####
                                ##########################
                                if GPIO.input(SW2) == False:
                                    timer = True
                                    one_hour_from_now = datetime.now() + timedelta(hours=1)
                                    turn_off_led = one_hour_from_now.strftime("%-H%-M")
                                    display_time()
                                    draw.text((2, 10), " Back  " + pin_eleven_name + "  " + pin_twelve_name + "   Off", fill=BLACK, font=menu_font)
                                    draw.text((4, 40), pin_eleven_name + " off at: " + one_hour_from_now.strftime("%-I:%M %p"), fill=BLACK, font=menu_font)
                                    papirus.display(image)
                                    papirus.update()
                                    pin_change(11, "on")
                                    break

                                ##########################
                                ##### Two-hour timer #####
                                ##########################
                                if GPIO.input(SW1) == False:
                                    timer = True
                                    two_hours_from_now = datetime.now() + timedelta(hours=2)
                                    turn_off_led = two_hours_from_now.strftime("%-H%-M")
                                    display_time()
                                    draw.text((2, 10), " Back  " + pin_eleven_name + "  " + pin_twelve_name + "   Off", fill=BLACK, font=menu_font)
                                    draw.text((4, 40), pin_eleven_name + " off at: " + two_hours_from_now.strftime("%-I:%M %p"), fill=BLACK, font=menu_font)
                                    papirus.display(image)
                                    papirus.update()
                                    pin_change(11, "on")
                                    break

                                sleep(1)
                                count = count + 1

                        ######################
                        ##### Pin Twelve #####
                        ######################
                        if GPIO.input(SW2) == False:
                            display_time()
                            draw.text((2, 10), " Back  More  " + pin_ten_name + "   " +  pin_nine_name, fill=BLACK, font=menu_font)
                            draw.text((4, 40), pin_twelve_name + " toggled", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            speakers_timer = False
                            pin_change(12, "toggle")
                            break

                        ###################
                        ##### All off #####
                        ###################
                        if GPIO.input(SW1) == False:
                            display_time()
                            draw.text((2, 10), " Back  More  " + pin_ten_name + "   " +  pin_nine_name, fill=BLACK, font=menu_font)
                            draw.text((4, 40), "All off", fill=BLACK, font=menu_font)
                            papirus.display(image)
                            papirus.update()
                            pin_change(12, "off")
                            pin_change(11, "off")
                            pin_change(10, "off")
                            pin_change(9, "off")
                            speakers_timer = False
                            timer = False
                            break

                        sleep(1)
                        count = count + 1

                ##########################
                ##### Pin ten toggle #####
                ##########################
                if GPIO.input(SW2) == False:
                    display_time()
                    draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                    draw.text((4, 40), pin_ten_name + " toggled", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    pin_change(10, "toggle")
                    break

                ##########################
                ##### Pin nine toggle ####
                ##########################
                if GPIO.input(SW1) == False:
                    display_time()
                    draw.text((2, 10), " Menu   Info   Stuff   Lights", fill=BLACK, font=menu_font)
                    draw.text((4, 40), pin_nine_name + " toggled", fill=BLACK, font=menu_font)
                    papirus.display(image)
                    papirus.update()
                    pin_change(9, "toggle")
                    break

                sleep(1)
                count = count + 1

################################################################################
##### End of main program #####
###############################

######################
##### Pin change #####
######################
def pin_change(pin, change):
    head("http://127.0.0.1/api/" + change + "/" + str(pin) + "/")

########################
##### Display Time #####
########################
def display_time():
    now = datetime.now() # Get current time
    timeString = now.strftime("%I:%M %p")
    dateString = now.strftime("%a %b %-d")
    abv_dateString = now.strftime("%-m/%-d/%y")
    draw.rectangle((0, 0, width, height), fill=WHITE, outline=WHITE)
    draw.text((5, 70), timeString, fill=BLACK, font=clock_font)
    draw.text((10, 120), dateString, fill=BLACK, font=date_font)
    draw.text((10, 145), abv_dateString, fill=BLACK, font=date_font)

#################################
##### Conway's Game Of Life #####
#################################
def papirus_gol(start_type="random"):
    CELLSIZE = 5
    #Colours the cells green for life and white for no life
    def colourGrid(draw, item, lifeDict):
        x = item[0]
        y = item[1]
        y = y * CELLSIZE # translates array into grid size
        x = x * CELLSIZE # translates array into grid size
        if lifeDict[item] == 0:
            draw.rectangle(( (x, y), (x + CELLSIZE, y + CELLSIZE) ), fill=WHITE, outline=WHITE)
        if lifeDict[item] == 1:
            draw.rectangle(( (x, y), (x + CELLSIZE, y + CELLSIZE) ), fill=BLACK, outline=WHITE)
        return None

    #Creates an dictionary of all the cells
    #Sets all cells as dead (0)
    def generateGrid(height, width):
        gridDict = {}
        #creates dictionary for all cells
        for y in range (height / CELLSIZE):
            for x in range (width / CELLSIZE):
                gridDict[x,y] = 0 #Sets cells as dead
        return gridDict

    #Assigns a 0 or a 1 to all cells
    def startingGridRandom(lifeDict):
        for item in lifeDict:
            lifeDict[item] = randint(0,1)
        return lifeDict

    def startingRpentomino(lifeDict):
        #R-pentomino
        lifeDict[28,12] = 1
        lifeDict[29,12] = 1
        lifeDict[27,13] = 1
        lifeDict[28,13] = 1
        lifeDict[28,14] = 1
        return lifeDict

    def startingGosperGliderGun(lifeDict):
        #Gosper Glider Gun
        #left square
        lifeDict[5,5] = 1
        lifeDict[5,6] = 1
        lifeDict[6,5] = 1
        lifeDict[6,6] = 1
        #left part of gun
        lifeDict[15,5] = 1
        lifeDict[15,6] = 1
        lifeDict[15,7] = 1
        lifeDict[16,4] = 1
        lifeDict[16,8] = 1
        lifeDict[17,3] = 1
        lifeDict[18,3] = 1
        lifeDict[17,9] = 1
        lifeDict[18,9] = 1
        lifeDict[19,6] = 1
        lifeDict[20,4] = 1
        lifeDict[20,8] = 1
        lifeDict[21,5] = 1
        lifeDict[21,6] = 1
        lifeDict[21,7] = 1
        lifeDict[22,6] = 1
        #right part of gun
        lifeDict[25,3] = 1
        lifeDict[25,4] = 1
        lifeDict[25,5] = 1
        lifeDict[26,3] = 1
        lifeDict[26,4] = 1
        lifeDict[26,5] = 1
        lifeDict[27,2] = 1
        lifeDict[27,6] = 1
        lifeDict[29,1] = 1
        lifeDict[29,2] = 1
        lifeDict[29,6] = 1
        lifeDict[29,7] = 1
        #right square
        lifeDict[39,3] = 1
        lifeDict[39,4] = 1
        lifeDict[40,3] = 1
        lifeDict[40,4] = 1
        return lifeDict

    #Determines how many alive neighbours there are around each cell
    def getNeighbours(epd, item,lifeDict):
        neighbours = 0
        for x in range (-1,2):
            for y in range (-1,2):
                checkCell = (item[0]+x,item[1]+y)
                if checkCell[0] < (epd.width / CELLSIZE)  and checkCell[0] >=0:
                    if checkCell[1] < (epd.height / CELLSIZE) and checkCell[1]>= 0:
                        if lifeDict[checkCell] == 1:
                            if x == 0 and y == 0: # negate the central cell
                                neighbours += 0
                            else:
                                neighbours += 1
        return neighbours

    #determines the next generation by running a "tick"
    def tick(epd, lifeDict):
        newTick = {}
        for item in lifeDict:
            #get number of neighbours for that item
            numberNeighbours = getNeighbours(epd, item, lifeDict)
            if lifeDict[item] == 1: # For those cells already alive
                if numberNeighbours < 2: # kill under-population
                    newTick[item] = 0
                elif numberNeighbours > 3: #kill over-population
                    newTick[item] = 0
                else:
                    newTick[item] = 1 # keep status quo (life)
            elif lifeDict[item] == 0:
                if numberNeighbours == 3: # cell reproduces
                    newTick[item] = 1
                else:
                    newTick[item] = 0 # keep status quo (death)
        return newTick

    #main function

    papirus.clear()

    image = Image.new("1", papirus.size, WHITE)
    draw = ImageDraw.Draw(image)

    lifeDict = generateGrid(papirus.height, papirus.width) # creates library and Populates to match blank grid

    ###Starting options
    if start_type == "random":
        lifeDict = startingGridRandom(lifeDict) # Assign random life
    elif start_type == "R-pentomino":
        lifeDict = startingRpentomino(lifeDict) # Setup R-pentomino
    elif start_type == "Gosper":
        lifeDict = startingGosperGliderGun(lifeDict) # Setup Gosper Glider Gun

    #Colours the live cells, blanks the dead
    for item in lifeDict:
        colourGrid(draw, item, lifeDict)

    while True: #main game loop

        if GPIO.input(SW4) == False:
            now = datetime.now()
            timeString = now.strftime("%I:%M %p")
            dateString = now.strftime("%a %b %-d")
            abv_dateString = now.strftime("%-m/%-d/%y")

            draw.rectangle((0, 0, width, height), fill=WHITE, outline=WHITE)

            draw.text((5, 70), timeString, fill=BLACK, font=clock_font)
            draw.text((10, 120), dateString, fill=BLACK, font=date_font)
            draw.text((10, 145), abv_dateString, fill=BLACK, font=date_font)
            draw.text((2, 10), " Back   Random   Gosper   R", fill=BLACK, font=menu_font)
            papirus.display(image)
            papirus.update()
            break

        #runs a tick
        lifeDict = tick(papirus, lifeDict)

        #Colours the live cells, blanks the dead
        for item in lifeDict:
            colourGrid(draw, item, lifeDict)

        #print("Rendering Frame")
        papirus.display(image)
        papirus.partial_update()

###############################################
##### Exit cleanly if SIGTERM is received #####
###############################################
def sigterm_handler(signal, frame):
    raise SystemExit

#########################
##### Run main loop #####
#########################
try:
    if __name__ == "__main__":
        signal(SIGTERM, sigterm_handler)
        main()

except KeyboardInterrupt:
    print ""
    system("papirus-write 'You pressed CTRL+C' > /dev/null 2>&1")
    print "You pressed CTRL+C"

except SystemExit:
    system("papirus-write 'Turned off' > /dev/null 2>&1")
    print "SystemExit raised"

except Exception as e:
    system("papirus-write 'An error occurred: " + str(e) +"' > /dev/null 2>&1")
    print "An error occurred: " + str(e)
    raise SystemExit(1)

finally:
    GPIO.cleanup() # this ensures a clean exit
