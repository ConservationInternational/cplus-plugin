# Running under Nix

## Assumptions:

1. You have direnv setup
2. You have flake support enabled
3. You have a QGIS profile called (case sensitive) CPLUS

## What to do the first time:

```bash
direnv allow
```

This will take a few minutes while it gets all runtime and developer dependencies.

```bash
python admin.py --qgis-profile CPLUS symlink
```

## What to do every time you want to run with updated code:


```bash
python admin.py build
./start_qgis.sh
```
