# AutoQCLPower   [![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]
Motorized power adjuster for the QCL laser.

This mod uses some of the components that are already in the instrument, e.g. the stationary and the rotating polarizers. Since the laser is polarized, we need a rotating linear polarizer to decrease the power and then another, fixed linear polarizer to reset the polarization to the tip axis. The manual rotation mount needs to be replaced with the assembly shown in the CAD folder.

## Parts list
- [Thorlabs ELL14K - Rotation Mount Bundle: ELL14 Mount, Interface Board, Power Supply, Cables](https://www.thorlabs.com/thorproduct.cfm?partnumber=ELL14K)
- [CP36 - 30 mm Cage Plate](#)([https://www.thorlabs.com/thorproduct.cfm?partnumber=ELL14K](https://www.thorlabs.com/thorproduct.cfm?partnumber=CP36))
- [ER05-P4 cage rods](https://www.thorlabs.com/thorproduct.cfm?partnumber=ER05-P4)
- [SM1L06 lens tube](https://www.thorlabs.com/thorproduct.cfm?partnumber=SM1L05)
- [SR05 Assembly rods](https://www.thorlabs.com/thorproduct.cfm?partnumber=SR05-P4)

## Control software

The Elliptec components can be controlled with the software provided by Thorlabs.

TODO: We will soon provide a cleaner, more simple interface.

## Warning

Pay attention to setup the initial cross-polarized rotation configuration and block the laser before large-range wavelength tuning as the power can increase sharply. 

### License

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg
