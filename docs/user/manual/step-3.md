# Step 3: Weighting priorities

`Step 3` focuses on weighting priorities, which involves assigning importance to different priority groups and weighted layers. This step is critical for determining the relative significance of various factors in the analysis.

![UI Step 3](img/manual-step3.png)

- **Priority groups**: Users can define different priority groups to which Priority Weighted Layers (PWLs) can be assigned. These groups represent different categories or themes that contribute to the overall analysis.

- **Priority weighted layers (PWL)**: Users can assign importance values to each priority group by associating them with Priority Weighted Layers. These layers represent the spatial data layers or attributes that contribute to the analysis.

- ![right arrow](img/cplus_right_arrow.svg): Remove the selected PWL from the priority group.

- ![left arrow](img/cplus_left_arrow.svg): Add the selected PWL to the selected priority group.

- ![add button](img/symbologyAdd.svg): Add a new PWL.

- ![remove button](img/symbologyRemove.svg): Remove the selected PWL.

- ![edit button](img/mActionToggleEditing.svg): Edit the selected PWL.

- **Run Scenario**: Starts running the analysis. The progress dialog will open when the user clicks this button.

## Priority Weighted Layers Editor dialog

![UI Priority layer dialog](img/manual-priority-layer-dialog.png)

- **Priority layer**: Select the priority layer.

- **Priority layer name**: A unique name for the priority layer.

- **Priority layer description**: A detailed description for the priority layer.

- **Assign activities**: Selected activities associated with the priority layer.


![UI Priority layer dialog](img/manual-pwl-selection.png)

- List of activities a user can select. Multiple activities can be selected.

- **OK**: Save the selected activities.

- **Select All**: Select each of the available activities.

- **Clear Selection**: Deselects each of the selected activities.

- **Toggle Selection**: Switches each option from deselected to selected, or selected to deselected.

## Progress dialog

![Progress dialog](img/manual-processing-dialog.png)

- **Analysis Progress**: Progress of the current step.

- **Status**: A status message on the current analysis being performed.

- **View Report**: This button will remain disabled until the processing is done.

- **Cancel**: Clicking this button will stop the processing.

- **Close**: Only visible once the processing stops. Will close the progress dialog.

### Report options

These options will be available once the analysis has finished. The options will stay disabled if the analysis failed

![Report options](img/manual-report-options.png)

- **Layout designer**: Opens the report in the QGIS layout designer.

- **Open PDF**: Opens the created PDF.

- **Help**: Takes the user to the User's documentation site.

Overall, Step 3 provides users with tools to assign priorities and weights to different factors, guiding the analysis process and helping to identify key areas of focus in the scenario.
