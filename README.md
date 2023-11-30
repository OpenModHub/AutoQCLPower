# AutoQCLPower   [![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]
Motorized power attenuator for QCL laser.

This mod uses some of the components that are already in the instrument, e.g. the stationary and the rotating polarizers. Since the laser is polarized, we need a rotating linear polarizer to decrease the power and then another, fixed linear polarizer to reset the polarization to the tip axis. The manual rotation mount needs to be replaced with the assembly shown in the CAD folder.

## Parts list

### Thorlabs

- [ELL14K - Rotation Mount Bundle](https://www.thorlabs.com/thorproduct.cfm?partnumber=ELL14K)
- [CP36 - 30 mm Cage Plate](https://www.thorlabs.com/thorproduct.cfm?partnumber=CP36)
- [ER05-P4 cage rods](https://www.thorlabs.com/thorproduct.cfm?partnumber=ER05-P4)
- [SM1L06 lens tube](https://www.thorlabs.com/thorproduct.cfm?partnumber=SM1L05)
- [SR05 Assembly rods](https://www.thorlabs.com/thorproduct.cfm?partnumber=SR05-P4)

The final assembly looks like this:

![cad_design](/images/fulassembly.png)

## Control software

The Elliptec components can be controlled with the [software provided by Thorlabs](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ELL).

OR

You can use our custom Python application (software/RotatorControlApp.py) that can control the rotator and use the power meter which is built in neaSNOM instrument to autoset the desired power level.

## How to use

1. Only use the attenuator

The software starts without connecting to the SNOM server machine. In this mode, you can control the rotating polarizer in the attenuator and monitor the power level from neaSCAN.

2. Use the attenuator with the SNOM power meter

If you want to use the automatic power settings you have to connect to the neaSNOM server machine. When you are connected you can see the power readings and use the automatic power adjustment.
## ⚠️Warning⚠️

1. Pay attention to setting up the initial cross-polarized rotation configuration and block the laser before large-range wavelength tuning as the power can increase sharply.
2. Make sure to change:
   - **path_to_dll**, **fingerprint**, **host** variables in **connect_to_neasnom** function
3. Check the requirements file for the module versions
4. The software was tested with:
   - neaSCAN 2.2.10875
   - neaServer 2.1.11062.0
   - Python 3.9.10 64 bit

### License

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg
