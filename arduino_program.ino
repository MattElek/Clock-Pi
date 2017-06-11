const int pin_thirteen = 13; // Define pins.
const int pin_twelve = 12;
const int pin_eleven = 11;
const int pin_ten = 10;
const int pin_nine = 9;
const int pin_eight = 8;
bool pin_thirteen_state = false; // Define variables to store pin states
bool pin_twelve_state = false;
bool pin_eleven_state = false;
bool pin_ten_state = false;
bool pin_nine_state = false;

char rx_char = 0; // rx_char holds the received command.

void setup() {
  Serial.begin(9600); // Open serial port (9600 bauds).
  Serial.flush(); // Clear receive buffer.
  pinMode(pin_thirteen, OUTPUT);
  pinMode(pin_twelve, OUTPUT); // Sets pins as OUTPUT.
  pinMode(pin_eleven, OUTPUT);
  pinMode(pin_ten, OUTPUT);
  pinMode(pin_nine, OUTPUT);
  pinMode(pin_eight, INPUT);
}

void loop() {
  delay(100);
  if (Serial.available() > 0) { // Check receive buffer.
    rx_char = Serial.read(); // Save character received.
    Serial.flush(); // Clear receive buffer.

    switch (rx_char) {

      /*
        ########################
        ##### PIN THIRTEEN #####
        ########################
      */

      case 'Q': // Turn pin thirteen on.
        digitalWrite(pin_thirteen, HIGH);
        pin_thirteen_state = true;
        break;

      case 'q': // Turn pin thirteen off.
        digitalWrite(pin_thirteen, LOW);
        pin_thirteen_state = false;
        break;

      case 'A': // Toggle pin thirteen.
        if (pin_thirteen_state == true) { // If pin thirteen is on:
          digitalWrite(pin_thirteen, LOW); // Turn off pin thirteen.
          pin_thirteen_state = false;
        } else if (pin_thirteen_state == false) { // If pin thirteen is off:
          digitalWrite(pin_thirteen, HIGH); // Turn on pin thirteen.
          pin_thirteen_state = true;
        }
        break;

      case 'a': // Get pin thirteen status
        if (pin_thirteen_state == true) { // If pin thirteen is on:
          Serial.println("True"); // Send pin state
        } else if (pin_thirteen_state == false) { // If pin thirteen is off:
          Serial.println("False"); // Send pin state
        }
        break;

      /*
        ######################
        ##### PIN TWELVE #####
        ######################
      */

      case 'W': // Turn pin twelve on.
        digitalWrite(pin_twelve, HIGH);
        pin_twelve_state = true;
        break;

      case 'w': // Turn pin twelve off.
        digitalWrite(pin_twelve, LOW);
        pin_twelve_state = false;
        break;

      case 'S': // Toggle pin twelve.
        if (pin_twelve_state == true) { // If pin twelve is on:
          digitalWrite(pin_twelve, LOW); // Turn off pin twelve.
          pin_twelve_state = false;
        } else if (pin_twelve_state == false) { // If pin twelve is off:
          digitalWrite(pin_twelve, HIGH); // Turn on pin twelve.
          pin_twelve_state = true;
        }
        break;

      case 's': // Get pin twelve status
        if (pin_twelve_state == true) { // If pin twelve is on:
          Serial.println("True"); // Send pin state
        } else if (pin_twelve_state == false) { // If pin twelve is off:
          Serial.println("False"); // Send pin state
        }
        break;

      /*
        ######################
        ##### PIN ELEVEN #####
        ######################
      */

      case 'E': // Turn pin eleven on.
        digitalWrite(pin_eleven, HIGH);
        pin_eleven_state = true;
        break;

      case 'e': // Turn pin eleven off.
        digitalWrite(pin_eleven, LOW);
        pin_eleven_state = false;
        break;

      case 'D': // Toggle pin eleven.
        if (pin_eleven_state == true) { // If pin eleven is on:
          digitalWrite(pin_eleven, LOW); // Turn off pin eleven.
          pin_eleven_state = false;
        } else if (pin_eleven_state == false) { // If pin eleven is off:
          digitalWrite(pin_eleven, HIGH); // Turn on pin eleven.
          pin_eleven_state = true;
        }
        break;

      case 'd': // Get pin eleven status
        if (pin_eleven_state == true) { // If pin eleven is on:
          Serial.println("True"); // Send pin state
        } else if (pin_eleven_state == false) { // If pin eleven is off:
          Serial.println("False"); // Send pin state
        }
        break;

      /*
        ###################
        ##### PIN TEN #####
        ###################
      */

      case 'R': // Turn pin ten on.
        digitalWrite(pin_ten, HIGH);
        pin_ten_state = true;
        break;

      case 'r': // Turn pin ten off.
        digitalWrite(pin_ten, LOW);
        pin_ten_state = false;
        break;

      case 'F': // Toggle pin ten.
        if (pin_ten_state == true) { // If pin ten is on:
          digitalWrite(pin_ten, LOW); // Turn off pin ten.
          pin_ten_state = false;
        } else if (pin_ten_state == false) { // If pin ten is off:
          digitalWrite(pin_ten, HIGH); // Turn on pin ten.
          pin_ten_state = true;
        }
        break;

      case 'f': // Get pin ten status
        if (pin_ten_state == true) { // If pin ten is on:
          Serial.println("True"); // Send pin state
        } else if (pin_ten_state == false) { // If pin ten is off:
          Serial.println("False"); // Send pin state
        }
        break;

      /*
        ####################
        ##### PIN NINE #####
        ####################
      */

      case 'T': // Turn pin nine on.
        digitalWrite(pin_nine, HIGH);
        pin_nine_state = true;
        break;

      case 't': // Turn pin ten off.
        digitalWrite(pin_nine, LOW);
        pin_nine_state = false;
        break;

      case 'G': // Toggle pin nine.
        if (pin_nine_state == true) { // If pin nine is on:
          digitalWrite(pin_nine, LOW); // Turn off pin nine.
          pin_nine_state = false;
        } else if (pin_nine_state == false) { // If pin nine is off:
          digitalWrite(pin_nine, HIGH); // Turn on pin nine.
          pin_nine_state = true;
        }
        break;

      case 'g': // Get pin nine status
        if (pin_nine_state == true) { // If pin nine is on:
          Serial.println("True"); // Send pin state
        } else if (pin_nine_state == false) { // If pin nine is off:
          Serial.println("False"); // Send pin state
        }
        break;

      /*
        #####################
        ##### PIN EIGHT #####
        #####################
      */

      case 'h': // Get pin eight status
        if (digitalRead(pin_eight) == HIGH) { // If pin eight is on:
          Serial.println("True"); // Send pin state
        } else if (digitalRead(pin_eight) == LOW) { // If pin eight is off:
          Serial.println("False"); // Send pin state
        }
        break;

      default:
        Serial.print("'");
        Serial.print((char)rx_char);
        Serial.println("' is not a command!");
    }
  }
}
