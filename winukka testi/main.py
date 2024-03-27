import sys
from PySide2.QtWidgets import QApplication, QWidget, QGridLayout, QVBoxLayout, QPushButton, QInputDialog, QMessageBox, QLabel, QTextEdit, QLineEdit
from PySide2.QtCore import QTimer, QThread, QObject, Signal, Qt
from PySide2.QtGui import QPixmap
import serial
from serial.tools import list_ports
import fetch_csv
import csv
from datetime import datetime
import os


# tenperatre , ph
SENSOR_URLS = ["http://192.168.1.212/userfiles/Data0_logbook.csv", "http://192.168.1.212/userfiles/Data1_logbook.csv" ]

class FetchSensorDataWorker(QObject):
    finished = Signal()
    error = Signal(str)
    update = Signal(dict)

    def __init__(self, url, ser):
        super().__init__()
        self.url = SENSOR_URLS[0]
        self.ser = ser

    def fetch_data(self):
        try:
            result = fetch_csv.fetch_sensor_data("http://192.168.1.212/userfiles/Data0_logbook.csv")  # Use the mock function
            if result:
                # Directly access the values from the dictionary
                sensor_type = result['sensor_type']
                value = result['value']
                unit = result['unit']
                
                # Format the update to be emitted. Adjust according to your needs.
                self.update.emit({"sensor_type": sensor_type, "value": value, "unit": unit})
                
                # Prepare and send the command via serial
                command = f"Sensor_Reading_DO {value/10}"
                self.send_via_serial(command)
            else:
                self.error.emit("Failed to fetch data")
        except Exception as e:
            self.error.emit(str(e))
            

    def send_via_serial(self, command):
        try:
            self.ser.write(f"{command}\n".encode())
            print(f"Sent: {command}")
        except serial.SerialException as e:
            self.error.emit(f"Error sending command via serial: {e}")

    def run(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_data)
        self.timer.start(6000)  # 60 seconds interval
        self.fetch_data()



class SerialReadWorker(QObject):
    finished = Signal()
    error = Signal(str)
    update = Signal(str)

    def __init__(self, ser):
        super().__init__()
        self.ser = ser

    def read_serial(self):
        try:
            line = self.ser.readline().decode().strip()
            if line:
                self.update.emit(line)
        except serial.SerialException as e:
            self.error.emit(f"Error reading from serial: {e}")

    
    def run(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial)
        self.timer.start(100)  # 1 second interval
        self.read_serial()
        
        
class LogSensorDataWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, urls):
        super().__init__()
        self.urls = SENSOR_URLS
        self.timer = QTimer()
        self.timer.timeout.connect(self.log_data)
        self.timer.start(30000)  # 30 seconds interval
        
    def log_data(self):
        for url in self.urls:
            try:
                result = fetch_csv.fetch_sensor_data(url)
                if result:
                    sensor_type = result.get("sensor_type", "Unknown")
                    value = result.get("value", 0)
                    unit = result.get("unit", "Unknown")
                    print(f"fetched Logging data: {sensor_type}, {value}, {unit}")
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    filename = f"{sensor_type}.csv"
                    file_exists = os.path.isfile(filename)
                    with open(filename, 'a', newline='') as file:
                        writer = csv.writer(file)
                        if not file_exists:
                            writer.writerow(["timestamp", "value", "unit"])
                        writer.writerow([timestamp, value, unit])
                else:
                    self.error.emit(f"Failed to fetch data from {url}")
            except Exception as e:
                self.error.emit(str(e))

    def run(self):
        print("Running the background task")


class SerialCommandsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Available Serial Commands")
        self.setGeometry(100, 100, 400, 300)  # Adjust size as needed
        layout = QVBoxLayout()

        # Define your commands and descriptions
        commands = [
            "Sensor_Reading_DO <value>: Send sensor reading with value.",
            "Target_DO <value>: Set target dissolved oxygen to <value>.",
            "Force_Sweep: Initiate a sweep action.",
            "Move_Valve <steps>: Move the valve a certain number of steps.",
            "Set_Valve_Min_Position <position>: Set the minimum position for the valve."
        ]

        # Create and add labels for each command
        for command in commands:
            layout.addWidget(QLabel(command))

        self.setLayout(layout)


class StepperMotorControllerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.sensorData = {}  # Dictionary joka säilyttää datan
        self.initUI()
        self.get_com_port()
        self.open_serial_connection()
        self.start_serial_read_worker()  # Start the SerialReadWorker
        self.thread = None
        self.log_data_thread = None  # Initialize log_data_thread

    def initUI(self):
        self.setWindowTitle('AS')
        self.setGeometry(300, 300, 600, 400)  # Adjust size for better layout

        # Use a grid layout for flexible positioning
        layout = QGridLayout(self)

        # Stylesheet to enhance UI appearance
        stylesheet = """
            QWidget {
                font-size: 16px; /* Slightly larger to avoid pixelation */
                font-family: Arial, sans-serif; /* Arial is widely available and renders smoothly on most systems */
            }
            QLabel {
                font-weight: bold;
                padding: 4px;
                color: #333; /* Ensuring good contrast */
            }
            QPushButton {
                background-color: #FFA500;
                color: #05386B;
                border: none;
                padding: 10px 15px;
                margin: 5px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF4500;
            }
            QTextEdit, QLineEdit {
                padding: 5px;
                border: 1px solid #edf5e1;
                margin: 5px;
                border-radius: 5px;
            }
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """
        
        self.setStyleSheet(stylesheet)

        self.sensor_value_label = QLabel('Sensor Value: N/A')
        layout.addWidget(self.sensor_value_label, 0, 0, 1, 2)

        self.new_position_label = QLabel('Valve calc newPosition: N/A')
        layout.addWidget(self.new_position_label, 1, 0, 1, 2)

        self.position_label = QLabel('Valve Position: N/A')
        layout.addWidget(self.position_label, 2, 0, 1, 2)

        # Add a label for the serial output text box
        serial_output_label = QLabel('Incoming Serial:')
        layout.addWidget(serial_output_label, 3, 0, 1, 2)
        self.serial_output = QTextEdit()
        self.serial_output.setReadOnly(True)
        layout.addWidget(self.serial_output, 4, 0, 1, 2)
         # Add a label for the command input text box
        command_input_label = QLabel('Command Output:')
        layout.addWidget(command_input_label, 5, 0, 1, 2)

        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.send_command)
        layout.addWidget(self.command_input, 6, 0, 1, 2)
        
        self.start_button = QPushButton('Start Fetching Sensor Data')
        self.start_button.clicked.connect(self.start_sensor_data_worker)
        layout.addWidget(self.start_button, 7, 0)
        
        self.force_sweep_button = QPushButton('Force Sweep')
        self.force_sweep_button.clicked.connect(lambda: self.send_via_serial("Force_Sweep"))
        layout.addWidget(self.force_sweep_button, 7, 1)
        
        self.log_data_button = QPushButton('Start Logging Sensor Data')
        self.log_data_button.clicked.connect(self.toggle_log_data_worker)
        layout.addWidget(self.log_data_button, 8, 0)
    
        
        self.show_serial_commands_button = QPushButton('Show Serial Commands')
        self.show_serial_commands_button.clicked.connect(self.show_serial_commands_window)
        layout.addWidget(self.show_serial_commands_button, 8, 1)
        

        # Load and display the company logo
        image_path = "./endress-hauser-logo.png"
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():  # Check if the pixmap was loaded successfully
            image_label = QLabel()
            image_label.setPixmap(pixmap.scaled(400, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            # Create a QLabel for the sponsor text
            sponsor_label = QLabel("Sponsor")
            sponsor_label.setAlignment(Qt.AlignCenter)

            # Create a QVBoxLayout to stack the sponsor label and the image
            sponsor_layout = QVBoxLayout()
            sponsor_layout.addWidget(sponsor_label)
            sponsor_layout.addWidget(image_label)

            # Create a QWidget to hold the layout and add it to the main layout
            sponsor_widget = QWidget()
            sponsor_widget.setLayout(sponsor_layout)
            layout.addWidget(sponsor_widget, 9, 0, 1, 2, Qt.AlignCenter)

        else:
            print("Error: Image not loaded correctly. Please check the file path.")
     # Set the layout to the QWidget
        self.setLayout(layout)
        
    def show_serial_commands_window(self):
        self.commands_window = SerialCommandsWindow()
        self.commands_window.show()
        
    def open_serial_connection(self):
        try:
            self.ser = serial.Serial(self.com_port, 9600, timeout=1)
        except serial.SerialException as e:
            QMessageBox.critical(self, "Serial Error", f"Error opening serial connection: {e}")
            sys.exit()
            
    def handle_serial_data_update(self, data):
        # Check if 'data' is a dictionary, meaning it's from FetchSensorDataWorker
        if isinstance(data, dict):
            sensor_type = data.get("sensor_type", "N/A")
            value = data.get("value", "N/A")
            unit = data.get("unit", "N/A")
            # Update the UI elements accordingly
            # For example, if you want to display the sensor value:
            self.sensor_value_label.setText(f"{sensor_type} Value: {value} {unit}")
        elif isinstance(data, str):
            # Original string handling logic
            if data.startswith('Valve calc newPosition:'):
                self.new_position_label.setText(data)
            elif data.startswith('Valve Position:'):
                self.position_label.setText(data)
            else:
                self.serial_output.append(data)
    def send_command(self):
        command = self.command_input.text()
        self.send_via_serial(command)
        self.command_input.clear()
        
                   
    def start_serial_read_worker(self):
        self.serial_read_thread = QThread()
        self.serial_read_worker = SerialReadWorker(self.ser)
        self.serial_read_worker.moveToThread(self.serial_read_thread)
        self.serial_read_worker.finished.connect(self.serial_read_thread.quit)
        self.serial_read_worker.update.connect(self.handle_serial_data_update)
        self.serial_read_worker.error.connect(self.handle_error)
        self.serial_read_thread.started.connect(self.serial_read_worker.run)
        self.serial_read_thread.finished.connect(self.serial_read_thread.deleteLater)
        self.serial_read_thread.start()
            
            
        
            
            
    def toggle_log_data_worker(self):
        if self.log_data_thread is None:
            # Start the worker
            self.log_data_thread = QThread()
            self.log_data_worker = LogSensorDataWorker(SENSOR_URLS)
            self.log_data_worker.moveToThread(self.log_data_thread)
            self.log_data_worker.finished.connect(self.log_data_thread.quit)
            self.log_data_worker.error.connect(self.handle_error)
            self.log_data_thread.started.connect(self.log_data_worker.run)
            self.log_data_thread.finished.connect(self.log_data_thread.deleteLater)
            self.log_data_thread.start()

            self.log_data_button.setText('Stop Logging Sensor Data')
        else:
        # Stop the worker
             self.log_data_worker.timer.stop()
             self.log_data_thread.quit()
             self.log_data_thread.wait()
             self.log_data_thread = None
             self.log_data_worker = None

             self.log_data_button.setText('Start Logging Sensor Data')


    def start_sensor_data_worker(self):
        if self.thread is None:
            self.thread = QThread()
            self.worker = FetchSensorDataWorker('http://192.168.1.212/userfiles/Data0_logbook.csv', self.ser)
            self.worker.moveToThread(self.thread)
            self.worker.finished.connect(self.thread.quit)
            self.worker.update.connect(self.handle_serial_data_update)
            self.worker.error.connect(self.handle_error)
            self.thread.started.connect(self.worker.run)
            self.thread.finished.connect(self.thread.deleteLater)  # Ensure the thread is deleted after it finishes
            self.thread.start()


    def handle_error(self, error_message):
        QMessageBox.warning(self, "Error", error_message)

    def send_via_serial(self, command):
        try:
            self.ser.write(f"{command}\n".encode())
            print(f"Sent: {command}")
        except serial.SerialException as e:
            QMessageBox.critical(self, "Serial Error", f"Error sending command via serial: {e}")

    def get_com_port(self):
        available_ports = list(serial.tools.list_ports.comports())
        if available_ports:
            port_names = [port.device for port in available_ports]
            com_port, ok = QInputDialog.getItem(self, 'COM Port Selection', 'Select the COM port:', port_names, 0, False)
            if ok:
                self.com_port = com_port
        else:
            QMessageBox.critical(self, "No COM Ports Found", "No COM ports found. Please connect your device and try again.")
            sys.exit()    
            
    def closeEvent(self, event):
        if self.ser and self.ser.is_open:
            self.ser.close()

        #sammuttaa serial read thread
        if self.serial_read_thread is not None:
            self.serial_read_worker.timer.stop()
            self.serial_read_thread.quit()
            self.serial_read_thread.wait()

        # sammuttaa log_data_thread
        if self.log_data_thread is not None:
            self.log_data_worker.timer.stop()
            self.log_data_thread.quit()
            self.log_data_thread.wait()

        # sammuttaa  the main thread
        if self.thread is not None:
            self.worker.timer.stop()
            self.thread.quit()
            self.thread.wait()

        event.accept()

def main():
    app = QApplication(sys.argv)
    ex = StepperMotorControllerApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
