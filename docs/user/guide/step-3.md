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

- Weight values range from 0 to 5, and affect how important a PWL is compared to other layers.
- A value of 0 indicates that the PWL has a lower importance.

- A value of 5 means that the PWL has a higher importance

![CPLUS step 3](img/plugin-step3_2.png)

*Figure 1: Step 3 allows the user to set the Weights of each Priority Group*

## Priority groups

 The `Priority groups` are used to assign weights to specific activities or layers based on their importance.

## Add priority groups

To add a new priority group, the user must click on the ![add button](img/symbologyAdd.svg) button, as shown  in **Figure 1**.

This will open a `Priority Group Dialog` box, where user required to fill the following information.

* **Group name:** Name of the group.
* **Group description:** Description of the group.
* **Group value:** Numeric value that reflect the importance of the priority layer.
* **Assign priority layers:** Assign Priority Layers allows users to allocate importance values to different geographic layers.

    * To assign a priority layer, click on the `Assign priority layers` and select from the available layers in the list.(see **Figure 3**)

![Priority Dialog](./img/plugin-step3_11.png)

*Figure 2: Priority  Group Dialog*

After filling in the required information, click on the `OK` button to add it to the `Priority groups`.

![Assign Priority Layer](./img/plugin-step3_12.png)

*Figure 3: Assign priority layers*

## Edit group layer

Select the layer and click on the ![edit button](img/mActionToggleEditing.svg) icon. This will open the `Priority Group Dialog`, allowing you to edit the group name, group description, group value, and assign new priority layers. 

![Priority Dialog](./img/plugin-step3_11.png)

*Figure 4: Priority Group Dialog Edit*

Click `OK` to apply the changes.

## Remove group layer

Select the layer and click on the ![remove button](img/symbologyRemove.svg) to remove the layer from the priority group.

## Prority Weighting Layers

The priority weighting layers can be selected, added and removed into each priority group by using the arrow buttons. 

## Add priority layers

Select the target layer from the priority weighting layers list and the destination group from the priority groups and use the left arrow button ![left arrow](img/cplus_left_arrow.svg) to add the layer to the group.

## Remove priority layers

Select the target layer from the priority weighting layers list from its priority group and use the right arrow button ![right arrow](img/cplus_right_arrow.svg) to remove the layer to the group.

## Create custom priority layers

- Click on ![add button](img/symbologyAdd.svg) to add a new custom priority layer, or ![edit button](img/mActionToggleEditing.svg) to edit an existing priority layer.

- This will open the Priority Layer dialog (see **Figure 5**).
  
## Methods to create layers

### Method 1: Create manually

- The following parameters need to be set:
    - **Priority layer**: The layer that represents the priority layer.
    - **Priority layer name**: A unique identifier for the priority layer.
    - **Priority layer description**: A detailed description of the priority layer.
 
- Click the **Assign activities** button to select activities to be associated with the priority layer (see **Figure 6**)

![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-1.png)

*Figure 5: Priority layer dialog*

- Select the activities you want to be associated with the priority layer.

- Click **OK**.
  
![Priority layer editing/adding dialog](img/manual-pwl-selection.png)

*Figure 6: Activity selection for priority layers*

### Method 2: Create Online

![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-2.png)

- After clicking on this option a drop down menu will appear with the available online defaults. 
  
![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-3.png)

- Select the desired online default.
  
![Priority layer editing/adding dialog](img/manual-priority-layer-dialog-4.png)

- Then click on the 1️⃣ `OK` button, to add the priority layer to PWL.
       
- ![remove button](img/symbologyRemove.svg): Remove the selected PWL.

## Create a new financial priority layer Net Present Value (NPV)

- Click on the ![File image](./img/mActionNewMap.svg) icon to add a new financial priority layer.

- This will open the Financial priority layer dialog. By default, on first-time load, the NPV configurations for all activities are disabled.

    ![NPV dialog](./img/plugin-step3_5.png)

- To enable the NPV for an activity, check the NPV Priority Weighting Layer group box.

    ![NPV configuration enable](./img/plugin-step3_4.png)

- Enter the number of years and discount rate. Then, input the revenue and cost values for the respective years. The greyed out cells (i.e., Year and Discount Value) indicate that these values are automatically populated.

- On updating the discount rate, revenue, and cost values, the total NPV is automatically updated.

- For an enabled NPV PWL, all revenue and cost values must be specified. Otherwise, an error message will appear in the message bar indicating which activity(ies) and corresponding years have missing values. This occurs when the user tries to create or update the PWLs:

    ![Error Message](./img/plugin-step3_6.png)

- It is recommended to leave the Use computed NPVs checkbox enabled (the default option). This ensures that the minimum and maximum normalisation values can be synced and automatically updated when user input changes. The min/max values will be based on enabled NPV parameters for activities. Disabled NPV parameters (in the group box) will be excluded when computing the min/max normalisation values.

    ![Computed NPVs](./img/plugin-step3_7.png)

- When the Remove existing PWLs for disabled activity NPVs checkbox is enabled, any previously created NPV PWLs will be deleted when updating the NPVs.

    ![Remove existing](./img/plugin-step3_8.png)

- Click on Update button to create the new financial priority layer. A dialog showing the progress of creating/updating the NPVs will be displayed.

    ![Update button](./img/plugin-step3_9.png)

- Upon creating NPV PWL rasters, the corresponding PWLs will be created or updated in the list of PWLs. The naming convention for these layers will be [activity name] NPV Norm:

    ![](./img/plugin-step3_10.png)

- An NPV layer, which is a constant raster containing the normalised value, will be created under the {BASE_DIR}/priority_layers/npv directory. The extents are based on the user-defined extents from Step 1.

## Setting groups values

Move the slider to adjust the weight of each group, values can also be set manually, by using the left input spin box.

Click [here](step-4.md) to explore the step 4 section.

Click [here](logs.md) to explore the log section.
