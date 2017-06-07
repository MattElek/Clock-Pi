#!/usr/bin/env python

######################################################
##### The Server-end of more-than-an-alarm-clock #####
######################################################

############################
##### Import libraries #####
############################
from flask import Flask, redirect, render_template, request, url_for
from psutil import cpu_percent, virtual_memory
from os import getuid, path, system
from subprocess import check_output
from pyfirmata import Arduino, util
from signal import signal, SIGTERM
from datetime import datetime
from smbus import SMBus
from time import sleep

######################################
#### Check if we are run as root #####
######################################
if getuid() != 0:
    raise Exception("Please run script as root")

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

###############################################
##### Exit cleanly if SIGTERM is received #####
###############################################
def sigterm_handler(signal, frame):
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()
    raise SystemExit



########################
##### Main program #####
########################

#######################################
##### Start and connect to things #####
#######################################
board = Arduino("/dev/ttyACM0") # Connect to Arduino
sensor = LM75() # Connect to LM75 Temperature sensor
app = Flask(__name__) # Create flask object

#################################
##### Create and read files #####
#################################
with open("/home/pi/Clock-Pi/alarm_data.csv", "r") as f: # Read alarm file
    text = f.read()
    words = text.split(",")
    alarm_hour = int(words[0])
    alarm_min = int(words[1])
    alarm_set = bool(int(words[2]))

######################
##### Info Panel #####
######################
@app.route("/")
def index():
    now = datetime.now()
    timeString = now.strftime("%m/%d/%Y, %I:%M:%S %p") # Get the current time

    # Get temperature data
    with CPUTemp() as cpu_temp:
        cpu_temp_F = cpu_temp.get_temperature_in_f() # Get CPU Temp in Fahrenheit
        cpu_temp_C = cpu_temp.get_temperature_in_c()
    cpu_temp_C = str(cpu_temp_C).split(".")[0]
    ambient = str(sensor.getTempC()).split(".")[0]
    est_temp = sensor.toFah(int(ambient) - ((int(cpu_temp_C) - int(ambient)) / 0.8))

    memory = virtual_memory() # Get virtual memory usage

    templateData = {
        "time": timeString,
        "uptime": get_up_stats()[0], # Get uptime stats
        "sensor_temp": sensor.getTemp(), # Get LM75 temp
        "est_temp": est_temp,
        "cpu_temp": cpu_temp_F,
        "cpu_percent": str(cpu_percent()) + "%", # Get CPU percent
        "virtual_memory": str(memory.percent) + "%",
    }
    return render_template("index.html", **templateData)

#########################
##### Control Panel #####
#########################
@app.route("/control/")
def control():
    now = datetime.now()
    timeString = now.strftime("%m/%d/%Y, %I:%M:%S %p") # Get the current time
    global pin_twelve
    global pin_eleven
    global pin_ten
    global pin_nine
    # Get temperature data
    with CPUTemp() as cpu_temp:
        cpu_temp_F = cpu_temp.get_temperature_in_f() # Get CPU Temp in Fahrenheit
        cpu_temp_C = cpu_temp.get_temperature_in_c()
    cpu_temp_C = str(cpu_temp_C).split(".")[0]
    ambient = str(sensor.getTempC()).split(".")[0]
    est_temp = sensor.toFah(int(ambient) - ((int(cpu_temp_C) - int(ambient)) / 0.8))

    memory = virtual_memory() # Get virtual memory usage

    templateData = {
        "title": "Control Panel",
        "time": timeString,
        "uptime": get_up_stats()[0], # Get uptime stats
        "sensor_temp": sensor.getTemp(), # Get LM75 temp
        "est_temp": est_temp,
        "cpu_temp": cpu_temp_F,
        "cpu_percent": str(cpu_percent()) + "%", # Get CPU percent
        "virtual_memory": str(memory.percent) + "%",
        "pin_twelve": pin_twelve,
        "pin_eleven": pin_eleven,
        "pin_ten": pin_ten,
        "pin_nine": pin_nine,
    }
    return render_template("control.html", **templateData)

#########################
##### Alarm Control #####
#########################
@app.route("/control/alarm/", methods=["GET", "POST"])
def alarm_control():
    if request.method == "POST": # If alarm data updated
        alarm_set = bool(int(request.form["on_or_off"]))
        try: # Try getting alarm time
            usr_time = request.form["usr_time"].split(":")
            alarm_hour = usr_time[0]
            alarm_min = usr_time[1]
        except: # Try getting alarm data different way
            alarm_hour = request.form["hour"]
            alarm_min = request.form["minute"]

        # Write alarm data to file
        with open("/home/pi/Clock-Pi/alarm_data.csv", "w") as f:
            f.seek(0)
            if alarm_set == True:
                new_text = str(alarm_hour) + "," + str(alarm_min) + "," + "1"
            elif alarm_set == False:
                new_text = str(alarm_hour) + "," + str(alarm_min) + "," + "0"
            f.write(new_text)

        return redirect(url_for("alarm_control"))

    elif request.method == "GET": # If its just a normal page request
        now = datetime.now()
        timeString = now.strftime("%m/%d/%Y, %I:%M:%S %p") # Get the current time

        with open("/home/pi/Clock-Pi/alarm_data.csv", "r") as f: # Read alarm file
            text = f.read()
            words = text.split(",")
            alarm_hour = int(words[0])
            alarm_min = int(words[1])
            alarm_set = bool(int(words[2]))

        # Make sure wording is correct
        if alarm_set == True:
            alarm_set_str = "set for"
        elif alarm_set == False:
            alarm_set_str = "not set for"

        templateData = {
                    "time": timeString,
                    "alarm_on_or_off": alarm_set_str,
                    "alarm_time": str(alarm_hour) + ":" + str(alarm_min)
        }
        return render_template("alarm.html", **templateData)

