# Contributing

Contributions are welcome. DeskRecordor is experimental, so please keep
documentation and feature claims aligned with behavior that has been tested.

## Before opening a change

1. Open an issue for substantial changes or behavior questions.
2. Keep changes focused and avoid adding unneeded runtime dependencies.
3. Run the tests with `pytest`.
4. For packaging changes, run `./build-deb.sh` on Debian and inspect the
   resulting package metadata.
5. For capture changes, document the exact desktop, session type, permission
   flow, and output validation used.

Do not include recordings, personal data, or screenshots containing private
desktop content in issues or pull requests.
