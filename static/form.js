function displayProgress(document, data) {
    document.getElementById("results").innerHTML = data;
}

// Copied from Stackoverflow.
function isValidHttpUrl(string) {
    let url;    
    try {
      url = new URL(string);
    } catch (_) {
      return false;  
    }
    return url.protocol === "http:" || url.protocol === "https:";
  }
  
async function submitForm(event, document) {
    event.preventDefault();

    // Set up progress tracking.
    const taskIdResp = await fetch('/newtask');
    const taskId = await taskIdResp.json()
    console.log('task id', taskId);

    var refreshId = setInterval(function() {
        fetch('/progress/' + taskId)
            .then(resp => resp.json())
            .then(data => displayProgress(document, data))
            .catch(err => {
                console.error(err);
            });
    }, 200);

    // URL validation. This has to come after a new task ID is created
    // to properly cancel a running task.
    url_drama = document.getElementById('target_drama').value;
    if (!isValidHttpUrl(url_drama)){
        clearInterval(refreshId);
        console.log('Bad URL: ' + url_drama);
        displayProgress(document, 'Bad URL: ' + url_drama + '. Did you forget to add https://?');
        return;
    }
    url_user = document.getElementById('user_list').value;
    if (!isValidHttpUrl(url_user)){
        clearInterval(refreshId);
        console.log('Bad URL: ' + url_user);
        displayProgress(document, 'Bad URL: ' + url_user + '. Did you forget to add https://?');
        return;
    }

    // Intersection.
    var formElement = document.getElementById('inputForm');
    var data = new FormData(formElement);
    data.append("taskId", taskId);
    fetch('/intersector', {
        method: 'POST',
        body: data
    }).then(resp => {
        clearInterval(refreshId);
        return resp.text();
    }).then(resp => {
        document.getElementById("results").innerHTML
            = resp;
    }).catch(err => {
        clearInterval(refreshId);
        console.error(err);
    });
}