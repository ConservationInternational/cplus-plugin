#!/usr/bin/env bash
echo "🪛 Running QGIS with the CPLUS profile:"
echo "--------------------------------"
echo "Do you want to enable debug mode?"
choice=$(gum choose "🪲 Yes" "🐞 No" )
case $choice in
	"🪲 Yes") DEBUG_MODE=1 ;;
	"🐞 No") DEBUG_MODE=0 ;;
esac
echo "Do you want to enable experimental features?"
choice=$(gum choose "🪲 Yes" "🐞 No" )
case $choice in
	"🪲 Yes") CPLUS_EXPERIMENTAL=1 ;;
	"🐞 No") CPLUS_EXPERIMENTAL=0 ;;
esac

# Running on local used to skip tests that will not work in a local dev env
CPLUS_LOG=$HOME/CPLUS.log
rm -f $CPLUS_LOG
#nix-shell -p \
#  This is the old way using default nix packages with overrides
#  'qgis.override { extraPythonPackages = (ps: [ ps.pyqtwebengine ps.jsonschema ps.debugpy ps.future ps.psutil ]);}' \
#  --command "CPLUS_LOG=${CPLUS_LOG} CPLUS_DEBUG=${DEBUG_MODE} RUNNING_ON_LOCAL=1 qgis --profile CPLUS2"

# This is the new way, using Ivan Mincis nix spatial project and a flake
# see flake.nix for implementation details
CPLUS_LOG=${CPLUS_LOG} \
	CPLUS_DEBUG=${DEBUG_MODE} \
	CPLUS_EXPERIMENTAL=${CPLUS_EXPERIMENTAL} \
	RUNNING_ON_LOCAL=1 \
    nix run .#default -- qgis --profile CPLUS
