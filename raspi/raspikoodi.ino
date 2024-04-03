#include <Arduino.h>
#include <AccelStepper.h>
#include <PID_v1.h>

// Stepper pinnit venttiilille
const int enablePinValve = 2;
const int stepPinValve = 3;
const int dirPinValve = 4;

// sama sweepperille
const int enablePinSweeper =10;
const int stepPinSweeper = 11;
const int dirPinSweeper = 12;

// maksimit venttiilille
long valveMinPosition = -50; 
const long valveMaxPosition = 200; 


// PID Setup
double Setpoint = 0; // default arvo pid:lle
double Input, Output;
double Kp=30, Ki=0, Kd=10; // PID parametrit

unsigned long lastPIDUpdateTime = 0; 
const long pidUpdateInterval = 1000; 

// POwer managementtia
bool valveMovementFinished = false;
bool sweeperMovementFinished = false;
unsigned long valvePowerOffTime = 0;
unsigned long sweeperPowerOffTime = 0;
const unsigned long powerOffDelay = 1000; // 1 s



PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

AccelStepper stepperValve(AccelStepper::DRIVER, stepPinValve, dirPinValve);
AccelStepper stepperSweeper(AccelStepper::DRIVER, stepPinSweeper, dirPinSweeper);

String inputString = "";         
bool stringComplete = true;     

unsigned long lastSweepTime = 0; 
const long sweepInterval = 300000; // intervalli millisekunteina millon pyyhitään (5m= 300000)
bool sweeperDirection = true;    // sweeppering tän hetkinen suunta


void setup() {
  Serial.begin(9600);
  inputString.reserve(200);

  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(-5, 5); // pid:n  ulostusrajat

  // initiliaze stepper oliot
  stepperValve.setMaxSpeed(20);
  stepperValve.setAcceleration(5);
  stepperValve.setEnablePin(enablePinValve);
  stepperValve.setCurrentPosition(0); // oletetaan et rotari on täysin kiinni käynnistettäessä/ tätä alemmaks ei mennä
  
  stepperSweeper.setMaxSpeed(100); 
  stepperSweeper.setAcceleration(20);
  stepperSweeper.setEnablePin(enablePinSweeper);


  stepperValve.setPinsInverted(false, false, true);
  stepperSweeper.setPinsInverted(false, false, true);

  stepperValve.setMinPulseWidth(200);
  stepperSweeper.setMinPulseWidth(50);

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

  unsigned long currentTime = millis();
  if (currentTime - lastPIDUpdateTime >= pidUpdateInterval) {
    lastPIDUpdateTime = currentTime;

    if (myPID.Compute()) {
      long newPosition = stepperValve.currentPosition() + Output;
      newPosition = constrain(newPosition, valveMinPosition, valveMaxPosition);

      Serial.print("Valve calc newPosition: ");
      Serial.println(newPosition);

      if (newPosition != stepperValve.currentPosition()) {
        stepperValve.enableOutputs();
        stepperValve.moveTo(newPosition); 
      }
      
      Serial.print("Valve Position: ");
      Serial.println(stepperValve.currentPosition());
    }
    
  }

    // Sweeper logiikka
  // liikkuu x suuntaa per millon on aika
	if (millis() - lastSweepTime > sweepInterval) {
		moveSweeper();
  }

  stepperValve.run();
  stepperSweeper.run();

  // Aikaisemmin skripti otti liian nopee virrat pois steppereiltä, tää sallii niiden olla 1 s pidempään päällä varuiks ilman delay:tä

  if (stepperValve.distanceToGo() == 0) { 
    if (!valveMovementFinished) { 
      valveMovementFinished = true;
      valvePowerOffTime = millis(); 
    } else if ((millis() - valvePowerOffTime >= powerOffDelay) && valveMovementFinished) {
      stepperValve.disableOutputs(); 
      valveMovementFinished = false;
    }
  } else {
    valveMovementFinished = false; /
  }

 
  if (stepperSweeper.distanceToGo() == 0) {
    if (!sweeperMovementFinished) {
      sweeperMovementFinished = true;
      sweeperPowerOffTime = millis();
    } 
	else if ((millis() - sweeperPowerOffTime >= powerOffDelay) && sweeperMovementFinished) {
      stepperSweeper.disableOutputs();
      sweeperMovementFinished = false;
    }
  } else {
    sweeperMovementFinished = false; 
  }
    
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
    stepperSweeper.move(3145); // liikutaan oikealla
  } else {
    stepperSweeper.move(-3145); // ja vasemmalle
  }
  sweeperDirection = !sweeperDirection; // vaihtaa suuntaa
  lastSweepTime = millis(); 
}


void parseCommand(String command) {

  Serial.println("Received command: " + command); //debug print
  
  if (command.startsWith("Sensor_Reading_DO")) {
    String valueStr = command.substring(command.indexOf(' ') + 1);
    Input = valueStr.toDouble();
    Serial.print("Received Sensor Reading: ");
    Serial.println(Input);

  } 
  else if (command.startsWith("Target_DO")) {
    String valueStr = command.substring(command.indexOf(' ') + 1);
    Setpoint = valueStr.toDouble();
    Serial.print("Received Target DO: ");
    Serial.println(Setpoint);

  } 
  else if (command.startsWith("Force_Sweep")) {
    Serial.println("Force Sweep Command Received");
    moveSweeper();
  }

  else if (command.startsWith("Move_Valve")) {
    String stepsStr = command.substring(command.indexOf(' ') + 1);
    long steps = stepsStr.toInt();
    long targetPosition = stepperValve.currentPosition() + steps;
    
    targetPosition = constrain(targetPosition, valveMinPosition, valveMaxPosition);
    
    stepperValve.enableOutputs();
    stepperValve.moveTo(targetPosition);
    Serial.print("Moving valve to position: ");
    Serial.println(targetPosition);
  }
  
  else if (command.startsWith("Set_Valve_Min_Position")) {
      String valueStr = command.substring(command.indexOf(' ') + 1);
      long newMinPosition = valueStr.toInt();
      valveMinPosition = newMinPosition;
      Serial.print("New valve minimum position set to: ");
      Serial.println(valveMinPosition);
  }
}
