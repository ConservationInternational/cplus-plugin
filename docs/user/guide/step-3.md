# Step 3: Priority weighting

The final step deals with the **Weighting priorities** and **Priority groups**. These weights will be applied when the user starts running the scenario. An example is shown in **Figure 1**.

- Weight values range from 0 to 5, and affect how important a PWL is compared to other layers.

- A value of 0 indicates that the PWL has a lower importance.

- A value of 5 means that the PWL has a higher importance

![CPLUS step 3](img/plugin-step3_2.png)

*Figure 1: Step 3 allows the user to set the Weights of each Priority Group*

The priority weighting layers can be selected, added and removed into each priority group by using the 
arrow buttons. 

## Add priority layers

Select the target layer from the priority weighting layers list and the destination group from the priority groups and use the left arrow button ![left arrow](img/cplus_left_arrow.svg) to add the layer to the group.

## Remove priority layers

Select the target layer from the priority weighting layers list from its priority group and use the right arrow button ![right arrow](img/cplus_right_arrow.svg) to remove the layer to the group.

## Create custom priority layers

- Click on ![add button](img/symbologyAdd.svg) to add a new custom priority layer, or ![edit button](img/mActionToggleEditing.svg) to edit an existing priority layer.

- This will open the Priority Layer dialog (see **Figure 2**).

- The following parameters need to be set:
    - **Priority layer**: The layer that represents the priority layer.
    - **Priority layer name**: A unique identifier for the priority layer.
    - **Priority layer description**: A detailed description of the priority layer.

- Click the **Assign activities** button to select activities to be associated with the priority layer (see **Figure 3**)

![Priority layer editing/adding dialog](img/manual-priority-layer-dialog.png)

*Figure 2: Priority layer dialog*

- Select the activities you want to be associated with the priority layer.

- Click **OK**.

![Priority layer editing/adding dialog](img/manual-pwl-selection.png)

*Figure 3: Activity selection for priority layers*

- ![remove button](img/symbologyRemove.svg): Remove the selected PWL.

## Setting groups values

Move the slider to adjust the weight of each group, values can also be set manually, by using the left input spin box. Once done selecting weights, click the **Run Scenario** button to run the analysis.
