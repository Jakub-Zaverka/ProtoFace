# Main Controller

Dummy PlatformIO project for Adafruit Matrix Portal S3.

## Deploy

```powershell
.\deploy.ps1
```

Upload and open serial monitor:

```powershell
.\deploy.ps1 -Monitor
```

If the board is not on COM4:

```powershell
.\deploy.ps1 -Port COM5
```

If upload fails, put the Matrix Portal S3 into bootloader mode by holding BOOT,
pressing RESET, releasing RESET, then releasing BOOT. The COM port may change in
bootloader mode.

