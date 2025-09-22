#!/usr/bin/env bash

qgis_setup.sh

# FIX default installation because the sources must be in "cplus_plugin" parent folder
rm -rf  /root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/cplus_plugin
ln -sf /tests_directory /root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/cplus_plugin
ln -sf /tests_directory /usr/share/qgis/python/plugins/cplus_plugin

pip3 install -r /tests_directory/requirements-testing.txt
