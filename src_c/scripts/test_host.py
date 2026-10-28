"""Build/run the same pure C++ logic used by the firmware, then verify assets."""
import hashlib
import shutil
import struct
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compiler = shutil.which("g++") or shutil.which("clang++")
if not compiler:
    raise SystemExit("Install g++ or clang++ and add it to PATH.")
out = root / "test/bin"
out.mkdir(parents=True, exist_ok=True)
binary = out / "test_core.exe"
subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
                "-I"+str(root / "include"), str(root / "src/core.cpp"),
                str(root / "test/test_core.cpp"), "-o", str(binary)], check=True)
subprocess.run([str(binary)], check=True)
files = list((root / "data/transitions").glob("*.mph"))
assert len(files) == 51
for path in files:
    data = path.read_bytes()
    assert data[:4] == b"MPH1" and data[6] == 7, path
    pos = 7
    for _ in range(data[6]):
        count, = struct.unpack_from("<H", data, pos)
        pos += 2
        for _ in range(count):
            x,y,color = struct.unpack_from("<BBH", data, pos)
            assert x < data[4] and y < data[5], path
            pos += 4
    assert pos == len(data), path
for directory in ("faces", "transitions", "static"):
    source = root.parent / "src" / directory
    if source.exists():
        for path in source.iterdir():
            if path.is_file():
                target = root / "data" / directory / path.name
                assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest(), path
print("51 MPH files validated; reference asset hashes match.")
