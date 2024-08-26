#!/bin/sh

# Copy the profile directory to the correct location
PROFILE_DIR="$HOME/.var/app/org.flatpak.mezzo/data/profile"
if [ ! -d "$PROFILE_DIR" ]; then
    cp -r /app/profile "$PROFILE_DIR"
fi

# Start the hypercorn server
python3 -m hypercorn /app/app:app --bind '127.0.0.1:5000' &
HYPERCORN_PID=$!
echo "Hypercorn PID: $HYPERCORN_PID"

# Start Firefox
/app/firefox/firefox --no-remote --new-instance --profile "$PROFILE_DIR" --url http://127.0.0.1:5000
echo "Firefox closed!"

# Send a SIGINT to the hypercorn server
echo "Sending SIGINT to Hypercorn:"
kill -2 $HYPERCORN_PID
sleep 5
exit 0