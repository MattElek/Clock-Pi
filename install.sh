#!/usr/bin/env bash

# Make sure only root can run the script
if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root" 1>&2
  exit 1
fi

function _spinner() {
  # $1 start/stop
  #
  # on start: $2 display message
  # on stop : $2 process exit status
  #           $3 spinner function pid (supplied from stop_spinner)

  local on_success="DONE"
  local on_fail="FAIL"
  local white="\e[1;37m"
  local green="\e[1;32m"
  local red="\e[1;31m"
  local nc="\e[0m"

  case $1 in
    start)
    # calculate the column where spinner and status msg will be displayed
    let column=$(tput cols)-${#2}-8
    # display message and position the cursor in $column column
    echo -ne ${2}
    printf "%${column}s"

    # start spinner
    i=1
    sp="\|/-"
    delay=${SPINNER_DELAY:-0.15}

    while :
    do
      printf "\b${sp:i++%${#sp}:1}"
      sleep $delay
    done
    ;;
    stop)
    if [[ -z ${3} ]]; then
      echo "spinner is not running.."
      exit 1
    fi

    kill $3 > /dev/null 2>&1

    # inform the user uppon success or failure
    echo -en "\b["
    if [[ $2 -eq 0 ]]; then
      echo -en "${green}${on_success}${nc}"
    else
      echo -en "${red}${on_fail}${nc}"
      echo -e "]"
      echo ""
      echo "Something went wrong"
      echo ""
      exit 1
    fi
    echo -e "]"
    ;;
    *)
    echo "invalid argument, try {start/stop}"
    exit 1
    ;;
  esac
}

function start_spinner {
  # $1 : msg to display
  _spinner "start" "${1}" &
  # set global spinner pid
  _sp_pid=$!
  disown
}

function stop_spinner {
  # $1 : command exit status
  _spinner "stop" $1 $_sp_pid
  unset _sp_pid
}


cd /home/pi/

if (whiptail --no-button "Cancel" --yes-button "Continue" --yesno "Install script for More-Than-An-Alarm-Clock." 15 65) then
  :
else
  whiptail --msgbox "Install Canceled." 10 60
  exit 0
fi

if (whiptail --title "Shairport Sync" --yesno "Do you want to install Shairport Sync (Airplay) and have it automatically run at boot?" 15 65) then
  INSTALL_SHAIRPORT_SYNC=true
  whiptail --msgbox "Shairport Sync will be installed and set to run automatically at bootup." 10 60
else
  INSTALL_SHAIRPORT_SYNC=false
  whiptail --msgbox "Shairport Sync will not be installed." 10 60
fi

if (whiptail --title "HomeKit" --yesno "Do you want to install HomeBridge (HomeKit compatibility) and have it automatically run at boot?" 15 65) then
  INSTALL_HOMEKIT=true
  whiptail --msgbox "HomeBridge will be installed and set to run automatically at boot. The pin when registering Clock-Pi is the HomeBridge default, 031-45-154" 10 60
else
  INSTALL_HOMEKIT=false
  whiptail --msgbox "HomeBridge will not be installed." 10 60
fi

if (whiptail --title "Netatalk" --yesno "Do you want to install Netatalk? It allows you to connect to the Raspberry Pi and transfer files on a Mac from Finder." 15 65) then
  INSTALL_NETATALK=true
  whiptail --msgbox "Netatalk will be installed. Clock-Pi will show up under Shared in finder. The username and password are pi and raspberry, respectively." 10 60
else
  INSTALL_NETATALK=false
  whiptail --msgbox "Netatalk will not be installed." 10 60
fi

if (whiptail --title "Confirm" --no-button "Cancel" --yesno "Is this information correct? \n Install Main Script = true \n Install Web Backend = true \n Install Shairport Sync = $INSTALL_SHAIRPORT_SYNC \n Install HomeKit = $INSTALL_HOMEKIT \n Install Netatalk = $INSTALL_NETATALK" 15 65) then
  :
else
  whiptail --msgbox "Install Canceled." 10 60
  exit 0
fi

if (whiptail --title "Confirm" --yes-button "Continue" --no-button "Cancel" --defaultno --yesno "The install will take about 10-30 minutes." 15 65) then
  whiptail --msgbox "Press Enter to begin the install. This script takes a while, so be patient. As long as the spinner is spinning it hasn't crashed." 10 60
else
  whiptail --msgbox "Install Canceled." 10 60
  exit 0
fi

clear
echo ""

start_spinner "Updating Packages..."
apt-get update > /dev/null 2>&1
stop_spinner $?
start_spinner "Upgrading Packages..."
apt-get upgrade -y > /dev/null 2>&1
apt-get dist-upgrade -y > /dev/null 2>&1
apt-get autoremove -y > /dev/null 2>&1
apt-get clean > /dev/null 2>&1
stop_spinner $?

start_spinner "Installing apt-get Packages..."
apt-get install bc git i2c-tools libavformat-dev libfreetype6-dev libfuse-dev libjpeg-dev libportmidi-dev libsdl-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsmpeg-dev libswscale-dev python-dev python-imaging python-numpy python-pip python-pygame python-smbus -y > /dev/null 2>&1
stop_spinner $?
start_spinner "Installing python-pip packages..."
pip install flask psutil pyfirmata requests > /dev/null 2>&1
stop_spinner $?

start_spinner "Installing Main Script and Web Backend..."
git clone https://github.com/mhar9000/Clock-Pi.git > /dev/null 2>&1
cat > /lib/systemd/system/arduino_shutdown.service <<EOL
[Unit]
Description=Arduino Shutdown Button
After=multi-user.target

[Service]
Type=idle
ExecStart=/usr/bin/python /home/pi/Clock-Pi/arduino_shutdown.py

[Install]
WantedBy=multi-user.target
EOL
chmod 644 /lib/systemd/system/arduino_shutdown.service
cat > /lib/systemd/system/clock.service <<EOL
[Unit]
Description=More-Than-An-Alarm-Clock Front End Script
After=multi-user.target

[Service]
Type=idle
ExecStart=/usr/bin/python /home/pi/Clock-Pi/Clock/clock.py

[Install]
WantedBy=multi-user.target
EOL
chmod 644 /lib/systemd/system/clock.service
cat > /lib/systemd/system/web.service <<EOL
[Unit]
Description=More-Than-An-Alarm-Clock Web Script
After=multi-user.target

[Service]
Type=idle
ExecStart=/usr/bin/python /home/pi/Clock-Pi/Web/web.py

[Install]
WantedBy=multi-user.target
EOL
chmod 644 /lib/systemd/system/web.service
systemctl daemon-reload
systemctl enable arduino_shutdown.service > /dev/null 2>&1
systemctl enable clock.service > /dev/null 2>&1
systemctl enable web.service > /dev/null 2>&1
rm /home/pi/Clock-Pi/Music/README.md > /dev/null 2>&1
rm -rf /home/pi/Clock-Pi/.git > /dev/null 2>&1
chown -R pi:pi /home/pi/Clock-Pi/ > /dev/null 2>&1
stop_spinner $?

if [ "$INSTALL_SHAIRPORT_SYNC" = true ] ; then
  start_spinner "Installing Shairport-Sync prerequisites..."
  apt-get install autoconf automake avahi-daemon build-essential libasound2-dev libavahi-client-dev libconfig-dev libdaemon-dev libpopt-dev libssl-dev libtool xmltoman -y > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Downloading Shairport-Sync..."
  git clone https://github.com/mikebrady/shairport-sync.git > /dev/null 2>&1
  cd /home/pi/shairport-sync > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Installing Shairport-Sync..."
  autoreconf -i -f > /dev/null 2>&1
  ./configure --with-alsa --with-avahi --with-ssl=openssl --with-systemd > /dev/null 2>&1
  make > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Setting Up Shairport-Sync..."
  getent group shairport-sync &>/dev/null || groupadd -r shairport-sync >/dev/null
  getent passwd shairport-sync &> /dev/null || useradd -r -M -g shairport-sync -s /usr/bin/nologin -G audio shairport-sync >/dev/null
  make install > /dev/null 2>&1
  systemctl enable shairport-sync > /dev/null 2>&1
  cd /home/pi
  rm -rf /home/pi/shairport-sync
  cat > /usr/local/etc/shairport-sync.conf <<EOL
  // Sample Configuration File for Shairport Sync
  // Commented out settings are generally the defaults, except where noted.

  // General Settings
  general =
  {
  name = "Clock-Pi"; // This means "Hostname" -- see below. This is the name the service will advertise to iTunes.
  //		The default is "Hostname" -- i.e. the machine's hostname with the first letter capitalised (ASCII only.)
  //		You can use the following substitutions:
  //				%h for the hostname,
  //				%H for the Hostname (i.e. with first letter capitalised (ASCII only)),
  //				%v for the version number, e.g. 3.0 and
  //				%V for the full version string, e.g. 3.0-OpenSSL-Avahi-ALSA-soxr-metadata-sysconfdir:/etc
  //		Overall length can not exceed 50 characters. Example: "Shairport Sync %v on %H".
  //	password = "secret"; // leave this commented out if you don't want to require a password
  //	interpolation = "basic"; // aka "stuffing". Default is "basic", alternative is "soxr". Use "soxr" only if you have a reasonably fast processor.
  //	output_backend = "alsa"; // Run "shairport-sync -h" to get a list of all output_backends, e.g. "alsa", "pipe", "stdout". The default is the first one.
  //	mdns_backend = "avahi"; // Run "shairport-sync -h" to get a list of all mdns_backends. The default is the first one.
  //	port = 5000; // Listen for service requests on this port
  // 	udp_port_base = 6001; // start allocating UDP ports from this port number when needed
  //	udp_port_range = 100; // look for free ports in this number of places, starting at the UDP port base (only three are needed).
  //	statistics = "no"; // set to "yes" to print statistics in the log
  drift_tolerance_in_seconds = 0; // allow a timing error of this number of seconds of drift away from exact synchronisation before attempting to correct it
  resync_threshold_in_seconds = 0; // a synchronisation error greater than this number of seconds will cause resynchronisation; 0 disables it
  //	log_verbosity = 0; // "0" means no debug verbosity, "3" is most verbose.
  //	ignore_volume_control = "no"; // set this to "yes" if you want the volume to be at 100% no matter what the source's volume control is set to.
  volume_range_db = 30 ; // use this advanced setting to set the range, in dB, you want between the maximum volume and the minimum volume. Range is 30 to 150 dB. Leave it commented out to use mixer's native range.
  //	volume_max_db = 0.0 ; // use this advanced setting, which must have a decimal point in it, to set the maximum volume, in dB, you wish to use.
  //		The setting is for the hardware mixer, if chosen, or the software mixer otherwise. The value must be in the mixer's range (0.0 to -96.2 for the software mixer).
  //		Leave it commented out to use mixer's maximum volume.
  //	regtype = "_raop._tcp"; // Use this advanced setting to set the service type and transport to be advertised by Zeroconf/Bonjour. Default is "_raop._tcp".
  //	playback_mode = "stereo"; // This can be "stereo", "mono", "reverse stereo", "both left" or "both right". Default is "stereo".
  //	alac_decoder = "hammerton"; // This can be "hammerton" or "apple". This advanced setting allows you to choose
  //		the original Shairport decoder by David Hammerton or the Apple Lossless Audio Codec (ALAC) decoder written by Apple.
  //	interface = "name"; // Use this advanced setting to specify the interface on which Shairport Sync should provide its service. Leave it commented out to get the default, which is to select the interface(s) automatically.
  };

  // How to deal with metadata, including artwork
  metadata =
  {
  //	enabled = "no"; // set this to yes to get Shairport Sync to solicit metadata from the source and to pass it on via a pipe
  //	include_cover_art = "no"; // set to "yes" to get Shairport Sync to solicit cover art from the source and pass it via the pipe. You must also set "enabled" to "yes".
  //	pipe_name = "/tmp/shairport-sync-metadata";
  //	pipe_timeout = 5000; // wait for this number of milliseconds for a blocked pipe to unblock before giving up
  //	socket_address = "226.0.0.1"; // if set to a host name or IP address, UDP packets containing metadata will be sent to this address. May be a multicast address. "socket-port" must be non-zero and "enabled" must be set to yes"
  //	socket_port = 5555; // if socket_address is set, the port to send UDP packets to
  //	socket_msglength = 65000; // the maximum packet size for any UDP metadata. This will be clipped to be between 500 or 65000. The default is 500.
  };

  // Advanced parameters for controlling how a Shairport Sync runs
  sessioncontrol =
  {
  run_this_before_play_begins = "/usr/bin/curl http://localhost/api/on/11/ > /dev/null 2>&1"; // make sure the application has executable permission. It it's a script, include the #!... stuff on the first line
  run_this_after_play_ends = "//usr/bin/curl http://localhost/api/off/11/ > /dev/null 2>&1"; // make sure the application has executable permission. It it's a script, include the #!... stuff on the first line
  //	wait_for_completion = "no"; // set to "yes" to get Shairport Sync to wait until the "run_this..." applications have terminated before continuing
  //	allow_session_interruption = "no"; // set to "yes" to allow another device to interrupt Shairport Sync while it's playing from an existing audio source
  //	session_timeout = 120; // wait for this number of seconds after a source disappears before terminating the session and becoming available again.
  };

  // Back End Settings

  // These are parameters for the "alsa" audio back end, the only back end that supports synchronised audio.
  alsa =
  {
  //  output_device = "default"; // the name of the alsa output device. Use "alsamixer" or "aplay" to find out the names of devices, mixers, etc.
  //  mixer_control_name = "PCM"; // the name of the mixer to use to adjust output volume. If not specified, volume in adjusted in software.
  //  mixer_device = "default"; // the mixer_device default is whatever the output_device is. Normally you wouldn't have to use this.
  //  output_rate = 44100; // can be 44100, 88200, 176400 or 352800, but the device must have the capability.
  //  output_format = "S16"; // can be "U8", "S8", "S16", "S24", "S24_3LE", "S24_3BE" or "S32", but the device must have the capability. Except where stated using (*LE or *BE), endianness matches that of the processor.
  //  audio_backend_latency_offset_in_seconds = 0.0; // Set this offset to compensate for a fixed delay in the audio back end. E.g. if the output device delays by 100 ms, set this to -0.1.
  //  audio_backend_buffer_desired_length_in_seconds = 0.15; // If set too small, buffer underflow occurs on low-powered machines. Too long and the response times with software mixer become annoying.
  //  disable_synchronization = "no"; // Set to "yes" to disable synchronization. Default is "no".
  //  period_size = <number>; // Use this optional advanced setting to set the alsa period size near to this value
  //  buffer_size = <number>; // Use this optional advanced setting to set the alsa buffer size near to this value
  //  use_mmap_if_available = "yes"; // Use this optional advanced setting to control whether MMAP-based output is used to communicate  with the DAC. Default is "yes"
  };

  // These are parameters for the "pipe" audio back end, a back end that directs raw CD-style audio output to a pipe. No interpolation is done.
  pipe =
  {
  //  name = "/path/to/pipe"; // there is no default pipe name for the output
  //  audio_backend_latency_offset = 0.0; // Set this offset in seconds to compensate for a fixed delay in the audio back end. E.g. if the output device delays by 100 ms, set this to -0.1.
  //  audio_backend_buffer_desired_length = 1.0;  // Having started to send audio at the right time, send all subsequent audio this much ahead of time, creating a buffer this length.
  };

  // These are parameters for the "stdout" audio back end, a back end that directs raw CD-style audio output to stdout. No interpolation is done.
  stdout =
  {
  //  audio_backend_latency_offset = 0.0; // Set this offset in seconds to compensate for a fixed delay in the audio back end. E.g. if the output device delays by 100 ms, set this to -0.1.
  //  audio_backend_buffer_desired_length = 1.0;  // Having started to send audio at the right time, send all subsequent audio this much ahead of time, creating a buffer this length.
  };

  // These are parameters for the "ao" audio back end. No interpolation is done.
  ao =
  {
  //  audio_backend_latency_offset = 0.0; // Set this offset in seconds to compensate for a fixed delay in the audio back end. E.g. if the output device delays by 100 ms, set this to -0.1.
  //  audio_backend_buffer_desired_length = 1.0;  // Having started to send audio at the right time, send all subsequent audio this much ahead of time, creating a buffer this length.
  };

  // Static latency settings are deprecated and the settings have been removed.
EOL
  stop_spinner $?
fi


if [ "$INSTALL_HOMEKIT" = true ] ; then
  start_spinner "Installing HomeBridge prerequisites..."
  apt-get install libavahi-compat-libdnssd-dev -y > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Installing NodeJS (For HomeBridge)..."
  curl -sL https://deb.nodesource.com/setup_7.x | bash -  > /dev/null 2>&1
  apt-get install -y nodejs > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Installing HomeBridge..."
  npm install -g --unsafe-perm homebridge > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Installing HomeBridge Plugins..."
  npm install -g homebridge-better-http-rgb > /dev/null 2>&1
  npm install -g homebridge-http-temperature > /dev/null 2>&1
  npm install -g homebridge-pi > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Finishing installing HomeBridge..."
  useradd -M --system homebridge > /dev/null 2>&1
  mkdir /var/lib/homebridge > /dev/null 2>&1
  chown homebridge: /var/lib/homebridge > /dev/null 2>&1
  chmod u+w /var/lib/homebridge > /dev/null 2>&1
  cat > /etc/systemd/system/homebridge.service <<EOL
[Unit]
Description=Node.js HomeKit Server
After=syslog.target network-online.target

[Service]
Type=simple
User=homebridge
EnvironmentFile=/etc/default/homebridge
# Adapt this to your specific setup (could be /usr/bin/homebridge)
# See comments below for more information
ExecStart=/usr/bin/homebridge $HOMEBRIDGE_OPTS
Restart=on-failure
RestartSec=10
KillMode=process

