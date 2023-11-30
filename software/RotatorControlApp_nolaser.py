# -*- coding: utf-8 -*-
"""
GUI app to control the motorized polarizer and read power meter sensor from NeaSNOM microscope
Standalone app
@author: Gergely Németh
"""

#For the GUI
import sys
from PySide6 import QtWidgets
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox
import pyqtgraph as pg
import serial.tools.list_ports
import numpy as np
import elliptec
from time import sleep
import asyncio
import os

# import neaSDK
try:
    import nea_tools
except:
    print("nea_tools module not found, working in offline mode")
    offline_mode = True

# UI import
ui_file_name = 'RotatorApp_nolaser.ui'
current_folder = os.getcwd()
ui_file_path = os.path.join(current_folder,ui_file_name)

uiclass, baseclass = pg.Qt.loadUiType(ui_file_path)

class RotatorApp(uiclass, baseclass):
    def __init__(self):
        super().__init__()

        # Initialize the user interface from the generated module
        self.setupUi(self)

        self.connected = False

        self.SearchCOMports()

        self.sensor_value = 0
        self.setpoint_error = 0
        self.dt_sensor = 1000

        #set and start a timer for sensor reading
        self.timer=QTimer(self)
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.readSensor)
        self.timer.start(self.dt_sensor)

        # timer for P control
        self.timerPstep=QTimer(self)
        self.timerPstep.setTimerType(QtCore.Qt.PreciseTimer)
        self.timerPstep.setSingleShot(True)
        self.timerPstep.setInterval(1000)
        self.timerPstep.timeout.connect(self.proceedOrNot)

        # button signals
        self.JogFWPushButton.clicked.connect(lambda: self.jogging("forward",1))
        self.JogFFWPushButton.clicked.connect(lambda: self.jogging("forward",3))
        self.JogBWPushButton.clicked.connect(lambda: self.jogging("backward",1))
        self.JogFBWPushButton.clicked.connect(lambda: self.jogging("backward",3))
        self.GoHomePushButton.clicked.connect(lambda: self.ro.home())
        self.JumpPushButton.clicked.connect(self.jumptoangle)
        self.SetHomeOffsetPushButton.clicked.connect(self.setCurrentAsHome)
        self.AutoFindPushButton.clicked.connect(self.find_power_minimum)
        self.SetPowerPushButton.clicked.connect(self.findSetPointPower)
        self.connectSNOM.clicked.connect(self.connect_to_neasnom)
        if offline_mode:
            self.connectSNOM.setEnabled(False)
            self.statusbar.showMessage(u"\u26A0 nea_tools module not found, you can only use the rotator.")

        # Timer for everything
        self.timer=QTimer(self)
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.readSensor)
        self.timer.start(1000)

        #Update initial angle
        self.lcdNumber_2.display(self.ro.get_angle())
        # self.show()

    def SearchCOMports(self):
            comports = serial.tools.list_ports.comports()
            p = [x for x in comports if 'USB VID:PID=0403:6015 SER=DK0BIUIAA' in x.hwid]
            try:
                self.deviceport = p[0].name
                print(f"Device found on {self.deviceport}")
                self.controller = elliptec.Controller(self.deviceport, debug=False)
                self.ro = elliptec.Rotator(self.controller)
            except:
                print("No device was found")
                msg = QMessageBox(self)
                msg.setWindowTitle("No USB connection!")
                msg.setText("No USB connection found!")
                msg.setIcon(QMessageBox.Critical)
                msg.setStandardButtons(QMessageBox.Ok|QMessageBox.Cancel)
                msg.setInformativeText("Connect the device to the PC!")
                button = msg.exec()

                if button == QMessageBox.Ok:
                    self.SearchCOMports()
                elif button == QMessageBox.Cancel:
                    self.close()

    def connect_to_neasnom(self):
        path_to_dll = r"\\nea-server\updates\Application Files\neaSCAN_2_1_10694_0"
        fingerprint = 'af3b0d0f-cdbb-4555-9bdb-6fe200b64b51'
        host = 'nea-server'
        if self.connected:
            print('\nDisconnecting from neaServer!')
            nea_tools.disconnect()
            self.SetPowerPushButton.setEnabled(False)
            self.SetPointSpinBox.setEnabled(False)
            self.AutoFindPushButton.setEnabled(False)
            self.lcdNumber.setEnabled(False)
            self.checkBoxSNOM.setChecked(False)
            self.connected = False
            self.statusbar.showMessage("Disconnected from SNOM")
        else:
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(nea_tools.connect(host, fingerprint, path_to_dll))
            except ConnectionError:
                print("Disable the WiFi connection!")

            try:
                from neaspec import context
                import Nea.Client.SharedDefinitions as nea
            except ModuleNotFoundError:
                raise ConnectionError('Connection refused or timeout. Retry to connect again.')
            else:
                self.connected = True
                self.SetPowerPushButton.setEnabled(True)
                self.SetPointSpinBox.setEnabled(True)
                self.AutoFindPushButton.setEnabled(True)
                self.lcdNumber.setEnabled(True)
                self.checkBoxSNOM.setChecked(True)
                print('\nConnected.')
                self.statusbar.showMessage("Connected to SNOM")

            self.context = context
            self.nea = nea

            return context, nea

    def getTemperature(self):
        self.LaserTemp = self.m.Temperature

    def readSensor(self):
        if self.connected:
            self.sensor_value = self.context.Microscope.Py.EnergySensor
            self.setpoint_error = self.SetPointSpinBox.value() - self.sensor_value
            self.lcdNumber.display(self.sensor_value)

    def jogging(self,direction,speed):
        stepsize = speed*self.JogSizeSpinBox.value()
        self.ro.set_jog_step(stepsize)
        self.ro.jog(direction)
        self.lcdNumber_2.display(self.ro.get_angle())

    def jumptoangle(self):
        alpha = self.GoToAngleSpinBox.value()
        self.ro.set_angle(alpha)
        self.statusbar.showMessage(f"Moved to: {self.ro.get_angle()}")
        self.lcdNumber_2.display(self.ro.get_angle())

    def setCurrentAsHome(self):
        angle_shift = self.ro.get_angle()
        old_home = self.ro.get_home_offset()
        self.ro.set_home_offset(old_home + angle_shift)
        self.lcdNumber_2.display(self.ro.get_angle())
        self.statusbar.showMessage(f"New home is set to: {old_home + angle_shift}")

    def find_power_minimum(self):
        self.ro.set_home_offset(0)
        self.ro.home()
        sleep(3)
        angles = np.arange(0, 180, 2)
        real_angles = []
        sensor_data = []
        for alpha in angles:
            real_angles.append(self.ro.set_angle(alpha))
            sleep(1)
            temp = self.context.Microscope.Py.EnergySensor
            sensor_data.append(temp)
            print("Angle:", alpha, "Energy Sensor:", temp)
        
        home_shift = real_angles[np.argmin(sensor_data)]
        angle_offset = self.ro.get_home_offset() + home_shift

        print(f'Minimum is at {angle_offset}')
        print(f'Before homing we are at: {self.ro.get_angle()}, Energy Sensor: {self.context.Microscope.Py.EnergySensor}')

        self.ro.set_home_offset(angle_offset)
        self.ro.home()
        sleep(3)
        print(f'After homing we are at: {self.ro.get_angle()}, Energy Sensor: {self.context.Microscope.Py.EnergySensor}')
        self.statusbar.showMessage(f"New home offset: {self.ro.get_home_offset()}")
        self.lcdNumber_2.display(self.ro.get_angle())

    def findSetPointPower(self):
        self.timer.stop()
        self.timer.timeout.disconnect(self.readSensor)
        self.timer.timeout.connect(self.proportionalStep)
        self.timer.start(2000)

    def proportionalStep(self):
        P = 10
        angle_step = self.setpoint_error*P
        if angle_step > 20:
            angle_step = 20
        self.ro.shift_angle(angle_step)
        self.timerPstep.start()

    def proceedOrNot(self):
        self.readSensor()
        self.lcdNumber_2.display(self.ro.get_angle())
        if abs(self.setpoint_error) < 0.05:
            self.timer.stop()
            self.timer.timeout.disconnect(self.proportionalStep)
            self.timer.timeout.connect(self.readSensor)
            self.timer.start(self.dt_sensor)
            print("Setpoint reached")
            self.statusbar.showMessage(f"Setpoint reached! P={self.sensor_value}")

    def closeEvent(self, event):
        quit_msg = "Are you sure you want to exit the program?"
        print(quit_msg)
        reply = QtWidgets.QMessageBox.question(self, 'Message', quit_msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
            try:
                self.ro.close()
                print(f'{self.deviceport} port closed')
            except:
                pass
            if self.connected:
                print('\nDisconnecting from neaServer!')
                nea_tools.disconnect()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = RotatorApp()
    ex.show()
    sys.exit(app.exec())