# Steps 1 to 3 example

The following recording (**Figure 1**) shows an example of how to do steps 1, 2 and 3. This is based on the pilot study area.

![Steps 1 to 3 example](img/steps_1_to_3.gif)

*Figure 1: Shows how to implement Steps 1, 2 and 3 in QGIS*

## Processing

- Once the user has provided all desired parameters, click **Run Scenario**.

- The processing dialog will open (**Figure 2**).

- The processing will take a while, depending on the number of activities and pathways provided for each activity.

- Click the **Cancel** button to stop the processing.

![Processing dialog running](img/plugin-processing-dialog.png)

*Figure 2: Processing dialog while the algorithm is running*

- **Figure 3** will be the result of the processing if succeeds.

- The user should take note that the **View Report** button is now available.

![Processing dialog success](img/plugin-processing-succeeded.png)

*Figure 3: Processing dialog if successful*

## Processing results

The following groups and layers will be added to the QGIS canvas once the processing finishes (see **Figure 4**):

- A group containing the Scenario results.

- **Activity Maps**: Non-weighted activities created by the user in Step 2.

- **Weighted Activity Maps**: Weighted activities based on the activities added in Step 2 and weighing set in Step 3.

- **NCS Pathways Maps**: Pathways used for each activity in Step 2. If an activity layer were provided as the activity in Step 2, this would contain no pathways.

![Layers added to a canvas](img/plugin-added-layers.png)

*Figure 4: Groups and layers added to the QGIS canvas*

An example of output results in QGIS is detailed in **Figure 5**

![Outputs example](img/outputs-qgis.gif)

*Figure 5: A recording example of an example scenario*

## Report generating

- Click the **View Report** button.

- The user will have the following options:
    - **Layout designer**: Opens the report in the QGIS layout designer.
    - **Open PDF**: Opens the report in PDF format.
    - **Help**: Open the help documentation related to the reports.

![Report options](img/plugin-report-options.png)

*Figure 6: Report options*

- **Figure 7** shows an example of a report opened in the layout designer.

![Report layout designer](img/report-layout-designer.png) 

*Figure 7: Report opened in the QGIS layout designer*

- **Figure 8** shows a report in PDF format.

![Report PDF](img/report-pdf.png)

*Figure 8: PDF version of a report*

## Generated report example

Here is an example of how to open a report in the QGIS layout designer, or as a PDF (**Figure 9**).

![Generated report example](img/generated-reports.gif)

*Figure 9: Example of a generated report in PDF and layout designer formats*
