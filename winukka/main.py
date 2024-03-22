import sys
from PySide2.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QInputDialog, QMessageBox, QLabel, QTextEdit, QLineEdit
from PySide2.QtCore import QTimer, QThread, QObject, Signal
from PySide2.QtGui import QPixmap
import serial
from serial.tools import list_ports
import fetch_csv
import csv
from datetime import datetime
import os



# tenperatre , 
SENSOR_URLS = ["http://192.168.1.212/userfiles/Data0_logbook.csv", "http://192.168.1.212/userfiles/Data2_logbook.csv" ]

class FetchSensorDataWorker(QObject):
    finished = Signal()
    error = Signal(str)
    update = Signal(dict)

    def __init__(self, url, ser):
        super().__init__()
        self.url = url
        self.ser = ser

    def fetch_data(self):
        try:
            result = fetch_csv.fetch_sensor_data(self.url)
            if result:
                sensor_type, value, unit = result
                self.update.emit({"sensor_type": sensor_type, "value": value, "unit": unit})
                command = f"Sensor_Reading_DO {value}"
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
        self.timer.start(60000)  # 60 seconds interval
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
        self.urls = urls
        self.timer = QTimer()
        self.timer.timeout.connect(self.log_data)
        self.timer.start(600000)  # 10 minutes interval
        
    def log_data(self):
        for url in self.urls:
            try:
                result = fetch_csv.fetch_sensor_data(url)
                if result:
                    sensor_type, value, unit = result
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
        self.setWindowTitle('Sensor Data and Commands')
        self.setGeometry(300, 300, 400, 300)

        layout = QVBoxLayout()

        self.sensor_value_label = QLabel('Sensor Value: N/A')
        layout.addWidget(self.sensor_value_label)
        
        self.new_position_label = QLabel('Valve calc newPosition: N/A')
        layout.addWidget(self.new_position_label)

        self.position_label = QLabel('Valve Position: N/A')
        layout.addWidget(self.position_label)
        
        
        self.serial_output = QTextEdit()
        self.serial_output.setReadOnly(True)
        layout.addWidget(self.serial_output)
        
        
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.send_command)
        layout.addWidget(self.command_input)
        
        self.start_button = QPushButton('Start Fetching Sensor Data')
        self.start_button.clicked.connect(self.start_sensor_data_worker)
        layout.addWidget(self.start_button)

        self.force_sweep_button = QPushButton('Force Sweep')
        self.force_sweep_button.clicked.connect(lambda: self.send_via_serial("Force_Sweep"))
        layout.addWidget(self.force_sweep_button)
        
        
        self.log_data_button = QPushButton('Start Logging Sensor Data')
        self.log_data_button.clicked.connect(self.toggle_log_data_worker)
        layout.addWidget(self.log_data_button)
        
        pixmap = QPixmap("./endress-hauser-logo.png")

        # Create a QLabel object and set the QPixmap object as its pixmap
        image_label = QLabel()
        image_label.setPixmap(pixmap)

        # Add the QLabel object to the layout
        layout.addWidget(image_label)


        


        self.setLayout(layout)
        
    def open_serial_connection(self):
        try:
            self.ser = serial.Serial(self.com_port, 9600, timeout=1)
        except serial.SerialException as e:
            QMessageBox.critical(self, "Serial Error", f"Error opening serial connection: {e}")
            sys.exit()
            
    def handle_serial_data_update(self, line):
        if line.startswith('Valve calc newPosition:'):
            self.new_position_label.setText(line)
        elif line.startswith('Valve Position:'):
            self.position_label.setText(line)
        else:
            self.serial_output.append(line)
    
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
            self.worker.update.connect(self.handle_sensor_data_update)
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
        event.accept()

def main():
    app = QApplication(sys.argv)
    ex = StepperMotorControllerApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
