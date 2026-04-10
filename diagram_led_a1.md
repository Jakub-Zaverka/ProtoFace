# Zapojeni LED na A1 + potenciometr na A2

```
3V -----(krajni pin potenciometru)
A2 -----(prostredni pin potenciometru)
GND ----(druhy krajni pin potenciometru)

A1 ---[220 az 330 ohm]---|>|--- GND
                         LED
```

- delsi nozicka LED (anoda) smerem k rezistoru a pinu `A1`
- kratsi nozicka LED (katoda) smerem na `GND`
- rezistor je nutny, jinak muzes LED nebo pin poskodit
- potenciometr pripoj na `3V`, `A2`, `GND`
- na `A2` dej vzdy prostredni pin potenciometru
- pokud se jas otaci opacne, prohod dva krajni piny potenciometru
