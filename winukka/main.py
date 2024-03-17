import sys
from PySide2.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QInputDialog, QMessageBox, QLabel, )
from PySide2.QtCore import  QThread, QObject, Signal
import serial
from serial.tools import list_ports
import fetch_csv

class FetchSensorDataWorker(QObject):
    finished = Signal()
    error = Signal(str)
    update = Signal(dict)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        result = fetch_csv.fetch_sensor_data(self.url)
        if result:
            sensor_type, value, unit = result
            self.update.emit({"sensor_type": sensor_type, "value": value, "unit": unit})
        else:
            self.error.emit("Failed to fetch data")
        self.finished.emit()

class StepperMotorControllerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.sensorData = {}  # Dictionary joka säilyttää datan
        self.initUI()
        self.get_com_port()

    def initUI(self):
        self.setWindowTitle('Sensor Data and Commands')
        self.setGeometry(300, 300, 400, 300)

        layout = QVBoxLayout()

        self.sensor_value_label = QLabel('Sensor Value: N/A')
        layout.addWidget(self.sensor_value_label)

        self.start_button = QPushButton('Start Fetching Sensor Data')
        self.start_button.clicked.connect(self.start_sensor_data_worker)
        layout.addWidget(self.start_button)

        self.force_sweep_button = QPushButton('Force Sweep')
        self.force_sweep_button.clicked.connect(lambda: self.send_via_serial("Force_Sweep"))
        layout.addWidget(self.force_sweep_button)

        self.setLayout(layout)

    def start_sensor_data_worker(self):
        self.thread = QThread()
        worker = FetchSensorDataWorker('http://192.168.1.212/userfiles/Data0_logbook.csv')
        worker.moveToThread(self.thread)
        worker.finished.connect(self.thread.quit)
        worker.update.connect(self.handle_sensor_data_update)
        worker.error.connect(self.handle_error)
        self.thread.started.connect(worker.run)
        self.thread.start()

    def handle_sensor_data_update(self, sensor_data):
        sensor_type = sensor_data["sensor_type"]
        value = sensor_data["value"]
        unit = sensor_data["unit"]
        self.sensorData[sensor_type] = {"value": value, "unit": unit}
        display_text = ", ".join([f"{k}: {v['value']:.2f} {v['unit']}" for k, v in self.sensorData.items()])
        self.sensor_value_label.setText(display_text)

    def handle_error(self, error_message):
        QMessageBox.warning(self, "Error", error_message)

    def send_via_serial(self, command):
        try:
            with serial.Serial(self.com_port, 9600, timeout=1) as ser:
                ser.write(f"{command}\n".encode())
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

def main():
    app = QApplication(sys.argv)
    ex = StepperMotorControllerApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
