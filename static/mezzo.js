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
            this.player.play();
            update_ref("player_play", "pause");
        });

        console.log("Mezzo player initialized.");
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
        console.log("Track info:", res);
        update_ref("player_title", res.title);
        update_ref("player_artist", res.artist);

        console.log("Playing track:", uuid);
        this.player.unload();
        this.player._src = `/stream/${uuid}`;
        this.player.load();
    }
}

function update_ref(key, val) {
    // Find element with attribute ref="key"
    document.querySelector(`[ref="${key}"]`).innerText = val;
}
