# Cyber track exports

Browse the [current editable export](cyber-tracks/) for cyber tracks organized by
domain. Its TOML files mirror the [canonical community packs](../packs/community/)
and retain the same track IDs and contents.

The versioned ZIP files are release snapshots. They retain their original folder
layouts for compatibility; the editable export uses the current domain folders.
`python scripts/package_tracks.py` builds an archive from that export and checks
each pack against its canonical source.