[Install]
WantedBy=multi-user.target
EOL
  cat > /etc/default/homebridge <<EOL
# Defaults / Configuration options for homebridge
# The following settings tells homebridge where to find the config.json file and where to persist the data (i.e. pairing and others)
HOMEBRIDGE_OPTS=-U /var/lib/homebridge

# If you uncomment the following line, homebridge will log more
# You can display this via systemd's journalctl: journalctl -f -u homebridge
# DEBUG=*
EOL
  cat > /etc/systemd/system/homebridge.service <<EOL
{
  "bridge": {
    "name": "Clock-Pi",
    "username": "CC:22:3D:E3:CE:30",
    "port": 51826,
    "pin": "031-45-154"
  },

  "description": "More-Than-An-Alarm-Clock",

  "accessories": [
  {
    "accessory": "HTTP-RGB",
    "name": "Pin 12",
    "http_method": "HEAD",

    "switch": {
      "status": "http://localhost/api/info/12/",
      "powerOn": "http://localhost/api/on/12/",
      "powerOff": "http://localhost/api/off/12/"
    }
  }, {
    "accessory": "HTTP-RGB",
    "name": "Pin 11",
    "http_method": "HEAD",

    "switch": {
      "status": "http://localhost/api/info/11/",
      "powerOn": "http://localhost/api/on/11/",
      "powerOff": "http://localhost/api/off/11/"
    }
  }, {
    "accessory": "HTTP-RGB",
    "name": "Pin 10",
    "http_method": "HEAD",

    "switch": {
      "status": "http://localhost/api/info/10/",
      "powerOn": "http://localhost/api/on/10/",
      "powerOff": "http://localhost/api/off/10/"
    }
  }, {
    "accessory": "HTTP-RGB",
    "name": "Pin 9",
    "http_method": "HEAD",

    "switch": {
      "status": "http://localhost/api/info/9/",
      "powerOn": "http://localhost/api/on/9/",
      "powerOff": "http://localhost/api/off/9/"
    }
  }, {
    "accessory": "PiTemperature",
    "name": "CPU Temp"
  }, {
    "accessory": "HttpTemperature",
    "name": "LM75 Temp",
    "url": "http://localhost/api/info/temperature/",
    "http_method": "GET"
  }
  ],

  "platforms": []
}
EOL
  systemctl daemon-reload > /dev/null 2>&1
  systemctl enable homebridge > /dev/null 2>&1
  stop_spinner $?
fi


if [ "$INSTALL_NETATALK" = true ] ; then
  start_spinner "Installing Netatalk..."
  apt-get install netatalk -y > /dev/null 2>&1
  stop_spinner $?
fi

start_spinner "Enabling I2C and SPI"
raspi-config nonint do_i2c 0
raspi-config nonint do_spi 0
stop_spinner $?

start_spinner "Installing Papirus Driver..."
git clone https://github.com/PiSupply/PaPiRus.git > /dev/null 2>&1
cd PaPiRus > /dev/null 2>&1
python setup.py install > /dev/null 2>&1
rm -rf /home/pi/PaPiRus/
mkdir /tmp/papirus
cd /tmp/papirus
git clone https://github.com/repaper/gratis.git > /dev/null 2>&1
cd /tmp/papirus/gratis
make rpi EPD_IO=epd_io.h PANEL_VERSION="V231_G2" > /dev/null 2>&1
make rpi-install EPD_IO=epd_io.h PANEL_VERSION="V231_G2" > /dev/null 2>&1
systemctl enable epd-fuse.service > /dev/null 2>&1
papirus-set 2.7 > /dev/null 2>&1
stop_spinner $?

whiptail --msgbox "Install sucsessful!" 10 60

echo ""
echo "###############################"
echo "##### Install sucsessful! #####"
echo "###############################"

if (whiptail --yesno "Reboot now?" 15 65) then
  echo ""
  echo "######################"
  echo "##### Rebooting! #####"
  echo "######################"
  reboot
else
  whiptail --msgbox "You must reboot for the changes to to take effect" 10 60
  echo ""
  echo "#############################################################"
  echo "##### You must reboot for the changes to to take effect #####"
  echo "#############################################################"
  exit 0
fi
