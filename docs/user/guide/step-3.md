---
title: Conservation International
summary:
    - Jeremy Prior
    - Ketan Bamniya
date:
some_url:
copyright:
contact:
license: This program is free software; you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.
---

# Step 3: Priority weighting

The final step deals with the **Weighting priorities** and **Priority groups**. These weights will be applied when the user starts running the scenario. An example is shown in **Figure 1**.

- Weight values range from 0 to 5, and affect how important a Priority Weighting Layer (PWL) is compared to other layers.
- A value of 0 indicates that the PWL has a lower importance.

- A value of 5 means that the PWL has a higher importance.

<br>

![CPLUS step 3](img/plugin-step3_2.png)

*Figure 1: Step 3 allows the user to set the weights of each Priority Group*

<br>

## Priority Groups

 The `Priority groups` are used to assign weights to specific PWLs based on their importance. These PWLs 
are subsequently applied during the weighting of NCS pathways when creating a scenario analysis.

<br>

### Add priority groups

To add a new priority group, the user must click on the ![add button](img/symbologyAdd.svg) button, as shown in **Figure 1**.

This will open a `Priority Group Dialog` box, where user required to fill the following information.

* **Group name:** Name of the group.
* **Group description:** Description of the group.
* **Group value:** Numeric value that reflect the importance of the priority layer.
* **Assign priority layers:** This allows users to allocate importance values to different PWLs.

    * To assign a priority layer, click on the `Assign priority layers` and select from the available PWLs in the list.(see **Figure 3**)

<br>

![Priority Dialog](./img/plugin-step3_11.png)

*Figure 2: Priority  Group Dialog*

<br>

After filling in the required information, click on the `OK` button to add it to the `Priority groups`.

<br>

![Assign Priority Layer](./img/plugin-step3_12.png)

*Figure 3: Assign priority layers*

<br>

### Edit group layer

Select the layer and click on the ![edit button](img/mActionToggleEditing.svg) icon. This will open the `Priority Group Dialog`, allowing you to edit the group name, group description, group value, and assign new priority layers.

<br>

![Priority Dialog](./img/plugin-step3_11.png)

*Figure 4: Priority Group Dialog Edit*

<br>

Click `OK` to apply the changes.

<br>

### Remove group layer

Select the layer and click on the ![remove button](img/symbologyRemove.svg) to remove the layer from the priority group.

<br>

## Prority Weighting Layers

The priority weighting layers can be selected, added and removed into each priority group by using the arrow buttons.

<br>

### Add priority layers

Select the target layer from the priority weighting layers list and the destination group from the priority groups and use the left arrow button ![left arrow](img/cplus_left_arrow.svg) to add the layer to the group.

<br>

### Remove priority layers

Select the target layer from the priority weighting layers list from its priority group and use the right arrow button ![right arrow](img/cplus_right_arrow.svg) to remove the layer to the group.

<br>

## Create custom priority layers

- Click on ![add button](img/symbologyAdd.svg) to add a new custom priority layer, or ![edit button](img/mActionToggleEditing.svg) to edit an existing priority layer.

- This will open the Priority Layer dialog (see **Figure 5**).

<br>
  
### Methods to create layers

#### Method 1: Create manually

- The following parameters need to be set:
    - **Priority layer**: The layer that represents the priority layer.
    - **Priority layer name**: A unique identifier for the priority layer.
    - **Priority layer description**: A detailed description of the priority layer.
 
- Click the **Assign NCS Pathways** button to select NCS pathways to be associated with the priority layer (see **Figure 5**)

<br>

![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-1.png)

*Figure 5: Priority layer dialog*

<br>

- Select the NCS pathways you want to be associated with the priority layer (see **Figure 6**).

- Click **OK**.

<br>
  
![Priority layer editing/adding dialog](img/manual-pwl-selection.png)

*Figure 6: NCS pathway selection for priority layers*

<br>

#### Method 2: Create Online

![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-2.png)

<br>

- After clicking on this option a drop down menu will appear with the available online defaults.

<br>
  
![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-3.png)

<br>

- Select the desired online default.

<br>
  
