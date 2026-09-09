# gok TypeK QMK Firmware Folder

![TK](https://i.imgur.com/0ZEbEZt.jpg)

## Introduction

This is the QMK Firmware repository for the Type K, the tented ergo by Gok. The TypeK went through GB on August, 2023. It is supported by a proprietary PCB ecosystem.

## How to flash

### Enter bootloader

The DFU state in the bootloader can be accessed in 3 ways:

* **Bootmagic reset**: Hold down the key at (0,0) in the matrix (usually the top left key, escape in the default keymap) and plug in the keyboard;
* **Physical reset button**: press the button on the front of the PCB, next to caps lock, for at least five seconds;
* **Keycode in layout**: Press the key mapped to `RESET`; in the default layout, that is top left key ('escape') in layer 1.

### How to compile and flash

And use dfu-util in the command line or through a GUI like QMK toolbox to upload the firmware to the PCB. To directly flash the PCB after it is put into a DFU state, use:

    qmk flash -kb typek -km via

See the [build environment setup](https://docs.qmk.fm/#/getting_started_build_tools) and the [make instructions](https://docs.qmk.fm/#/getting_started_make_guide) for more information. Brand new to QMK? Start with our [Complete Newbs Guide](https://docs.qmk.fm/#/newbs).

## VIA on Linux

The board exposes its VIA interface as a raw HID device (usage page `0xFF60`). On Linux the matching `/dev/hidraw*` node is root-only by default, so [usevia.app](https://usevia.app) can see the keyboard through WebHID but gets no response ("does not seem to respond like a VIA-enabled keyboard"). Grant the logged-in user access with a udev rule:

    # /etc/udev/rules.d/70-typek-via-uaccess.rules
    SUBSYSTEM=="hidraw", ATTRS{idVendor}=="7179", ATTRS{idProduct}=="8475", TAG+="uaccess"

Then `sudo udevadm control --reload` and replug the keyboard. Older `qmk_udev` helpers (e.g. the 0.1.2 bundled with the Arch `qmk` 1.2.0 package) only grant access to the console interface, not raw HID, which is why this rule is needed even with the QMK udev rules installed. Current upstream `qmk_udev` tags raw HID too.

## Host-driven layer switching (raw HID)

The VIA keymap accepts one extra raw-HID command, outside VIA's id range, so a host daemon can turn a layer on or off — e.g. the gaming layer while a game has focus. Report layout (32 bytes, unused bytes zero):

    [0x42, layer, state]    state: 1 = layer_on, 0 = layer_off

Handled in `via_command_kb` in `typek.c`; layers outside the dynamic keymap range are ignored, and no reply is sent. The Linux daemon that drives it is `typek-layerd` in [ksc98/rigtop](https://github.com/ksc98/rigtop): it follows Hyprland focus events and matches the focused window's class or executable against `~/.config/typek-layerd/allowlist`. It needs the same hidraw udev rule as VIA above.
