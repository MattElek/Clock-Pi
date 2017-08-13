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

if (whiptail --title "HomeBridge" --yesno "Do you want to install HomeBridge (HomeKit compatibility) and have it automatically run at boot?" 15 65) then
  INSTALL_HOMEBRIDGE=true
  whiptail --msgbox "HomeBridge will be installed and set to run automatically at boot. The pin when registering Clock-Pi is the HomeBridge default, 031-45-154" 10 60
else
  INSTALL_HOMEBRIDGE=false
  whiptail --msgbox "HomeBridge will not be installed." 10 60
fi

if (whiptail --title "Netatalk" --yesno "Do you want to install Netatalk? It allows you to connect to the Raspberry Pi and transfer files on a Mac from Finder." 15 65) then
  INSTALL_NETATALK=true
  whiptail --msgbox "Netatalk will be installed. Clock-Pi will show up under Shared in finder. The username and password are pi and raspberry, respectively." 10 60
else
  INSTALL_NETATALK=false
  whiptail --msgbox "Netatalk will not be installed." 10 60
fi

if (whiptail --title "Confirm" --no-button "Cancel" --yesno "Is this information correct? \n Install Main Script = true \n Install Web Backend = true \n Install Shairport Sync = $INSTALL_SHAIRPORT_SYNC \n Install HomeKit = $INSTALL_HOMEBRIDGE \n Install Netatalk = $INSTALL_NETATALK" 15 65) then
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
apt-get clean
stop_spinner $?

start_spinner "Installing apt-get Packages..."
apt-get install git i2c-tools libavformat-dev libfreetype6-dev libfuse-dev libjpeg-dev libportmidi-dev libsdl-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsmpeg-dev libswscale-dev python-dev python-imaging python-numpy python-pip python-pygame python-smbus -y > /dev/null 2>&1
stop_spinner $?
start_spinner "Installing python-pip packages..."
pip install flask psutil pyserial requests > /dev/null 2>&1
stop_spinner $?

start_spinner "Installing Main Script and Web Backend..."
bash -c '[ -d /home/pi/Clock-Pi/ ] && rm -rf /home/pi/Clock-Pi/'
git clone https://github.com/mhar9000/Clock-Pi.git -q
cat > /lib/systemd/system/arduino_shutdown.service <<EOL
[Unit]
Description=Arduino Shutdown Button
After=multi-user.target

[Service]
Type=idle
ExecStart=/usr/bin/env python /home/pi/Clock-Pi/arduino_shutdown.py

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
ExecStart=/usr/bin/env python /home/pi/Clock-Pi/Clock/clock.py

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
ExecStart=/usr/bin/env python /home/pi/Clock-Pi/Web/web.py

[Install]
WantedBy=multi-user.target
EOL
chmod 644 /lib/systemd/system/web.service
systemctl daemon-reload
systemctl enable arduino_shutdown.service -q
systemctl enable clock.service -q
systemctl enable web.service -q
rm /home/pi/Clock-Pi/Music/README.md
rm /home/pi/Clock-Pi/install.sh
rm -rf /home/pi/Clock-Pi/Pictures
chown -R pi:pi /home/pi/Clock-Pi/
stop_spinner $?

if [ "$INSTALL_SHAIRPORT_SYNC" = true ] ; then
  start_spinner "Installing Shairport-Sync prerequisites..."
  apt-get install autoconf automake avahi-daemon build-essential libasound2-dev libavahi-client-dev libconfig-dev libdaemon-dev libpopt-dev libssl-dev libtool xmltoman -y > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Downloading Shairport-Sync..."
  bash -c '[ -d /home/pi/shairport-sync/ ] && rm -rf /home/pi/shairport-sync/'
  git clone https://github.com/mikebrady/shairport-sync.git -q
  cd /home/pi/shairport-sync/
  stop_spinner $?
  start_spinner "Installing Shairport-Sync..."
  autoreconf -i -f > /dev/null 2>&1
  ./configure --with-alsa --with-avahi --with-ssl=openssl --with-systemd > /dev/null 2>&1
  make -s > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Setting Up Shairport-Sync..."
  getent group shairport-sync &> /dev/null 2>&1 || groupadd -r shairport-sync > /dev/null 2>&1
  getent passwd shairport-sync &> /dev/null 2>&1 || useradd -r -M -g shairport-sync -s /usr/bin/nologin -G audio shairport-sync > /dev/null 2>&1
  make install > /dev/null 2>&1
  systemctl enable shairport-sync -q > /dev/null 2>&1
  cd /home/pi/
  rm -rf /home/pi/shairport-sync
  cat > /usr/local/etc/shairport-sync.conf <<EOL
general =
{
name = "Clock-Pi";
drift_tolerance_in_seconds = 0;
resync_threshold_in_seconds = 0;
volume_range_db = 30 ;
};

