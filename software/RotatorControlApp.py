# -*- coding: utf-8 -*-
"""
GUI app to control the motorized polarizer and read power meter sensor from NeaSNOM microscope
Standalone app
@author: Gergely Németh
"""

#For the GUI
import sys
import yaml
from PySide6 import QtWidgets
from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer, QObject, QThread, Signal, Slot
import pyqtgraph as pg
import serial.tools.list_ports
import numpy as np
import elliptec
from time import sleep
import asyncio
import os
from qt_material import apply_stylesheet

from datetime import datetime
from ctypes import cdll,c_long, c_ulong, c_uint32,byref,create_string_buffer,c_bool,c_char_p,c_int,c_int16,c_double, sizeof, c_voidp
from TLPMX import TLPMX
import time
from TLPMX import TLPM_DEFAULT_CHANNEL

# import neaSDK
try:
    import nea_tools
    offline_mode = False
except:
    print("nea_tools module not found, working in offline mode")
    offline_mode = True

# UI import
ui_file_name = 'RotatorControlApp.ui'
current_folder = os.getcwd()
ui_file_path = os.path.join(current_folder,ui_file_name)

uiclass, baseclass = pg.Qt.loadUiType(ui_file_path)

class BasePowerSensor():
    def connect_to_sensor(self):
        raise NotImplementedError()
    
    def get_power(self):
        raise NotImplementedError()


class ThorlabsPM102A(BasePowerSensor):
    def __init__(self):
        self.name = None
        self.sensor = self.connect_to_sensor(self.get_device_name())
        self.set_wavelength(10000)

    def get_device_name(self):
        tlPM = TLPMX()
        deviceCount = c_uint32()
        tlPM.findRsrc(byref(deviceCount))
        # print("Number of found devices: " + str(deviceCount.value))
        resourceName = create_string_buffer(1024)
        for i in range(0, deviceCount.value):
            tlPM.getRsrcName(c_int(i), resourceName)
            print("Thorlabs power meter", i, ":", c_char_p(resourceName.raw).value)
            print("")
        tlPM.close()
        self.name = c_char_p(resourceName.raw).value

        return resourceName
    
    def connect_to_sensor(self, resourceName):
        tlPM = TLPMX()
        tlPM.open(resourceName, c_bool(True), c_bool(True))

        message = create_string_buffer(1024)
        tlPM.getCalibrationMsg(message,TLPM_DEFAULT_CHANNEL)
        # Enable auto-range mode.
        # 0 -> auto-range disabled
        # 1 -> auto-range enabled
        tlPM.setPowerAutoRange(c_int16(1),TLPM_DEFAULT_CHANNEL)

        # Set power unit to Watt.
        tlPM.setPowerUnit(c_int16(0),TLPM_DEFAULT_CHANNEL)
 
        print("Connected to PM102A/#### Thorlabs power sensor")
        # print(f"Last calibration date: {c_char_p(message.raw).value}\n")

        return tlPM
    
    def set_wavelength(self,wavelength):
        wl = c_double(wavelength)
        self.sensor.setWavelength(wl, TLPM_DEFAULT_CHANNEL)
    
    def get_power(self):
        power =  c_double()
        self.sensor.measPower(byref(power),TLPM_DEFAULT_CHANNEL)
        return power.value*1000

class Worker(QObject):
    progress = Signal(str)
    send_zero_offset = Signal(float)

    def __init__(self,sensor,rotator):
        super().__init__()
        self.sensor = sensor
        self.rotator = rotator

    @Slot()
    def measure_zero_offset(self,averages,delay):
        power_measurements = []
        count = 0
        while count < averages:
            power = self.sensor.get_power()
            power_measurements.append(power)
            count+=1
            time.sleep(delay)
            self.progress.emit(f"Zero adjust step: {count}")
            print(f"Zero adjust step: {count}")
        
        self.progress.emit(f"Zero adjust done: {np.mean(power_measurements)} mW")
        self.send_zero_offset.emit(np.mean(power_measurements))

