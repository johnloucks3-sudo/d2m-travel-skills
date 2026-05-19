# CLI COLOR THEME PROPOSAL (D2M STANDARDS)

## Color Palette (ANSI Mapping)
- **Primary Success (Chartreuse):** `\e[38;5;154m`
- **Primary Alert (Blue - Command Channel):** `\e[38;5;27m`
- **Secondary Alert (Cream - Background/System):** `\e[38;5;230m`
- **Error (Red):** `\e[38;5;196m`

## Implementation Protocol
1. Export these as standard env vars (`D2M_COL_SUCCESS`, etc.) in `~/.bashrc`.
2. Apply to all CLI output scripts using `printf` or `echo -e`.
3. Hale instances (Alpha/Bravo) will align response headers to these color codes.
