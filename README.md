# CPLUS QGIS plugin
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/kartoza/cplus-plugin/ci.yml?branch=main)
![GitHub](https://img.shields.io/github/license/kartoza/cplus-plugin)


QGIS plugin for the CPLUS framework.

![image](https://github.com/Samweli/ci-cplus-scoping/assets/2663775/cbcfdad4-34c5-4214-a633-b6a5cdc2515c)


[![QGIS.org](https://img.shields.io/badge/QGIS.org-ondevelopment-yellow)](https://plugins.qgis.org/plugins/ci-cplus-plugin/)
[![Documentation](https://img.shields.io/badge/Documentation-onprogress-inactive)](https://github.com/kartoza/ci-cplus/actions/workflows/doc.yml)
[![Tests](https://img.shields.io/badge/Tests-onprogress-inactive)](https://github.com/kartoza/ci-cplus-plugin/actions/workflows/ci.yml)


### Versions

* Available and supported in all the QGIS 3.x versions

| Plugin version   | Minimum QGIS version | Maximum QGIS version |
|-------------|----------|------|
| 0.0.1   | 3.0          | 3.99 |

### Installation


During the development phase the plugin is available to install via 

a dedicated plugin repository 

[https://raw.githubusercontent.com/kartoza/cplus-plugin/release/docs/repository/plugins.xml](https://raw.githubusercontent.com/kartoza/cplus-plugin/release/docs/repository/plugins.xml)

[//]: # ()
[//]: # (#### Install from QGIS plugin repository)

[//]: # ()
[//]: # (- Open QGIS application and open plugin manager.)

[//]: # (- Search for `CPLUS` in the All page of the plugin manager.)

[//]: # (- From the found results, click on the `CPLUS` result item and a page with plugin information will show up. )

[//]: # (  )
[//]: # (- Click the `Install Plugin` button at the bottom of the dialog to install the plugin.)

[//]: # ()

#### Install from ZIP file

Alternatively the plugin can be installed using **Install from ZIP** option on the 
QGIS plugin manager. 

- Download zip file from the required plugin released version
https://github.com/kartoza/cplus-plugin/releases/download/{tagname}/cplus.{version}.zip or create one
using the admin interface as explained [here](https://github.com/kartoza/cplus-plugin#plugin-admin-interface).

- From the **Install from ZIP** page, select the zip file and click the **Install** button to install plugin

#### Install from custom plugin repository


- Open the QGIS plugin manager, then select the **Settings** page


- Click **Add** button on the **Plugin Repositories** group box and use the above url to create

the new plugin repository.

- The plugin should now be available from the list

of all plugins that can be installed.


Disable QGIS official plugin repository in order to not fetch plugins from it.

**NOTE:** While the development phase is on going the plugin will be flagged as experimental, make

sure to enable the QGIS plugin manager in the **Settings** page to show the experimental plugins

in order to be able to install it.


When the development work is complete the plugin will be available on the QGIS
official plugin [repository](https://plugins.qgis.org/plugins).


### Development 

To use the plugin for development purposes, clone the repository locally,
install pip, a python dependencies management tool see https://pypi.org/project/pip/

#### Create virtual environment

Using any python virtual environment manager create project environment. 
Recommending to use [virtualenv-wrapper](https://virtualenvwrapper.readthedocs.io/en/latest/).

It can be installed using python pip 

```
pip install virtualenvwrapper
```

 1. Create virtual environment

    ```
    mkvirtualenv cplus
    ```

2. Using the pip, install plugin development dependencies by running 

    ```
    pip install -r requirements-dev.txt
   ```

#### Plugin admin interface
The plugin contain an admin script that can be used for various development tasks.

Install the plugin into the QGIS application, activate virtual environment the use the below command.
```
 python admin.py install
```

Generate a plugin zip file using the below command, after successful run a plugin zip file will be located
on the `dist` folder under the plugin root folder.

```
python admin.py generate-zip
```