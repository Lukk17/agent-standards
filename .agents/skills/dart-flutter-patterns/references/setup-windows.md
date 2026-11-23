# Environment Setup on Windows

Contents:

- [Install the toolchain](#install-the-toolchain)
- [Target Android from Windows](#target-android-from-windows)
- [Package a Windows desktop release](#package-a-windows-desktop-release)
- [Checklist](#checklist)

Installing a Flutter toolchain on Windows and packaging a Windows desktop build. Pinning the SDK, the `flutter doctor` loop and the CI gate are the same on every platform and are in [environment-setup.md](environment-setup.md).

---

### Install the toolchain

Windows builds the Windows desktop target and Android. Two different Microsoft products are involved and they are
easy to confuse: Visual Studio compiles the native C++ for Windows desktop, VS Code is a code editor and cannot
do that job.

Install the SDK. Chocolatey handles the download, extraction, and `PATH` entry in one step:

```powershell
choco install flutter
```

Without Chocolatey, download the stable SDK zip and extract it to a path your user account owns. Never extract it
under `C:\Program Files`, because the tool writes into its own directory and will fail on permissions:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\flutter_windows_stable.zip" -DestinationPath C:\src
```

Append the SDK `bin` directory to the user `PATH`:

```powershell
[Environment]::SetEnvironmentVariable('Path', "$([Environment]::GetEnvironmentVariable('Path','User'));C:\src\flutter\bin", 'User')
```

Open a new terminal so the change takes effect, then confirm the tool resolves:

```powershell
(Get-Command flutter).Source
```

Install Visual Studio with the C++ workload, which is mandatory for the Windows desktop target:

```powershell
choco install visualstudio2022community --package-parameters "--add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended"
```

Install an editor and add the official Flutter and Dart extensions:

```powershell
choco install vscode
```

Validate the whole toolchain:

```powershell
flutter doctor -v
```

Accept the Android SDK licences, which `flutter doctor` will otherwise keep reporting as missing:

```powershell
flutter doctor --android-licenses
```

Confirm the targets, which must list `windows` and any attached Android device:

```powershell
flutter devices
```

---

### Target Android from Windows

Targeting Android from Windows:

- Physical device. Enable Developer Options and USB debugging on the phone, and install the OEM USB driver.
- Emulator. In the AVD manager, set Emulated Performance, Graphics acceleration to a Hardware option, or the
  emulator will run unusably slowly.

Disable any target you do not build for, so `flutter doctor` stops checking its toolchain:

```powershell
flutter config --no-enable-web
```

---

### Package a Windows desktop release

Packaging a Windows desktop release. Build it:

```powershell
flutter build windows
```

The output lands in `build\windows\x64\runner\Release\`. A distributable archive needs the executable, every
`.dll` beside it, the whole `data` directory, and the Visual C++ redistributables `msvcp140.dll`,
`vcruntime140.dll`, and `vcruntime140_1.dll`.

```powershell
Compress-Archive -Path build\windows\x64\runner\Release\* -DestinationPath dist\my_flutter_app.zip
```

The archive must have this shape:

```text
my_flutter_app.zip
    my_flutter_app.exe
    flutter_windows.dll
    msvcp140.dll
    vcruntime140.dll
    vcruntime140_1.dll
    data/
        app.so
        icudtl.dat
```

Self-signed certificate for MSIX packaging or local testing. Install OpenSSL and put its `bin` directory on
`PATH`, then generate the private key:

```powershell
openssl genrsa -out mykeyname.key 2048
```

Generate the certificate signing request:

```powershell
openssl req -new -key mykeyname.key -out mycsrname.csr
```

Sign it:

```powershell
openssl x509 -in mycsrname.csr -out mycrtname.crt -req -signkey mykeyname.key -days 10000
```

Export the `.pfx`:

```powershell
openssl pkcs12 -export -out CERTIFICATE.pfx -inkey mykeyname.key -in mycrtname.crt
```

Import it into Trusted Root Certification Authorities before installing the packaged app:

```powershell
Import-PfxCertificate -FilePath CERTIFICATE.pfx -CertStoreLocation Cert:\LocalMachine\Root
```

---

### Checklist

- [ ] Windows hosts have Visual Studio with the C++ workload, not just VS Code.
- [ ] Windows distributions include the three Visual C++ redistributable DLLs and the `data` directory.
