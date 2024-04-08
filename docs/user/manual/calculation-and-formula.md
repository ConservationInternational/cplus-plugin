# Manual

The manual covers two sections. Firstly the workflow will be covered. This includes a discussion of the calculations
and formulas. This is so that a user can understand how the CPLUS processing workflow and calculations for each step are
done when processing the pathways and carbon layers, how the activities are created, algorithms applied to
create the priority weighted layer (weighted activity), and the last step, which is the highest position calculation.

The second section offers a succinct overview of each step, providing references to detailed explanations for further clarification. A description of the generated report is also provided.

## CPLUS calculations and formulas

**Figure 1** shows the workflow of the CPLUS model. The workflow can be split into four parts:

- Natural climate solution (NCS) weighted carbon pathway(s)
- Activity
- Priority weighted layer (Weighted activity)
- Highest position (Scenario result)

![QGIS highest position example](img/cplus-workflow.png)

*Figure 1: CPLUS workflow*

### NCS weighted carbon

The following steps/rules are considered to create the NCS weighted carbon layer(s):

- Carbon layers:
    - When multiple Carbon layers are provided, the average is calculated from the layers to create a single Carbon layer
    - The produced Carbon layer is multiplied by the Carbon coefficient provided by the user in the settings
    - If the Carbon coefficient is zero, the value is ignored
- NCS pathways:
    - Multiply the pathway raster with the Suitability index
    - If the index is zero, the pathway raster is used as-is
- **Equation 1** shows how the NCS weighted carbon layer is calculated

$$
\operatorname{NCS weighted carbon} ={CarbonCoefficient}\times{\frac{(Carbon_1 + Carbon_2 + .... + Carbon_n)}{n}} + ({SuitabilityIndex}\times{NcsPathway})
$$

*Equation 1: NCS weighted carbon* 

where *CarbonCoefficient* is the carbon coefficient value multiplied with the averaged carbon raster;

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *Carbon* is a carbon raster;

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *SuitabilityIndex* is the NCS pathway index value;

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *NcsPathway* is the NCS pathway raster; and

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *n* is the number of carbon rasters.

- The results from the above calculation are normalized to create the normalized NCS Weighted Carbon layer
- A normalized raster's pixel values range from 0 to 1
- Normalization is done as shown in **Equation 2**

$$
\operatorname{Normalized NCS weighted carbon} =\frac{value - min}{max - min}
$$

*Equation 2: Normalized NCS weighted carbon*

where *value* is the pixel value;

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *min* is the minimum value of the raster; and

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *max* is the maximum value of the raster.

### Activity

- Because an activity can consist of multiple pathways, the normalized results will be summed
- All NCS weighted carbon layers, as created from **Equation 2**, are summed as shown in **Equation 3** to
create the activity from the pathways

$$
\operatorname{Summed pathways} = NcsWeightedCarbon_1 + NcsWeightedCarbon_2 + ... + NcsWeightedCarbon_n
$$

*Equation 3: Summed pathways for the activity*

where *NcsWeightedCarbon* is a pathway set up by the user; and

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *n* is the number of pathways.

- Now that the pathways have been summed for the activity, the result needs to be normalized
- The Suitability index and the Carbon coefficient then needs to be taken into account after the normalized raster
has been created
- This calculation is shown in **Equation 4**

$$
\operatorname{Final activity} ={(SuitabilityIndex + CarbonCoefficient)}\times{\frac{value - min}{max - min}}
$$

*Equation 4: Final activity created from pathways*

where *value* is the pixel value;

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *min* is the minimum value of the raster;

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *max* is the maximum value of the raster;

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *SuitabilityIndex* is the NCS pathway index value; and

&emsp;&emsp;&nbsp;&nbsp;&nbsp; *CarbonCoefficient* is the carbon coefficient value multiplied with the averaged carbon raster.

- The resulting output is the final activity

### Priority weighted layer (Weighted activity)

- This step is performed after the activities have been created
- The PWL is more important, and will therefore be multiplied by five to take this into account
- The PWL weighted is calculated as shown in **Equation 5**

$$
\operatorname{Priority weighted layer} ={FinalActivity} + ({5}\times{Priority weighted layer})
$$

*Equation 5: Priority weighted layer (Weighted activity) calculation*

- The resulting PWL will then be used as input to the Highest position calculation

### Highest Position

The <a href="https://docs.qgis.org/3.28/en/docs/user_manual/processing_algs/qgis/rasteranalysis.html#qgishighestpositioninrasterstack">Highest position</a>
tool determines the raster in a stack with the highest value at a given pixel. Essentially the result
is a classification, where each class represents a specific activity. If multiple rasters has the highest
pixel value at a given pixel, the first raster with that pixel value in the stack will be used.
Figure 2 shows an example from the QGIS description of the Highest position tool.

![QGIS highest position example](img/qgis-highest-position-example.png)

*Figure 2: Highest position example*

In the plugin, the nodata values are ignored. This means that if at least one raster has a pixel value
at that cell there will be a raster stack value. If none of the rasters in the stack has a pixel value
at that cell (e.g. each raster pixel is nodata) the output will be nodata at that pixel.

Here is an explanation of how to use the **Highest position** tool:

- Figure 3 shows the layer for the Highest position at stack position 1

![QGIS layer 1](img/qgis-hp-stack-layer-1.png)

*Figure 3: Layer 1 used as the highest position input*

- Figure 4 shows the layer for the Highest position at stack position 2

![QGIS layer 2](img/qgis-hp-stack-layer-2.png)

*Figure 4: Layer 2 used as the highest position input*

- Figure 5 shows the result from the Highest position calculation (Scenario result)
    - *Stack layer 1* (blue): Figure 2 raster had the highest pixel value
    - *Stack layer 2* (red): Figure 3 raster had the highest pixel value

![QGIS highest position result](img/qgis-hp-result.png)

*Figure 5: Highest position result*

This concludes the section on how the calculations are done 

### References

- https://www.pnas.org/doi/10.1073/pnas.1710465114
- https://royalsocietypublishing.org/doi/10.1098/rstb.2019.0126

## Plugin

Detailed descriptions for each UI element of the plugin. This covers steps 1 to 3, dialogs,
and the settings UI.

### Dock widget

This is the main UI of the plugin. The dock widget opens on the right side of QGIS.
The dock widget consists of three tabs, each focussing on a particular phase of the analysis.
Here is a short description of those steps:

- **Step 1**: Scenario information. Click [here](step-1.md) for a detailed explanation.

- **Step 2**: NCS pathways and activities. Click [here](step-2.md) for a detailed explanation.

- **Step 3**: Weighting priorities (weighted activities). Click [here](step-3.md) for a detailed explanation.

For a detailed explanation of the plugin settings, the user can to refer the setting [documentation](settings.md)