class RotatorApp(uiclass, baseclass):
    def __init__(self):
        super().__init__()

        # Initialize the user interface from the generated module
        self.setupUi(self)

        self.connected = False
        self.config = None

        self.FindRotator()
        self.powersensor = ThorlabsPM102A()
        # Create the worker thread
        self.worker = Worker(sensor=self.powersensor,rotator=self.ro)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.sensor_value = 0.0
        self.sensor_offset = 0.0
        self.setpoint_error = 0.0
        self.dt_sensor = 1000
        
        # setup stylesheet
        apply_stylesheet(app, theme='light_blue.xml', invert_secondary=True)

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
        self.GoHomePushButton.clicked.connect(self.JustGoHome)
        self.JumpPushButton.clicked.connect(self.jumptoangle)
        self.SetHomeOffsetPushButton.clicked.connect(self.setCurrentAsHome)
        self.AutoFindPushButton.clicked.connect(self.find_power_minimum)
        self.SetPowerPushButton.clicked.connect(self.findSetPointPower)
        self.connectSNOM.clicked.connect(self.connect_to_neasnom)

        if offline_mode:
            self.connectSNOM.setEnabled(False)
            self.statusbar.showMessage(u"\u26A0 nea_tools module not found, you can only use the rotator.")

        self.zero_adjust_button.clicked.connect(lambda: self.worker.measure_zero_offset(10,0.5))
        self.worker.progress.connect(self.status_bar_update)
        self.worker.send_zero_offset.connect(self.receive_offset)

        # Timer for everything
        self.timer=QTimer(self)
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.readSensor)
        self.timer.start(1000)

        #Update initial angle
        self.lcdNumber_2.display(self.ro.get_angle())
        # self.show()

    def FindRotator(self):
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
                    self.FindRotator()
                elif button == QMessageBox.Cancel:
                    self.close()

    def check_config_file(self):   # load config
        with open('config.yaml', 'r') as file:
            self.config = yaml.safe_load(file)
            if (self.config['fingerprint'] == 'CHANGEMEE') or (self.config['path_to_dll'] == r"CHANGEMEE"):
                msg = QMessageBox()
                msg.setWindowTitle("Configuration missing")
                msg.setText("You have to set up neaSNOM configuration before use")
                msg.setIcon(QMessageBox.Critical)
                msg.setStandardButtons(QMessageBox.Ok|QMessageBox.Cancel)
                buttonConnect = msg.button(QMessageBox.Ok)
                buttonConnect.setText('Ok')
                msg.setInformativeText("Click 'Ok' and set the parameters in the config.yaml file or click 'Cancel' to continue in offline mode")
                button = msg.exec()
                if button == QMessageBox.Ok:
                    sys.exec()
                elif button == QMessageBox.Cancel:
                    self.offline_mode = True

    def connect_to_neasnom(self):
        if "nea_tools" not in sys.modules:
            return

        # self.path_to_dll = ''# yaml.load('config.yaml')
        path_to_dll = self.config['path_to_dll']
        fingerprint = self.config['fingerprint']
        host = 'nea-server'
        
        if self.connected:
            print('\nDisconnecting from neaServer!')
            nea_tools.disconnect()
            self.SetPowerPushButton.setEnabled(False)
            self.SetPointSpinBox.setEnabled(False)
            self.AutoFindPushButton.setEnabled(False)
            self.lcdNumber.setEnabled(True)
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
        # if self.connected:
        # self.sensor_value = self.context.Microscope.Py.EnergySensor
        self.sensor_value = self.powersensor.get_power()-self.sensor_offset
        self.setpoint_error = self.SetPointSpinBox.value() - self.sensor_value
        self.lcdNumber.display(self.sensor_value)

    def receive_offset(self,value):
        self.sensor_offset = value

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

    def JustGoHome(self):
        self.ro.home()
        self.statusbar.showMessage(f"Moved HOME to: {self.ro.get_angle()}")
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
        P = 5
        angle_step = self.setpoint_error*P
        if angle_step > 10:
            angle_step = 10
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

    def status_bar_update(self,m):
        self.statusbar.showMessage(m)

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
                print(f'{self.deviceport} port could NOT be closed')

            try:
                self.powersensor.close()
                print(f'{self.powersensor.name} closed')
            except:
                print(f'{self.powersensor.name} could NOT be closed')

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