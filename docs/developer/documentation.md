# Working with documentation

Documentation is written using <a href="https://mkdocs.org/">mkdocs</a>.
A detailed description on getting-started with mkdocs is available <a href="https://www.mkdocs.org/getting-started/">here</a>.

## Install mkdocs

- Open the terminal
- Run "pip install mkdocs"
- This should install mkdocs and all requirements

## Creating a new project

This should not be required as the mkdocs has been created already, but serves more of a guide for
a user whom are new to mkdocs

- Open the terminal
- Run "mkdocs new ."
- This will generate the documents folder with the home page index markdown file

## Serving the pages locally

This step is useful when making changes and the user wants to test and review their changes to the mkdocs
before creating a pull request.

- Open the terminal
- Run "mkdocs serve"
- 

## GitHub pages

This is only required if it has not been set up on GitHub for the repository, or if it has been disabled.
Only a user with admin rights to the repository will be able to do this.

- Go to the repository and click on **Settings**
- Click on **Pages**
- Set the branch to "gh-pages"
- Click **Save**
- Select the action
- Select **Deploy**
- Open the Run mkdocs gh-deploy section
- The URL should be https://kartoza.github.io/cplus-plugin/