sessioncontrol =
{
run_this_before_play_begins = "/usr/bin/curl -sSI http://localhost/api/on/12/ > /dev/null 2>&1";
run_this_after_play_ends = "/usr/bin/curl -sSI http://localhost/api/off/12/ > /dev/null 2>&1";
};
EOL
  stop_spinner $?
fi


if [ "$INSTALL_HOMEBRIDGE" = true ] ; then
  start_spinner "Installing HomeBridge prerequisites..."
  apt-get install libavahi-compat-libdnssd-dev -y > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Installing NodeJS (For HomeBridge)..."
  curl -sSL https://deb.nodesource.com/setup_7.x | bash > /dev/null 2>&1
  apt-get install nodejs -y > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Installing HomeBridge..."
  npm install -g --unsafe-perm homebridge > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Installing HomeBridge Plugins..."
  npm install -g homebridge-httpmultisensor > /dev/null 2>&1
  npm install -g homebridge-better-http-rgb > /dev/null 2>&1
  npm install -g homebridge-pi > /dev/null 2>&1
  stop_spinner $?
  start_spinner "Finishing installing HomeBridge..."
  id -u homebridge &> /dev/null || useradd -M --system homebridge > /dev/null 2>&1
  bash -c '[ -d /var/lib/homebridge ] && rm -rf /var/lib/homebridge'
  mkdir /var/lib/homebridge
  chown homebridge: /var/lib/homebridge
  chmod u+w /var/lib/homebridge
  cat > /etc/systemd/system/homebridge.service <<'EOL'
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
  mac_address_lower=$(/bin/cat /sys/class/net/eth0/address)
  mac_address="${mac_address_lower^^}"
  cat > /var/lib/homebridge/config.json <<EOL
  {
    "bridge": {
      "name": "Clock-Pi",
      "username": "$mac_address",
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
      },
      {
        "accessory": "HTTP-RGB",
        "name": "Pin 11",
        "http_method": "HEAD",
        "switch": {
          "status": "http://localhost/api/info/11/",
          "powerOn": "http://localhost/api/on/11/",
          "powerOff": "http://localhost/api/off/11/"
        }
      },
      {
        "accessory": "HTTP-RGB",
        "name": "Pin 10",
        "http_method": "HEAD",
        "switch": {
          "status": "http://localhost/api/info/10/",
          "powerOn": "http://localhost/api/on/10/",
          "powerOff": "http://localhost/api/off/10/"
        }
      },
      {
        "accessory": "HTTP-RGB",
        "name": "Pin 9",
        "http_method": "HEAD",
        "switch": {
          "status": "http://localhost/api/info/9/",
          "powerOn": "http://localhost/api/on/9/",
          "powerOff": "http://localhost/api/off/9/"
        }
      },
      {
        "accessory": "PiTemperature",
        "name": "CPU Temp"
      },
      {
        "accessory": "HttpMultisensor",
        "name": "LM75 Temp",
        "type": "CurrentTemperature",
        "manufacturer": "Default",
        "model": "Default",
        "serial": "Default",
        "url": "http://localhost/api/info/lm75/",
        "http_method": "GET",
        "debug": false
      }
    ],
    "platforms": []
  }
EOL
  systemctl daemon-reload
  systemctl enable homebridge -q > /dev/null 2>&1
  stop_spinner $?
fi


if [ "$INSTALL_NETATALK" = true ] ; then
  start_spinner "Installing Netatalk..."
  apt-get install netatalk -y > /dev/null 2>&1
  stop_spinner $?
fi

start_spinner "Enabling I2C and SPI"
raspi-config nonint do_i2c 0 > /dev/null 2>&1
raspi-config nonint do_spi 0 > /dev/null 2>&1
stop_spinner $?

start_spinner "Installing Papirus Driver..."
bash -c '[ -d /home/pi/PaPiRus/ ] && rm -rf /home/pi/PaPiRus/'
git clone https://github.com/PiSupply/PaPiRus.git -q
cd /home/pi/PaPiRus/
python setup.py install > /dev/null 2>&1
cd /home/pi
rm -rf /home/pi/PaPiRus/
cd /tmp/
bash -c '[ -d /tmp/papirus/ ] && rm -rf /tmp/papirus/'
mkdir /tmp/papirus/
cd /tmp/papirus/
git clone https://github.com/repaper/gratis.git -q
cd /tmp/papirus/gratis/
make rpi EPD_IO=epd_io.h PANEL_VERSION="V231_G2" > /dev/null 2>&1
make rpi-install EPD_IO=epd_io.h PANEL_VERSION="V231_G2" > /dev/null 2>&1
systemctl enable epd-fuse.service -q > /dev/null 2>&1
papirus-set 2.7 > /dev/null 2>&1
cd /home/pi/
rm -rf /tmp/papirus/
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
