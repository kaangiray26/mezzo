async function route(url) {
    // Fetch the content
    let res = await fetch(url, {
        headers: {
            "X-Requested-From": "router",
        },
    }).then((res) => res.text());

    // Render the content into the <router-view> element
    document.querySelector("router-view").innerHTML = res;

    // Update the URL
    window.history.pushState({}, "", url);
}
