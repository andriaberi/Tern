# Tern

[![CI](https://github.com/andriaberi/Tern/actions/workflows/ci.yml/badge.svg)](https://github.com/andriaberi/Tern/actions/workflows/ci.yml)

A statically typed systems language compiling to native x86-64, written from scratch in C.

## Building

| Command | Description |
|---|---|
| `make` / `make all` | Build the compiler to `build/tern` |
| `make test` | Build, then run the test suite |
| `make asan` | Build with AddressSanitizer + UBSan into `build/asan/` and run the test suite |
| `make clean` | Remove the `build/` directory |
| `make CC=clang` | Build with a different C compiler (works with any target) |

See [docs/SPEC.md](docs/SPEC.md) for the language specification.

## License

Released under the [MIT License](LICENSE).