![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-4.png)

<br>

- Select the applicable NCS pathways, then click on the 1️⃣ `OK` button, to create the PWL.
       
- Click the Remove PWL button ![remove button](img/symbologyRemove.svg) to remove one or more of the selected PWLs from the list.

<br>

## Matrix of Relative Impact Values

The Matrix of Relative Impact Values is used to assign impact coefficients to describe how each pathway influences each Priority Weighting Layer (PWL). These coefficients range from –3 to +3 and are evaluated separately from the PWL weightings.

The system also clearly distinguishes between impact-based and fragmentation-based PWLs, ensuring that the correct type of coefficient is applied during evaluation.

<br>

### Opening the Matrix Manager

To open the Matrix of Relative Impact Values Manager, first ensure that a Priority Weighting Layer is selected.

1. Use the ![add button](img/symbologyAdd.svg) button to add a new custom priority layer.

2. Select a layer from the Priority Weighted Layers panel.

3. Click the `Create Matrix of Relative Impact Values` button to open the manager.

<br>

![Opening Matrix Manager](./img/plugin-step3_13.png)

<br>

### Assigning Impact Coefficients

In the Matrix Manager, each pathway and PWL pair is represented in a table. Enter an impact coefficient between –3 and +3 to indicate the relative influence of that pathway on the selected PWL.

These coefficients are stored and used during model evaluation alongside, but independently from, the weighting values applied to PWLs.

<br>

![Matrix of Relative Impact Values Manager](./img/plugin-step3_14.png)

<br>

## Create a new financial priority layer Net Present Value (NPV)

- Click on the ![File image](./img/mActionNewMap.svg) icon to add a new financial priority layer.

- This will open the Financial priority layer dialog. By default, on first-time load, the NPV configurations for all NCS pathways are disabled.

    <br>

    ![NPV dialog](./img/plugin-step3_5.png)

    <br>

- To enable the NPV for an NCS pathway, check the NPV Priority Weighting Layer group box.

    <br>

    ![NPV configuration enable](./img/plugin-step3_4.png)

    <br>

- Enter the number of years and discount rate. Then, input the revenue and cost values for the respective years. The greyed out cells (i.e., Year and Discount Value) indicate that these values are automatically populated.

- On updating the discount rate, revenue, and cost values, the total NPV is automatically updated.

- For an enabled NPV PWL, all revenue and cost values must be specified. Otherwise, an error message will appear in the message bar indicating which NCS pathway(s) and corresponding years have missing values. This occurs when the user tries to create or update the PWLs:

    <br>

    ![Error Message](./img/plugin-step3_6.png)

    <br>

- It is recommended to leave the `Use computed NPVs` checkbox enabled (the default option). This ensures that the minimum and maximum normalisation values can be synced and automatically updated when user input changes. The min/max values will be based on enabled NPV parameters for NCS pathways. Disabled NPV parameters (in the group box) will be excluded when computing the min/max normalisation values.

    <br>

    ![Computed NPVs](./img/plugin-step3_7.png)

    <br>

- When the `Remove existing PWLs for disabled NCS pathway NPVs` checkbox is enabled, any previously created NPV PWLs will be deleted when updating the NPVs.

    <br>

    ![Remove existing](./img/plugin-step3_8.png)

    <br>

- Click on Update button to create the new financial priority layer. A dialog showing the progress of creating/updating the NPVs will be displayed.

    <br>

    ![Update button](./img/plugin-step3_9.png)

    <br>

- Upon creating NPV PWL rasters, the corresponding PWLs will be created or updated in the list of PWLs. The naming convention for these layers will be `[NCS pathway name] NPV Norm`:

    <br>

    ![](./img/plugin-step3_10.png)

    <br>

- An NPV layer, which is a constant raster containing the normalised value, will be created under the `{BASE_DIR}/priority_layers/npv` directory. The extents are based on the user-defined extents from Step 1.

## Setting groups values

Move the slider to adjust the weight of each group, values can also be set manually, by using the left input spin box.

<br>

Click [here](step-4.md) to explore the step 4 section.

Click [here](logs.md) to explore the log section.

<br>
