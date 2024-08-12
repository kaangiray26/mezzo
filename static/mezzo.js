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

    async playTrack(uuid) {
        // Get track info
        let res = await fetch(`/stream/${uuid}/basic`).then((res) =>
            res.json(),
        );

        // Update UI
        update_ref("player_title", res.name);
        update_ref("player_artist", res.artist);

        this.player.unload();
        this.player._src = `/stream/${uuid}`;
        this.player.load();
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
