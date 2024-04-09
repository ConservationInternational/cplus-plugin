## How to apply CPLUS settings?

The CPLUS settings provide users with a customizable interface to configure various aspects of the platform according to their needs and preferences. Users can access the CPLUS settings through either the QGIS options or the CPLUS toolbar.

### Accessing CPLUS Settings

QGIS options (**Figure 1**):

- Click on **Settings** -> **Options**

![QGIS settings](img/settings-qgis.png)

*Figure 1: QGIS settings*

- Select the *CPLUS* tab to the left.
- This will open the CPLUS settings dialog. See **Figure 2** for an example.

![CPLUS settings](img/settings-cplus-tab.png)

*Figure 2: CPLUS section as loaded in the QGIS settings dialog*

CPLUS toolbar (**Figure 3**):

- Click on the CPLUS toolbar drop-down.
- Select **Settings**.
- This will take you directly to the CPLUS settings dialog in the QGIS options.

![CPLUS plugin toolbar icon](img/plugin-toolbar-icon.png)

*Figure 3: CPLUS toolbar button*

A short description of each available setting a user can change. Most are optional, but the user needs to set the base directory as it's a requirement for the processing to work (e.g. outputs are stored in the base directory). Another important option to consider is snapping, as it will improve analysis results.

### Overview of Available Settings

**Configure Analysis**:

- Settings will be added as the plugin development continues.

**Reports**:

- Information that will be included when a report is generated. These settings are optional and will be excluded from the report if not provided.

- **Organization**: The organization(s) to be included in the report.
- **Contact Email**: Contact email for the author.
- **Website**: A website link to the project or company.
- **Custom logo**: Enable and provide a custom logo of your choosing. If disabled, the CI logo will be used in the report.
- **Footer**: Footer section for the report.
- **Disclaimer**: A disclaimer to be added to the report.
- **License**: A license to be added to the report.

**Advanced**:

- **Base data directory** (required): Data accessed and downloaded by the plugin will be stored here.
- **Coefficient for carbon layers**: Value applied during processing to the carbon-based layers. The default is 0.
- **Pathway suitability index**: Index multiplied by the pathways. A lower value means the pathway is less important, higher value means it's more important.

- **Snapping**: Will set rasters to match the cell alignment of a reference layer.
    - **Resample method**: Resampling performed on pixel values.
    - **Reference layer**: The reference layer to which the cell alignment will be applied.
    - **Rescale values**: Rescale values according to cell size.

**Figure 4** shows an example of updating and applying CPLUS settings.

![CPLUS settings example](img/settings-recording.gif)

*Figure 4: CPLUS settings example*

## How to perform the analysis?

**Figure 5** shows the toolbar button/menu for the plugin. Clicking on the icon will open the plugin. When a user clicks on the drop-down button, they will be presented with four options:

- **CPLUS**: Close or open the plugin dock widget.
- **Settings**: Open the settings for the plugin.
- **Help**: Takes the user to the online guide for the plugin.
- **About**: This will take the user to the About section on the GH pages.

![CPLUS plugin toolbar icon](img/plugin-toolbar-icon.png)

*Figure 5: CPLUS toolbar icon*

Open the CPLUS dock widget by clicking on the CPLUS toolbar icon (**Figure 5**).

Overall, the CPLUS settings offer users the flexibility to tailor the platform to their specific requirements and optimise their workflow for conducting analyses and generating reports.
