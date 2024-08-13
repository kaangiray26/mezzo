document.addEventListener("DOMContentLoaded", () => {
    // Redirect to path if needed
    const params = new URLSearchParams(window.location.search);
    if (params.has("path")) {
        window.history.replaceState(
            {},
            document.title,
            window.location.pathname,
        );
        route(params.get("path"));
    }
    window.mezzo = new Mezzo();
});

class Mezzo {
    constructor() {
        this.queue = [];
        this.player = new Howl({
            src: [null],
            format: ["flac", "mp3", "ogg", "wav", "aac", "m4a", "opus", "webm"],
            preload: true,
            html5: true,
            volume: 1,
        });

        this.player.on("load", () => {
            this.on_track_loaded();
            this.listen_progress();
            update_ref("player_play", "pause");
        });

        console.log("Mezzo player initialized.");
    }

    async on_track_loaded() {
        this.player.play();
        let duration = this.player.duration();
        update_ref("player_duration", formatTime(duration));
    }

    async listen_progress() {
        this.player._sounds[0]._node.addEventListener("timeupdate", () => {
            let duration = this.player.duration();
            let position = this.player.seek();
            let percent = (position / duration) * 100;
            let val = `width: ${percent}%;`;

            update_ref("progress", val);
            update_ref("player_current_time", formatTime(position));
        });
    }

    async play() {
        if (this.player.playing()) {
            this.player.pause();
            update_ref("player_play", "play_arrow");
            return;
        }
        this.player.play();
        update_ref("player_play", "pause");
    }

    async playAlbum(uuid) {
        // Get album songs
        let res = await fetch(`/album/${uuid}/songs`).then((res) => res.json());

        // Add songs to queue
        this.queue = res["songs"];

        // Start playing
        this.playQueue();
    }

    async playSong(uuid) {
        // Get song info
        let res = await fetch(`/stream/${uuid}/basic`).then((res) =>
            res.json(),
        );
        console.log(res);

        // Update UI
        update_ref("player_cover", `/cover/${res.cover}`);
        update_ref("player_title", res.name);
        update_ref("player_artist", res.artist);

        this.player.unload();
        this.player._src = `/stream/${uuid}`;
        this.player.load();
    }

    async playArtist(uuid) {
        // Get artist songs
        let res = await fetch(`/artist/${uuid}/songs`).then((res) =>
            res.json(),
        );

        // Add songs to queue
        this.queue = res["songs"];

        // Start playing
        this.playQueue();
    }

    async seek(float) {
        let duration = this.player.duration();
        this.player._sounds[0]._node.currentTime = duration * float;
    }

    async playQueue() {
        if (this.queue.length === 0) {
            return;
        }

        let song = this.queue.shift();
        this.playSong(song);
    }

    async next() {
        // Play next song
        let song = this.queue.shift();
        this.playSong(song);
    }

    async prev() {
        return;
    }

    async openQueue() {
        // Get songs
        let res = await fetch("/queue", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(this.queue),
        }).then((res) => res.text());
        let dialog = document.querySelector("dialog");
        dialog.innerHTML = res;
        dialog.showModal();
    }

    async closeQueue() {
        let dialog = document.querySelector("dialog");
        dialog.close();
    }
}

function update_ref(key, val) {
    // Find element with attribute ref="key"
    let el = document.querySelector(`[ref="${key}"]`);
    let src_to = el.attributes.getNamedItem("ref_to");

    if (src_to) {
        el.setAttribute(src_to.value, val);
        return;
    }
    el.innerText = val;
}

function formatTime(secs) {
    let seconds = parseInt(secs);
    let minutes = Math.floor(seconds / 60);
    seconds = seconds % 60;
    return minutes + ":" + (seconds < 10 ? "0" : "") + seconds;
}

async function seek(click) {
    // Get progress bar
    let progress = document.querySelector(".progress-bar");

    // Get bounding box of progress bar
    let rect = progress.getBoundingClientRect();

    // Get relative position of mouse
    let point = (click.clientX - rect.left) / rect.width;

    window.mezzo.seek(point);
}

async function search(ev, query) {
    // Check for enter key
    if (ev.key !== "Enter") {
        return;
    }

    // Get search query
    let response = await fetch(`/query?q=${query}`).then((res) => res.text());

    // Render the content into the <search-results> element
    document.querySelector("search-results").innerHTML = response;
}

async function focusSearch() {
    document.querySelector("search input").focus();
}
