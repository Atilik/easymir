# Bundled wheels

Why bundle at all? Two dependencies are not on PyPI. Installing them from
their git URLs (a) requires `git`, which fresh Macs only get via the Xcode
Command Line Tools, and (b) for madmom, compiles C code on the user's machine
— which failed on end-user machines (e.g. a macOS 26 SDK/linker mismatch:
`ld: tapi error … arm64e.x1 unknown architecture`). Bundling both wheels makes
the install compiler-free AND git-free.

## beat_this-1.1.0-py3-none-any.whl

- **Source:** https://github.com/CPJKU/beat_this tag `v1.1.0`
  (commit `ad79748…`); pure-Python wheel, works on any platform.
- **Built:** 2026-09-29 (`pip wheel --no-deps`), unmodified.
- **sha256:** `8a56f9847c8e51a00a523cb12fbba8983a97599a3060d45efc22acbb71cc6dc2`
- **License:** MIT (CPJKU).

## madmom-0.17.dev0-cp311-cp311-macosx_11_0_arm64.whl

madmom has no usable PyPI release for modern numpy, so it must come from
source — but compiling C extensions on end users' machines was the single
most common installation failure (missing/foreign compiler setups). This
prebuilt wheel removes compilation from the install entirely, and with it the
whole Xcode Command Line Tools requirement.

- **Source:** https://github.com/CPJKU/madmom
  commit `27f032e8947204902c675e5e341a3faf5dc86dae`
- **Built:** 2026-09-29 on macOS/Apple Silicon, CPython 3.11,
  build deps per madmom's own pyproject (`cython>=0.25`, `numpy>2`;
  numpy 2.4 ABI — matches environment.yml's pin)
- **sha256:** `4269cd33b327e5a5d1737fb04bbf49da0031210567b584005da7fee92a691dbb`
- **License:** madmom is BSD-licensed (CPJKU); this wheel is an unmodified
  build of the commit above.

### Rebuild it yourself

```bash
python -m pip wheel \
  "madmom @ git+https://github.com/CPJKU/madmom@27f032e8947204902c675e5e341a3faf5dc86dae" \
  --no-deps --no-cache-dir -w wheels/
```

Rebuild whenever the pinned numpy major version changes (a mismatched build
fails at import with "numpy.dtype size changed").

### Linux

The bundled wheel is macOS/arm64-only. On Linux, install the compiler
toolchain of your distro and run, inside the activated env:

```bash
pip install "madmom @ git+https://github.com/CPJKU/madmom@27f032e8947204902c675e5e341a3faf5dc86dae"
```
