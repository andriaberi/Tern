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

## A taste of Tern

Three primitive types (`int`, `char`, `bool`), slices, structures, tagged unions and generics;
one conditional (`when`) and one loop (`loop`); explicit memory with `new` and `delete`.

### FizzBuzz

```tern
fn main() {
    loop [ int i = 1 .. 101 ] {
        when {
            i % 15 == 0 => out ("FizzBuzz\n");
            i % 3 == 0  => out ("Fizz\n");
            i % 5 == 0  => out ("Buzz\n");
            _           => out ("${i}\n");
        }
    }
}
```

### Sieve of Eratosthenes

```tern
fn main() {
    const int N = 100;
    []bool composite = new [N + 1]bool;

    loop [ int i = 2 .. N + 1 ] {
        when composite[i] => continue;
        out ("${i} ");
        loop [ int j = i * i; j <= N; j += i ] {
            composite[j] = true;
        }
    }
    out ("\n");

    delete composite;
}
```

### Quicksort, in place, with sub-slices

```tern
fn swap(@int a, @int b) {
    int t = @a;
    @a = @b;
    @b = t;
}

fn quicksort([]int a) {
    when a.len < 2 => return;

    int pivot = a[a.len - 1];
    int store = 0;
    loop [ int i = 0 .. a.len - 1 ] {
        when a[i] < pivot => {
            swap(&a[i], &a[store]);
            store++;
        }
    }
    swap(&a[store], &a[a.len - 1]);

    quicksort(a[.. store]);       // shares a's elements: nothing is copied
    quicksort(a[store + 1 ..]);
}

fn main() {
    [8]int numbers = [38, 27, 43, 3, 9, 82, 10, 3];
    quicksort(numbers);
    loop [ int i = 0 .. numbers.len ] {
        out ("${numbers[i]} ");
    }
    out ("\n");                   // 3 3 9 10 27 38 43 82
}
```

### Evaluating an expression tree

An `enum` is a tagged union, and `when` is how its variants are taken apart. Used as an
expression, `when` must cover every variant.

```tern
enum Expr {
    Num { int value; }
    Add { @Expr left, right; }
    Mul { @Expr left, right; }
    Neg { @Expr operand; }
}

fn eval(@Expr e) -> int {
    return when @e {
        Num n => n.value;
        Add a => eval(a.left) + eval(a.right);
        Mul m => eval(m.left) * eval(m.right);
        Neg n => -eval(n.operand);
    };
}

fn num(int value) -> @Expr {
    return new Expr.Num { value: value };
}

fn main() {
    // (2 + 3) * -4
    @Expr e = new Expr.Mul {
        left:  new Expr.Add { left: num(2), right: num(3) },
        right: new Expr.Neg { operand: num(4) }
    };
    out ("${eval(e)}\n");         // -20
}
```

### Balanced brackets, with a generic stack

```tern
struct Stack[T] {
    []T items;
    int len;
}

fn push[T](@Stack[T] s, T x) {
    when s.len == s.items.len => {
        []T bigger = new [s.items.len * 2 + 4]T;
        loop [ int i = 0 .. s.len ] { bigger[i] = s.items[i]; }
        delete s.items;
        s.items = bigger;
    }
    s.items[s.len] = x;
    s.len++;
}

fn pop[T](@Stack[T] s) -> T {
    s.len--;
    return s.items[s.len];
}

fn balanced([]char text) -> bool {
    Stack[char] open;
    bool ok = true;

    loop [ int i = 0 .. text.len ] {
        char c = text[i];
        when c {
            '(', '[', '{' => push(&open, c);
            ')', ']', '}' => {
                when open.len == 0 => { ok = false; break; }
                char o = pop(&open);
                ok = when c { ')' => o == '('; ']' => o == '['; _ => o == '{'; };
                when !ok => break;
            }
        }
    }

    ok = ok && open.len == 0;
    delete open.items;
    return ok;
}

fn main() {
    []char good = "{ a[i] = (b + c); }";
    []char bad  = "f(x[1)]";
    out ("${balanced(good)}\n");  // true
    out ("${balanced(bad)}\n");   // false
}
```

### `wc`: counting a file's lines, words and characters

`main` can take the command-line arguments, and an `in` into a `char` reads one character at
a time, whitespace included, so a whole file can be read exactly as it is.

```tern
fn main([][]char args) -> int {
    when args.len != 2 => {
        out ("usage: ${args[0]} <file>\n");
        return 1;
    }

    int lines = 0, words = 0, chars = 0;
    bool inWord = false;
    char c;

    loop [ in [ args[1] ] (c) == 1 ] {
        chars++;
        when c {
            ' ', '\t', '\r' => inWord = false;
            '\n' => {
                lines++;
                inWord = false;
            }
            _ => {
                when !inWord => words++;
                inWord = true;
            }
        }
    }

    out ("${lines} ${words} ${chars} ${args[1]}\n");
    return 0;
}
```

## License

Released under the [MIT License](LICENSE).
