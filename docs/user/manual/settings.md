# Settings

![CPLUS settings](img/manual-settings.png)

## Reports

Under the Reports section, users can configure the information to be included in the generated reports. These settings include:

    - *Organization*: (optional) Organization or institute name.

    - *Contact email*: (optional) Contact email of the user.

    - *Website*: (optional) Link to the website of your company or institute.

    - *Custom logo*: (optional) If enabled, the user needs to provide a custom logo. Most formats should suffice (png, jpeg, etc.).

    - *Logo preview*: Visual preview of the default CI logo, or the custom logo a user selected.

    - *Footer*: (optional) Will be added to the report.

    - *Disclaimer*: Change as desired, otherwise use the default disclaimer.

    - *License*: Change as desired, otherwise use the default license description.

## Advanced

The Advanced settings section offers more detailed configuration options:

    - *Base data directory*: Directory to read data from, and to which results will be written.

    - *Coefficient for carbon layers*: Applied to carbon layers during processing.

    - *Pathway suitability index*: Index multiplied to the pathways. Lower values means the pathway is less important, and higher means its more important.

    - *Snapping*: Will set rasters to match the cell alignment of a reference layer.

        - *Resample method*: Resampling performed on pixel values.

            - *Nearest neighbour*: Closest pixel value. This will be best to use if a user wants to preserve the original pixel values.

            - *Bilinear*: Computes the pixel values from the two closest pixels (2 x 2 kernel).

            - *Cubic*: Computes the pixel values from the four closest pixels (4 x 4 kernel).

            - *Cubic B-Spline*: Cubic resampling based on B-Spline (4 x 4 kernel).

            - *Lanczos*: Lanczos windowed sinc interpolation (6 x 6 kernel).

            - *Average*: Computes the average of all non-nodata contributing pixels.

            - *Mode*: Select the value which appears most often of all the sampled pixels.

            - *Maximum*: Selects the maximum value which appears of all the sampled pixels.

            - *Minimum*: Selects the minimum value which appears of all the sampled pixels.

            - *Median*: Selects the median value which appears in all the sampled pixels.

            - *First quartile (Q1)*: Selects the first quartile value which appears in all the sampled pixels.

            - *Third quartile (Q3)*: Selects the third quartile value which appears in all the sampled pixels.

        - *Reference layer*: The reference layer to which the cell alignment will be applied.

        - *Rescale values*: Rescale values according to cell size.        

These settings provide users with flexibility and control over how the plugin operates and how reports are generated, ensuring that it meets their specific needs and preferences.
