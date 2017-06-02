# Clock-Pi
A Raspberry Pi, E Ink Display and an Arduino.

This project was born out of the need to get up in the morning. I need something loud, so my first thought was to play an audio file from a [Raspberry Pi](https://www.raspberrypi.org). I also had a [Papirus E Ink Display](https://www.pi-supply.com/product/papirus-epaper-eink-screen-hat-for-raspberry-pi/) lying around, and I went from there. This is the first project I have put on GitHub so constructive criticism is welcome.

## What this project does!
It is a combination of 3 python programs, Airplay, HomeKit, and Netatalk. I added all the Apple support because I have Apple products (Sorry android users). I already had this hardware setup, and the Raspberry Pi CPU was always under 5%, so I wondered, how much more can I pile on this Pi?
1. Script number one is the main script, clock.py, which is the front end for this project. It controls the E ink screen.
2. Script number two is the web back end, and is what allows homekit to work. It is also the only way to change the alarm time.
3. Script number three is a small but helpful addition. When a button on the arduino is pressed for ten seconds, reboots the pi. I added this in because the other scripts used to crash a lot, and I needed this to reboot.

## Parts
1. [Raspberry Pi](https://www.raspberrypi.org)
2. [Papirus E Ink Display - 2.7"](https://www.pi-supply.com/product/papirus-epaper-eink-screen-hat-for-raspberry-pi/)
3. [Arduino Uno](https://www.arduino.cc/en/Main/arduinoBoardUno), Mega and others would probably work fine
4. [PowerSwitch Tail II](http://www.powerswitchtail.com/Pages/default.aspx), regular relays work fine
5. USB-A to B, i.e. Printer Cable
6. Some Jumper wires to connect to the relays
7. Power cable for Raspberry Pi
8. A button
9. Ethernet Cable or Wifi  adapter (Not needed if using Raspberry Pi 3)

## Install:
I absolutely LOVE it when an install is easy and painless. I have tried very hard to create that, so here is a oneliner that I made. Copy and paste it into your Raspberry Pi terminal, hit enter, select some options, and let it do it's thing.

```Shell
curl -sS https://raw.githubusercontent.com/mhar9000/Clock-Pi/master/install.sh | sudo bash
```

Wire up your relays to pins 12, 11, 10, and 9 on your arduino, with the relays that the speakers are connected to wired to pin 11. Also, if you have a nightlight or something that you want to be able to turn off automatically after 1 or 2 hours, connect it to pin 9. Connect a button to pin 4 to be used as the reboot button.

Finally, connect an arduino to your computer and load the StandardFirmata example (Under File > Examples > Firmata)

Thats it!

###### Additional Configuration
You can configure the pin names to personal preference in:
1. The HomeKit app, when adding the Clock to HomeKit, you can configure custom names for the pins.
2. At the top of clock.py (located in Clock-Pi/Clock). There are some variables there that you can change.
3. In control.html (located in Web/templates/). Near the middle, you can change the pin names for the website.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
