# Plugin guide

## Perform analysis

Open the CPLUS dockwidget by clicking on the CPLUS toolbar icon:

![CPLUS plugin toolbar icon](../img/plugin/plugin-toolbar-icon.png)

### Step 1: Scenario Information

The first step focusses on the **Scenario Information**. A *Scenario* refers to an overall analysis
done in an area of interest (AOI). Different criteria and priorities for spatial decision-making and
comparison will be considered for each scenario.

- **Scenario name**: A name for the analysis to be performed
- **Scenario description**: A detailed desription of the analysis
- **Extent**: The area of interest for this analysis. This can be calculated from the current
  canvas view extent, a layer, or an extent drawn by the user
- Once the information has been provided, click **Step 2**

![CPLUS step 1](../img/plugin/plugin-step1.png)

### Step 2: Pathways and models

This step deals with the **Natural Climate Solution (NCS) pathways** and the **Implementation models (IM)**.
A NCS pathway can be defined as a composite spatial layer on specific land use classes and other
factors that determine areas ideal for a specific use case (e.g. Animal mangement).
An IM is a combination of NCS pathways represented in an AOI spatial layer.

![CPLUS step 1](../img/plugin/plugin-step2.png)

Step 2 buttons:

- **Add**: Adds a new pathway or model
- **Editing**: Edit and existing pathway or model
- **Delete**: Delete a pathway or model

![CPLUS step 2 buttons](../img/plugin/plugin-step2-buttons.png)

#### NCS Pathway

- Click on the left green plus button to add a new pathway
- Provide a **Name** and **Description** for the pathway
- Two approaches to select a layer: A layer from the **QGIS canvas**, or **Upload from a file**
- Click **OK**
- The new **NCS pathway** will be added

```
NOTE: If the NCS pathway is broken (e.g. layer or file cannot be found), the pathway text
will be highlighted in red. The user will need to rectify the issue before continuing to
step 3.
```

![CPLUS add pathway](../img/plugin/plugin-pathway-editor.png)

#### Implementation model

- Click on the right green plus button to add an **Implementation model**
- Provide a **Name** and **Description**
- Click **OK**
- The new **Implementation model** will be added

![CPLUS add implementation model](../img/plugin/plugin-implementation-model.png)

### Step 3: Priority weighting

The final step deals with the **Weighting priorities** and **Priority groups**. These weights
will be applied when the user starts running the scenario.

![CPLUS step 3](../img/plugin/plugin-step3.png)

- Move the slider to adjust the weight of each group
- The user can also manually set the value
- Once the user is done selecting weights, click **Run Scenario**

## Report generating