###########################
##### HomeBridge Temp #####
###########################
@app.route("/api/info/temperature/")
def temperature():
    return "{ " + '"temperature": ' + str(sensor.getTempC()) + " }"

################################
##### HomeBridge pin state #####
################################
@app.route("/api/info/<pin>/")
def homekit_pins(pin):
    global pin_twelve
    global pin_eleven
    global pin_ten
    global pin_nine
    if pin == "12":
        if pin_twelve == True:
            return "1"
        elif pin_twelve == False:
            return "0"
    elif pin == "11":
        if pin_eleven == True:
            return "1"
        elif pin_eleven == False:
            return "0"
    elif pin == "10":
        if pin_ten == True:
            return "1"
        elif pin_ten == False:
            return "0"
    elif pin == "9":
        if pin_nine == True:
            return "1"
        elif pin_nine == False:
            return "0"

#######################
##### Pin control #####
#######################
@app.route("/api/<action>/<pin>/", methods=["GET", "HEAD"])
def pin_control(action, pin):
    global pin_twelve
    global pin_eleven
    global pin_ten
    global pin_nine
    if str(action) == "on":
        if pin == "12":
            board.digital[12].write(1)
            pin_twelve = True
        elif pin == "11":
            board.digital[11].write(1)
            pin_eleven = True
        elif pin == "10":
            board.digital[10].write(1)
            pin_ten = True
        elif pin == "9":
            board.digital[9].write(1)
            pin_nine = True

    elif str(action) == "off":
        if pin == "12":
            board.digital[12].write(0)
            pin_twelve = False
        elif pin == "11":
            board.digital[11].write(0)
            pin_eleven = False
        elif pin == "10":
            board.digital[10].write(0)
            pin_ten = False
        elif pin == "9":
            board.digital[9].write(0)
            pin_nine = False

    elif str(action) == "toggle":
        if pin == "12":
            if pin_twelve == True:
                board.digital[12].write(0)
                pin_twelve = False
            else:
                board.digital[12].write(1)
                pin_twelve = True

        elif pin == "11":
            if pin_eleven == True:
                board.digital[11].write(0)
                pin_eleven = False
            else:
                board.digital[11].write(1)
                pin_eleven = True

        elif pin == "10":
            if pin_ten == True:
                board.digital[10].write(0)
                pin_ten = False
            else:
                board.digital[10].write(1)
                pin_ten = True

        elif pin == "9":
            if pin_nine == True:
                board.digital[9].write(0)
                pin_nine = False
            else:
                board.digital[9].write(1)
                pin_nine = True

    if request.method == "GET":
        return redirect(url_for("control"))
    elif request.method == "HEAD":
        return '', 200

######################
##### Disclaimer #####
######################
@app.route("/disclaimer/")
def disclaimer():
    return render_template("disclaimer.html")

###############################
##### Reboot confirmation #####
###############################
@app.route("/reboot/ask/")
def rebootask():
    templateData = {
       "title" : "Are you sure?",
       "text" : "Are you sure that you want to reboot the raspberry pi?",
       "rebootask" : "Yes"
    }
    return render_template("power.html", **templateData)

##################
##### Reboot #####
##################
@app.route("/reboot/")
def reboot():
    system("shutdown -r 1") # Reboot
    templateData = {
       "title" : "Rebooting...",
       "text" : "The system is going down for reboot"
    }
    return render_template("power.html", **templateData)

#################################
##### Shutdown confirmation #####
#################################
@app.route("/shutdown/ask/")
def shutdownask():
    templateData = {
       "title" : "Are you sure?",
       "text" : "Are you sure that you want to shutdown the raspberry pi?",
       "shutdownask" : "Yes"
    }
    return render_template("power.html", **templateData)

####################
##### Shutdown #####
####################
@app.route("/shutdown/")
def shutdown():
    system("shutdown -h 1") # Shutdown
    templateData = {
        "title" : "Shutting down...",
        "text" : "The system is going down for system halt"
    }
    return render_template("power.html", **templateData)

####################
##### 404 Page #####
####################
@app.errorhandler(404)
def page_not_found(e):
    return render_template("error/404.html"), 404

####################
##### 403 Page #####
####################
@app.errorhandler(403)
def forbidden(e):
    return render_template("error/403.html"), 403

####################
##### 410 Page #####
####################
@app.errorhandler(410)
def page_gone(e):
    return render_template("error/410.html"), 410

####################
##### 500 Page #####
####################
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("error/500.html"), 500


##########################
##### Start Web Page #####
##########################
try:
    if __name__ == "__main__":
        ############################
        ##### Define Pin State #####
        ############################
        global pin_twelve
        global pin_eleven
        global pin_ten
        global pin_nine
        pin_twelve = False
        pin_eleven = False
        pin_ten = False
        pin_nine = False

        signal(SIGTERM, sigterm_handler)
        app.run(host="0.0.0.0", port=80, debug=False)

except KeyboardInterrupt:
    print "You pressed CTRL+C"

except SystemExit:
    print "SystemExit raised"

except Exception as e:
    print "An error occurred: " + str(e)

finally:
    board.exit()
