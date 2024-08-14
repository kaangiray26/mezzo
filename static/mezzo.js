// Event Listeners
window.onpopstate = (event) => {
    route(window.location.pathname);
};

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

        this.player.on("end", () => {
            this.track_finished();
        });

        // mediaSession
        navigator.mediaSession.playbackState = "none";
        navigator.mediaSession.setActionHandler("play", () => {
            this.play();
        });
        navigator.mediaSession.setActionHandler("pause", () => {
            this.play();
        });
        navigator.mediaSession.setActionHandler("nexttrack", () => {
            this.next();
        });
        navigator.mediaSession.setActionHandler("previoustrack", () => {
            this.prev();
        });

        // Set boolean states
        this.is_dialog_open = false;

        // Mouse click event
        document.addEventListener("click", (ev) => {
            // Check for dialog
            if (this.is_dialog_open) this.dialogCheck();
        });

        // ESC key event
        document.addEventListener("keydown", (ev) => {
            if (ev.key === "Escape") this.dialogCheck();
        });

        console.log("Mezzo player initialized.");
    }

    async dialogCheck() {
        if (this.is_dialog_open) this.closeAllDialogs();
    }

    async track_finished() {
        // Checks for playing modes
        // TODO: Add shuffle and repeat modes
        // Play next song
        this.playQueue();
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
        // Check if any song is loaded
        if (!this.player._src[0]) return;

        // Play or pause
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
        // Load song
        this.player.unload();
        this.player._src = `/stream/${uuid}`;
        this.player.load();

        // Get song info
        let res = await fetch(`/stream/${uuid}/basic`).then((res) =>
            res.json(),
        );

        // Update UI
        update_ref("player_cover", `/cover/${res.cover}`);
        update_ref("player_title", res.name);
        update_ref("player_artist", res.artist);

        // Update media session
        navigator.mediaSession.metadata = new MediaMetadata({
            title: res.name,
            artist: res.artist,
            album: res.album,
            artwork: [
                {
                    src: `/cover/${res.cover}`,
                    sizes: "512x512",
                    type: "image/png",
                },
            ],
        });

        // Update window title
        document.title = `${res.name} - ${res.artist}`;
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
        if (!this.queue.length) return;

        let song = this.queue.shift();
        this.playSong(song);
    }

    async next() {
        if (!this.queue) return;

        // Play next song
        let song = this.queue.shift();
        console.log(song);
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
        let dialog = document.querySelector("#dialog");
        dialog.innerHTML = res;
        dialog.showModal();
    }

    async closeQueue() {
        let dialog = document.querySelector("#dialog");
        dialog.close();
    }

    async openContext(ev, el, song, artist, album) {
        ev.stopPropagation();

        // Get dropdown
        let dropwdown = el.parentElement.querySelector(`.dropdown-menu`);
        dropwdown.setAttribute("open", "true");
        this.is_dialog_open = true;
    }

    async openSettings(ev, el) {
        ev.stopPropagation();

        // Get dropdown
        let dropwdown = document.querySelector(`#settings`);
        dropwdown.setAttribute("open", "true");
        this.is_dialog_open = true;
    }

    async closeAllDialogs() {
        let dialogs = [...document.querySelectorAll(".dropdown-menu")];
        dialogs.map(async (dialog) => dialog.removeAttribute("open"));
        this.is_dialog_open = false;
    }

    async exit() {
        await fetch("/exit", {
            method: "POST",
        });
        // What to do here?
        window.location.href = "about:blank";
    }

    async addToQueue(song) {
        this.queue.push(song);
    }

    async goToAlbum(album) {
        route(`/album/${album}`);
    }

    async goToArtist(artist) {
        route(`/artist/${artist}`);
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
