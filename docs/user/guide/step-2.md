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

# Step 2: Pathways and activities

This step deals with the **Natural Climate Solution (NCS) pathways** and the **Activities**. An NCS pathway can be defined as a composite spatial layer on specific land use classes and other factors that determine areas ideal for a specific use case (e.g. Animal management). An activity is a combination of NCS pathways represented in an AOI spatial layer. **Figure 1** shows the UI.

![CPLUS step 1](img/plugin-step2.png)

*Figure 1: Step 2 allows the user to create and edit NCS pathways and Activities*

Activities buttons:

- **Add**: Adds a new activity.

- **Delete**: Delete an activity.

- **Editing**: Edit an existing activity.

- **Ordering pixel value:** Edit activity order in the scenario analysis and output layer.

![CPLUS step 2 buttons](img/plugin-step2-buttons.png)

NCS pathways buttons:

- **Add**: Adds a new pathway.

- **Delete**: Delete a pathway.

- **Editing**: Edit an existing pathway.

- **Refresh view**: Checks the base directory for data.

- **Validation inspector:** Checks the validation of NCS pathways against a predefined set of rules.

![CPLUS step 2 pathways buttons](img/plugin-step2-pathways-buttons.png)

## How to add NCS pathway

Click on the left green plus button ![plus button](./img/plugin-step2-1.png) to add a new pathway (**Figure 3**).

**You can use two methods to add the NCS pathway**

### Method 1: Manually add NCS pathway

In this method, you will create a new NCS pathway by providing a name, description, and selecting the applicable map layer as shown in Figure 2 below.

![CPLUS step 1](img/ncs_pathway_editor_local_layer.png)

*Figure 2: Input fields in the NCS Pathway Editor when using a local map layer*

**Step 1 Enter NCS Pathway Details**

- In the `Name` field, enter name for your NCS pathway. This name will help you identify the pathway in the system.

- In the `Description` field, enter a brief description of the NCS pathway. This description will provide context and help others understand the purpose of the pathway.

**Step 2 Select Pathway Type**

* Pathway Type: Select the type of the NCS pathway.
    - **Protect:** Protect the world’s natural ecosystems from unsustainable practices and degradation.
    - **Manage:** Farming systems and working lands must shift from net carbon emitters to carbon sinks.
    - **Restore:** Restore ecosystem types and globally can reduce global greenhouse gas emissions and store additional carbon up to 3 gigatons annually.

**Step 3 Select Map Layer**
- Click the `Local map layer` radio button to load the widgets for specifying a map layer in your computer.
- In the `Map Layer` dropdown menu, select the map layer that is relevant to your NCS pathway. You can choose 
- from the list of available map layers that you have downloaded and imported into the system, or 
- from the layers in the QGIS map canvas.

For example, if you are creating an NCS pathway for Agroforestry, you would select the `Agroforestry` map layer.

**Step 4 Add NCS Pathway**

Once you have entered all the required details, click on the `OK` button to add the NCS pathway.

### Method 2 add using online default

In this method, you will add a new NCS pathway using online defaults. This option is available if you have an account on the Trends.Earth platform.

**Step 1 Add Online Defaults**

- Click the `Online defaults` radio button to load the layers in the online server.

- Choose the NCS pathway you want to use from the list of available options.

- Once you select the NCS pathway, the name and description fields will be automatically populated.

- Select the pathway type.

- Click on the `OK` button to add the NCS pathway.

![After online default](./img/plugin-step2-13.png)

*Figure 3: Input fields in the NCS Pathway Editor when using an online layer*

> If the NCS pathway is broken (e.g. layer or file cannot be found), the pathway text will have an exclamation mark next to it. The user will need to rectify the issue before continuing to step 3.

Add pathways to an existing activity:

- Select the activity to which a pathway should be added.

- Select the pathway you want to add to the activity.

- Click the right arrow ![right arrow](img/cplus_right_arrow.svg) to add a pathway to the selected activity.

- Click the double right arrow ![right arrow](img/cplus_double_right_arrows.svg) to add all pathways to the activity.

- The user can also drag and drop a pathway onto the desired activity.

### How to add a new activity?

- Click on the right green plus button to add an **activity** (**Figure 4**).

- Provide a **Name** and **Description**.

- (Optional) **Activity Mask** excludes specific areas, restricting pathways to a targeted activity.

- Click **OK**.

- The new **activity** will be added.

![Edit Activity Mask](./img/plugin-step2-5.png)

*Figure 4: Activity creator/editor*

### Activity Mask

Activity Masking enables users to exclude specific areas from pathways. This functionality helps in refining analyses by isolating regions that are not relevant or need to be avoided during operations.

#### How does the Activity Masking work?

Imagine planning a journey or mapping an area, and you want to exclude specific region like restricted zones, private properties, or hazardous locations. This masking tool allows you to mark those areas, ensuring they are excluded from your plans or analysis. It is like instructing the system, avoid these areas, enabling you to focus on relevant zones and create more precise and efficient plans.

* Here is the list of activities displayed without applying any mask. This means all areas are included, and no regions have been excluded or hidden from the analysis.

    ![Without Activity Mask 1](./img/plugin-step2-7.png)


* After applying the mask, the specified area becomes restricted for that particular activity. This ensures that no operations or tasks are carried out within that area, effectively excluding it from the analysis. As shown in the image below, after applying the mask, the specified area is marked as restricted for that particular activity. This restriction ensures that no operations or tasks related to the specific activity take place within the designated area, effectively excluding it from the further analysis.

    ![With Activity Mask 1](./img/plugin-step2-9.png)

#### How to add Activity Mask?

- Click on the **Activity Mask** checkbox. This will allow to add the activity mask.

- To add new activity mask click on the ![plus button](./img/plugin-step2-1.png) icon. This will open a `Select mask layer` pop up window. Select your desired 1️⃣ mask you want to add and then click on the 2️⃣ `Open` button.

    ![Activity Mask Selection](./img/plugin-step2-11.png)

- This process will add the mask on your activity.

#### Edit Activity Mask

- Select the activity mask and click on the ![Change Icon](./img/plugin-step2-rename-icon.png) icon. This will open a `Select mask layer` pop up window from where you choose your desired activity mask.

#### Delete Activity Mask

- Select the activity mask and click on the ![Delete Icon](./img/plugin-step2-delete-icon.png) icon. A confirmation dialog box will appear, allowing you to confirm the deletion of the selected activity mask or you can close the process.

    ![Delete Activity Mask](./img/plugin-step2-12.png)

### Ordering of the pixel values for the scenario output

- Open the Style pixel value editor by clicking on the ![CPLUS add implementation model](img/button_pixels_order.png) button.

- Select the activity which needs to be moved up or down in the stack.

- Drag-and-drop the activity where it needs to be in the stack.

- Click **OK** once done.

![CPLUS style pixel value editor](img/style_pixel_value_editor.png)

- The final step is to select each of the activities a user wants to include in the scenario run.
- A user can exclude activities if they do not want to include them, even if the activity has pathways.

![CPLUS selected IMs](img/plugin-selected-activities.png)

*Figure 5: Selected activities*

<blockquote>Before proceeding to Step 3, a user needs to define at least one NCS pathway layer for an activity, otherwise a warning message will be displayed. </blockquote>

Click [here](step-3.md) to explore the step 3 section.

Click [here](step-4.md) to explore the step 4 section.

Click [here](logs.md) to explore the log section.
