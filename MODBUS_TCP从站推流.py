import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QTextEdit, QMessageBox
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QIcon, QTextCursor
from pymodbus.client.sync import ModbusTcpClient
import requests
import json

class ModbusClientGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Modbus TCP 客户端 数据推流')
        self.setWindowIcon(QIcon('icon.png'))  # 设置窗口图标
        self.setGeometry(100, 100, 600, 500)
        self.client_ip_label = QLabel('MODBUSTCP-客户端-IP:', self)
        self.client_ip_input = QLineEdit(self)
        self.client_ip_input.setText("192.168.0.88")
        self.client_port_label = QLabel('端口:', self)
        self.client_port_input = QLineEdit(self)
        self.client_port_input.setText("502")

        self.webhook_url_label = QLabel('推流地址:', self)
        self.webhook_url_input = QLineEdit(self)

        self.register_address_labels = []
        self.register_address_inputs = []
        for i in range(1, 5):
            label = QLabel(f'寄存器地址 {i}:', self)
            input_box = QLineEdit(self)
            self.register_address_labels.append(label)
            self.register_address_inputs.append(input_box)
        self.connect_button = QPushButton('连接', self)
        self.connect_button.clicked.connect(self.toggle_connection)
        self.connected = False

        self.log_output = QTextEdit(self)
        self.log_output.append(f'本软件理论上支持所有的MODBUS—TCP从站数据读取,但是目前只支持读取保持寄存器!')

        self.author_label = QLabel('<a href="https://github.com/Liuxiaobai18/MODBUS-TCP-wechat">作者：刘小白</a>', self)
        self.author_label.setOpenExternalLinks(True)

        layout = QVBoxLayout()
        layout.addWidget(self.client_ip_label)
        layout.addWidget(self.client_ip_input)
        layout.addWidget(self.client_port_label)
        layout.addWidget(self.client_port_input)
        layout.addWidget(self.webhook_url_label)
        layout.addWidget(self.webhook_url_input)
        for label, input_box in zip(self.register_address_labels, self.register_address_inputs):
            layout.addWidget(label)
            layout.addWidget(input_box)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.log_output)
        layout.addWidget(self.author_label)

        self.setLayout(layout)
        self.client = None
        self.previous_register_values = {}
        self.webhook_url = None
        self.data_push_enabled = False


    def toggle_connection(self):
        if not self.connected:
            self.webhook_url = self.webhook_url_input.text().strip()
            if not self.webhook_url:
                QMessageBox.warning(self, '警告', '请填写推流地址')
                return
            if not self.validate_inputs():
                return
            self.connect_to_modbus()
        else:
            self.disconnect_from_modbus()
    def validate_inputs(self):
        if not self.client_ip_input.text():
            QMessageBox.warning(self, '警告', '请填写 Modbus 客户端 IP')
            return False
        if not self.client_port_input.text():
            QMessageBox.warning(self, '警告', '请填写端口号')
            return False
        return True

    def connect_to_modbus(self):
        client_ip = self.client_ip_input.text()
        client_port = int(self.client_port_input.text())
        unit_id = 1

        register_addresses = []
        for input_box in self.register_address_inputs:
            address = input_box.text().strip()
            if address:
                register_addresses.append(int(address))

        if not register_addresses:
            QMessageBox.warning(self, '警告', '请输入至少一个寄存器地址')
            return
        try:
            self.client = ModbusTcpClient(client_ip, port=client_port)
            self.client.connect()
            self.connected = True
            self.connect_button.setText('关闭')
            self.data_push_enabled = False
            for register_address in register_addresses:
                result = self.client.read_input_registers(register_address, count=1, unit=unit_id)
                if not result.isError():
                    self.log_output.append(f'成功读取寄存器 {register_address} 的值: {result.registers[0]}')
                    self.previous_register_values[register_address] = result.registers[0]
                else:
                    self.log_output.append(f'读取寄存器 {register_address} 时出错: {result}')
            self.send_message('数据推流已启用！')  # 发送一次数据推流已启用消息
        except Exception as e:
            self.log_output.append(f'连接出错: {str(e)}')

    def disconnect_from_modbus(self):
        if self.client:
            self.client.close()
        self.connected = False
        self.connect_button.setText('连接')

    def send_message(self, message):
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        try:
            response = requests.post(self.webhook_url, json=data, headers=headers)
            response.raise_for_status()
        except Exception as e:
            self.log_output.append(f'发送消息时出错: {str(e)}')
        else:
            self.log_output.append('消息已成功发送')

    def check_register_values(self):
        if self.connected:
            for register_address in self.previous_register_values.keys():
                result = self.client.read_holding_registers(register_address, count=1,  unit=int(self.unit_id_input.text()))
                if not result.isError():
                    current_value = result.registers[0]
                    previous_value = self.previous_register_values[register_address]
                        if current_value != 0:
                            self.data_push_enabled =True
                            self.send_message(f'寄存器{register_address} 的值发生变化: {current_value}')
                           else:
                            continue
                    if current_value != previous_value:
                        self.log_output.append(f'寄存器 {register_address} 的值发生变化: {current_value}')
                        self.send_message(f'寄存器 {register_address} 的值发生变化: {current_value}')
                        self.previous_register_values[register_address] = current_value

              
    def closeEvent(self, event):
        self.disconnect_from_modbus()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    modbus_client_gui = ModbusClientGUI()
    modbus_client_gui.show()

    timer = QTimer()
    timer.timeout.connect(modbus_client_gui.check_register_values)
    timer.start(1000)  # 每秒检查一次寄存器值

    sys.exit(app.exec_())








