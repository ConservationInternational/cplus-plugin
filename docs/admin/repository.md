<html>
<body>
<div>
    <h2><a href="#pull"> Pull requests artifacts </a></h2>
</div>
<div id="pull_artifacts">
    <table>
        <thead>
        <tr>
        <th>PR title</th>
        <th>PR url</th>
        <th>Artifact name</th>
        <th>Artifact url</th>
        <th>Created date</th>
        </tr>
        </thead>

        <tbody id="tbody">
        </tbody>
    </table>
</div>

<div>
    <h2><a href="#main"> Main branch artifacts </a></h2>
</div>
<div id="main_artifacts">
    <table>
        <thead>
        <tr>
        <th>Branch commit </th>
        <th>Commit link</th>
        <th>Artifact name</th>
        <th>Artifact url</th>
        <th>Created date</th>
        </tr>
        </thead>

        <tbody id="main_tbody">
        </tbody>
    </table>
</div>

</body>

<script type="module">
import { Octokit, App } from "https://esm.sh/octokit";
const octokit = new Octokit();

const pulls = await octokit.request("GET /repos/kartoza/cplus-plugin/pulls", {'state':'all'});

const fetched_artifacts = await octokit.request("GET /repos/kartoza/cplus-plugin/actions/artifacts", {'per_page': 30});
const pulls_artifacts = [];
const commits_artifacts = [];


for ( const pull of pulls.data ){
    const head_sha = pull['head']['sha'];
    const pull_artifact = {};

    if (pull == undefined)
        continue;

    for ( const artifact of fetched_artifacts.data.artifacts){

        if ( artifact['workflow_run']['head_sha'] == head_sha &&
            artifact['name'].indexOf('cplus_plugin') != -1 ){
            pull_artifact['pull'] = pull;
            pull_artifact['artifact'] = artifact;
        }
    }
    pulls_artifacts.push(pull_artifact)
}

for ( const artifact of fetched_artifacts.data.artifacts){

    if ( artifact['name'].indexOf('cplus_plugin') == -1){
        continue;
    }
    const commit = await octokit.request("GET /repos/kartoza/cplus-plugin/commits/"+ artifact['workflow_run']['head_sha'] );


    if ( commit == undefined | commit.data.parents.length < 2 ){
        continue;
    }

    const commit_artifact = {
        'commit': commit,
        'artifact': artifact
    }

    commits_artifacts.push(commit_artifact)
}

const tbody = document.getElementById('tbody');
const main_tbody = document.getElementById('main_tbody');

for (const pull_artifact of pulls_artifacts){

        if (pull_artifact['pull'] == undefined)
        {
            continue;
        }

     const p = document.createElement('p');
     const tr = document.createElement('tr');
     const td_1 = document.createElement('td');
     const td_2 = document.createElement('td');
     const td_3 = document.createElement('td');
     const td_4 = document.createElement('td');
     const td_5 = document.createElement('td');

     const pull_link = document.createElement("a");
     const link_node = document.createTextNode(pull_artifact['pull']['title']);

     pull_link.appendChild(link_node);
     pull_link.textContent = pull_artifact['pull']['html_url'];
     pull_link.title = pull_artifact['pull']['html_url'];
     pull_link.href = pull_artifact['pull']['html_url'];

     td_1.appendChild(link_node);
     td_2.appendChild(pull_link);

     tr.appendChild(td_1);
     tr.appendChild(td_2);

     const artifact_link = document.createElement("a");
     const link_node_2 = document.createTextNode(pull_artifact['artifact']['name']);
     const date_node = document.createTextNode(pull_artifact['artifact']['created_at']);
     artifact_link.appendChild(link_node_2);
     artifact_link.textContent = pull_artifact['artifact']['archive_download_url']
     artifact_link.href = pull_artifact['artifact']['archive_download_url'];

     td_3.appendChild(link_node_2);
     td_4.appendChild(artifact_link);
     td_5.appendChild(date_node);

     tr.appendChild(td_3);
     tr.appendChild(td_4);
     tr.appendChild(td_5);

     tbody.appendChild(tr)

}

for (const commit_artifact of commits_artifacts){

     if (commit_artifact['commit'] == undefined)
     {
         continue;
     }
     console.log(commit_artifact['artifact']);

     const p = document.createElement('p');
     const tr = document.createElement('tr');
     const td_1 = document.createElement('td');
     const td_2 = document.createElement('td');
     const td_3 = document.createElement('td');
     const td_4 = document.createElement('td');
     const td_5 = document.createElement('td');

     const pull_link = document.createElement("a");
     const link_node = document.createTextNode(commit_artifact['commit']['data']['sha']);

     pull_link.appendChild(link_node);
     pull_link.textContent = commit_artifact['commit']['data']['html_url'];
     pull_link.title = commit_artifact['commit']['data']['html_url'];
     pull_link.href = commit_artifact['commit']['data']['html_url'];

     td_1.appendChild(link_node);
     td_2.appendChild(pull_link);

     tr.appendChild(td_1);
     tr.appendChild(td_2);

     const artifact_link = document.createElement("a");
     const link_node_2 = document.createTextNode(commit_artifact['artifact']['name']);
     const date_node = document.createTextNode(commit_artifact['artifact']['created_at']);
     artifact_link.appendChild(link_node_2);
     artifact_link.textContent = commit_artifact['artifact']['archive_download_url'];
     artifact_link.href = commit_artifact['artifact']['archive_download_url'];

     td_3.appendChild(link_node_2);
     td_4.appendChild(artifact_link);
     td_5.appendChild(date_node);

     tr.appendChild(td_3);
     tr.appendChild(td_4);
     tr.appendChild(td_5);

     main_tbody.appendChild(tr)

}

</script>

</html>
