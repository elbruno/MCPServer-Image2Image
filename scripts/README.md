# Virtual Environment Scripts

This folder contains small helper scripts to activate and deactivate the project's Python virtual environment (`venv`) on Windows and Linux/macOS.

Windows (PowerShell)

- Activate (dot-source to affect current session):

```
. .\scripts\activate_venv.ps1
```

- Deactivate (dot-source to affect current session):

```
. .\scripts\deactivate_venv.ps1
```

Windows (Command Prompt)

- Activate:

```
\scripts\activate_venv.bat
```

- Deactivate:

```
\scripts\deactivate_venv.bat
```

Linux / macOS (bash)

- Activate (source to affect current shell):

```
source scripts/activate_venv.sh
```

- Deactivate (run after activation):

```
deactivate
# or
source scripts/deactivate_venv.sh
```

Notes

- Make sure the `venv` virtual environment exists (created with `python -m venv venv`).
- PowerShell scripts should be dot-sourced (prefix with a dot and space) so they modify the current shell environment.
- The scripts assume `venv` sits at the repository root as `./venv`.
