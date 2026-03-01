# TypeK Branch Details

## Commit 1 contents (shareable upstream)

### PWM fixes (LEDs don't work without these)
- `config.h`: `WS2812_PWM_FREQUENCY 80000`
- `halconf.h`: `HAL_USE_PAL TRUE`
- `mcuconf.h`: `STM32_PWM_USE_ADVANCED TRUE`

### VIA indicator system (`typek.c`)
- 3 RGB indicators with per-LED HSV color, brightness, function assignment
- Functions: caps/num/scroll lock, layer 0-7
- EEPROM persistence via `eeconfig_update_kb_datablock` (needs `EECONFIG_KB_DATA_SIZE`)
- VIA custom channel for runtime config
- Generic `indicators_callback()` — uses VIA-configured colors, no hardcoded layer colors

### Board modernization (`keyboard.json`)
- `LAYOUT_all`/`LAYOUT_nosplits` → single `LAYOUT`
- Added `extrakey`, `mediakey` features
- `nkro: false` (USB endpoint limit)
- EEPROM: `backing_size` 4096→16384, added `embedded_flash` driver, `logical_size: 4096`
- `dynamic_keymap.layer_count: 8`

### Keymaps
- `default/keymap.c`: updated `LAYOUT_all` → `LAYOUT`
- `via/keymap.c`: generic keymap mirroring default (2 layers)
- `via/rules.mk`: `VIA_ENABLE = yes` only

## Commit 2 contents (personal)

### Config (`config.h`)
- `OS_DETECTION_KEYBOARD_RESET`
- `HOLD_ON_OTHER_KEY_PRESS`
- `PERMISSIVE_HOLD`
- `TAPPING_TERM 200`

### OS detection (`typek.c`)
- `process_detected_host_os_kb()`: macOS/Linux → layer 0, Windows → layer 1

### Custom layer colors (`typek.c`)
- `indicators_callback()`: layer-based hue overrides (red/blue/purple/magenta)
- `layer_state_set_user()`: underglow color per layer

### Custom VIA keymap
- CTL_ESC (ctrl on hold, esc on tap)
- 4 layers (base, fn, base-swapped-gui/alt, fn2 with media/rgb)
- `OS_DETECTION_ENABLE = yes` in rules.mk
