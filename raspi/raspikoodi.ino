#include <Arduino.h>
#include <AccelStepper.h>
#include <PID_v1.h>

// Stepper pinnit venttiilille
const int stepPinValve = 2;
const int dirPinValve = 3;
const int enablePinValve = 4;

// sama sweepperille
const int stepPinSweeper = 5;
const int dirPinSweeper = 6;
const int enablePinSweeper = 7;

// maksimit venttiilille
const long valveMinPosition = 0; 
const long valveMaxPosition = 1000; 


// PID Setup
double Setpoint = 2.0; // default arvo pid:lle
double Input, Output;
double Kp=2.0, Ki=5.0, Kd=1.0; // PID parametrit
PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

AccelStepper stepperValve(AccelStepper::DRIVER, stepPinValve, dirPinValve);
AccelStepper stepperSweeper(AccelStepper::DRIVER, stepPinSweeper, dirPinSweeper);

String inputString = "";         
bool stringComplete = false;     

unsigned long lastSweepTime = 0; 
const long sweepInterval = 300000; // intervalli millisekunteina millon pyyhitään (5m= 300000)
bool sweeperDirection = true;    // sweeppering tän hetkinen suunta



void setup() {
  Serial.begin(9600);
  inputString.reserve(200);

  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(-50, 50); // pid:n  ulostusrajat

  // initiliaze stepper oliot
  stepperValve.setMaxSpeed(20);
  stepperValve.setAcceleration(10);
  stepperValve.setEnablePin(enablePinValve);
  stepperValve.setCurrentPosition(0); // Assume valve is fully closed at startup

  
  stepperSweeper.setMaxSpeed(200); 
  stepperSweeper.setAcceleration(50);
  stepperSweeper.setEnablePin(enablePinSweeper);
  


  // pistetään luukut poies
  stepperValve.disableOutputs();
  stepperSweeper.disableOutputs();
}

void loop() {
  if (stringComplete) {
    parseCommand(inputString);
    inputString = "";
    stringComplete = false;
  }

  if (myPID.Compute()) {
    long newPosition = stepperValve.currentPosition() + Output;
    newPosition = constrain(newPosition, valveMinPosition, valveMaxPosition);
    
    if (newPosition != stepperValve.currentPosition()) {
      stepperValve.enableOutputs();
      stepperValve.moveTo(newPosition); 
	  Serial.print("Valve Position: ");
	  Serial.println(stepperValve.currentPosition());

    }
  }

    // Sweeper logiikka
  // liikkuu x suuntaa per millon on aika
	if (millis() - lastSweepTime > sweepInterval) {
		moveSweeper();
  }

  // checkkaa nopee jos mitää ei tapahdu = virrat poies
  if (!stepperValve.isRunning()) {
    stepperValve.disableOutputs();
  }
  
  if (!stepperSweeper.isRunning()) {
  stepperSweeper.disableOutputs(); 
  }

  stepperValve.run();
  stepperSweeper.run();
}
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}

void moveSweeper() {
  stepperSweeper.enableOutputs(); 
  if (sweeperDirection) {
    stepperSweeper.move(1000); // liikutaan oikealla
  } else {
    stepperSweeper.move(-1000); // ja vasemmalle
  }
  sweeperDirection = !sweeperDirection; // vaihta suuntaa
  lastSweepTime = millis(); 
}



void parseCommand(String command) {
  if (command.startsWith("Sensor_Reading_DO")) {
    String valueStr = command.substring(command.indexOf(' ') + 1);
    Input = valueStr.toDouble();
  } else if (command.startsWith("Target_DO")) {
    String valueStr = command.substring(command.indexOf(' ') + 1);
    Setpoint = valueStr.toDouble();
  } else if (command.startsWith("Force_Sweep")) {
    moveSweeper();
  }
  // lisää tähän muut komennot
}

