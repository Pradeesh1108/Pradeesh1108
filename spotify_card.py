import base64
import os
import sys

import requests


def get_access_token(client_id, client_secret, refresh_token):
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_recently_played(access_token, limit=5):
    # Fetch extra tracks so deduplication still returns `limit` unique ones.
    fetch_limit = limit * 2
    response = requests.get(
        f"https://api.spotify.com/v1/me/player/recently-played?limit={fetch_limit}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    tracks = []
    seen = set()
    for item in items:
        track = item["track"]
        track_id = track["id"]
        if track_id not in seen:
            seen.add(track_id)
            tracks.append(
                {
                    "name": track["name"],
                    "artist": ", ".join(a["name"] for a in track["artists"]),
                }
            )
        if len(tracks) >= limit:
            break
    return tracks


def escape_xml(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


MAX_TRACK_NAME_LEN = 38
MAX_ARTIST_NAME_LEN = 42


def truncate(text, max_len=MAX_TRACK_NAME_LEN):
    return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"


def generate_svg(tracks):
    row_height = 44
    header_height = 56
    footer_padding = 16
    card_width = 480
    card_height = header_height + len(tracks) * row_height + footer_padding

    rows = ""
    for i, track in enumerate(tracks):
        y = header_height + i * row_height
        name = escape_xml(truncate(track["name"]))
        artist = escape_xml(truncate(track["artist"], MAX_ARTIST_NAME_LEN))
        rows += f"""
    <g transform="translate(0,{y})">
      <text x="20" y="16" fill="#bd93f9" font-size="13" font-weight="600"
            font-family="'Segoe UI',Helvetica,Arial,sans-serif">{i + 1}. {name}</text>
      <text x="32" y="32" fill="#6272a4" font-size="11"
            font-family="'Segoe UI',Helvetica,Arial,sans-serif">{artist}</text>
    </g>"""

    return f"""<svg width="{card_width}" height="{card_height}"
     viewBox="0 0 {card_width} {card_height}"
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#282a36"/>
      <stop offset="100%" stop-color="#1e2029"/>
    </linearGradient>
  </defs>
  <rect width="{card_width}" height="{card_height}" rx="12" ry="12"
        fill="url(#bg)" stroke="#44475a" stroke-width="1"/>
  <!-- Spotify icon (simplified) -->
  <circle cx="26" cy="28" r="12" fill="#1DB954"/>
  <ellipse cx="26" cy="24" rx="7" ry="2.5" fill="#fff" transform="rotate(-30,26,24)"/>
  <ellipse cx="26" cy="28" rx="5.5" ry="2" fill="#fff" transform="rotate(-30,26,28)"/>
  <ellipse cx="26" cy="32" rx="4" ry="1.5" fill="#fff" transform="rotate(-30,26,32)"/>
  <text x="46" y="33" fill="#50fa7b" font-size="15" font-weight="bold"
        font-family="'Segoe UI',Helvetica,Arial,sans-serif">Recently Played on Spotify</text>
  <line x1="20" y1="{header_height - 8}" x2="{card_width - 20}" y2="{header_height - 8}"
        stroke="#44475a" stroke-width="1"/>
  {rows}
</svg>
"""


def main():
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    refresh_token = os.environ["SPOTIFY_REFRESH_TOKEN"]

    access_token = get_access_token(client_id, client_secret, refresh_token)
    tracks = get_recently_played(access_token)

    if not tracks:
        print("No recently played tracks found; skipping SVG generation.")
        sys.exit(0)

    svg = generate_svg(tracks)

    os.makedirs("dist", exist_ok=True)
    with open("dist/spotify.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Generated dist/spotify.svg with {len(tracks)} track(s).")


if __name__ == "__main__":
    main()
