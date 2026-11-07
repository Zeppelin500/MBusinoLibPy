# dev_issues - internal development notes

This folder holds the **internal development notes** of the MBusinoLibPy
port. They are written for the people working on the port - full of technical
detail (C++ line references, test internals, known quirks) - and are **not
meant for end users**. The notes are in English, like the rest of the
repository.

**User documentation lives in the [root README](../README.md).**

## Contents

| File | What it is |
|------|------------|
| [port-notes.md](port-notes.md) | The original, detailed port documentation: function-by-function notes, frame layout, differences from the C++ library, test/golden-file internals, credits. |
| [open-points.md](open-points.md) | Open points and unclean things noticed while porting - each with fundstelle, status and a suggested fix. |

If you are looking for installation instructions, the API reference or error
handling, use the [root README](../README.md) instead.
