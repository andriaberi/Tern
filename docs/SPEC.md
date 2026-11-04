# Tern Language Specification

**Version** 0.1.0 · **Status** Draft · **File extension** `.tn`

Tern is a general-purpose programming language built around minimal syntax, predictable behavior, and explicit control over program execution and memory.

- Three primitive types: `int` (32-bit signed), `char` (8-bit, 0 to 255), and `bool`.
- Fixed-size arrays, slices, sub-slices, data-only structures, and tagged unions.
- Generic structures and functions.
- A unified conditional, `when`, usable as a statement or an expression, and a unified loop statement, `loop`.
- Functions with overloading.
- Explicit pointers and memory management, with no hidden allocation.
- File-based modules.
- Built-in input and output, and command-line arguments.

Tern has no floating-point numbers and no cast syntax.

## Contents

1. [Overview](#1-overview)
2. [Lexical structure](#2-lexical-structure)
3. [Grammar](#3-grammar)
4. [Operator precedence](#4-operator-precedence)
5. [Types](#5-types)
6. [Declarations](#6-declarations)
7. [Statements and control flow](#7-statements-and-control-flow)
8. [Expressions and evaluation order](#8-expressions-and-evaluation-order)
9. [Memory model](#9-memory-model)
10. [Program entry and runtime](#10-program-entry-and-runtime)
11. [Diagnostics](#11-diagnostics)
12. [Example program](#12-example-program)
- [Appendix A. Not in this version](#appendix-a-not-in-this-version)
- [Appendix B. Syntax reference](#appendix-b-syntax-reference)

---

## 1. Overview

Tern follows a small set of syntactic conventions:

| Syntax | Purpose | Example |
|---|---|---|
| `()` | Lists: parameters, arguments, `in`/`out` data, imported and exported names; and grouping | `add(5, 10)`, `out ("hi\n");`, `import math (square);`, `(a + b) * c` |
| `[]` | Types, array literals, indexing, configuration, and type parameters | `[4]int`, `[1, 2, 3]`, `numbers[0]`, `loop [ i < 10 ]`, `Vec[int]` |
| `{}` | Code blocks, structures, enums, and `when` arms | `struct Point { ... }`, `when { ... }` |
| `=>` | Separates a `when` pattern from its body | `x > 0 => count++;` |
| `->` | Specifies a function's return type | `fn add(int a, int b) -> int` |
| `;` | Ends statements and separates configuration parts | `int x = 10;`, `loop [ int i = 0; i < 10; i++ ]` |
| `,` | Separates items in a list | `int i = 0, j = 10;`, `add(1, 2)` |
| `..` | A range of indexes or loop values | `s[1 .. 3]`, `loop [ int i = 0 .. 10 ]` |

Square brackets directly after `loop` (or its label), `in`, or `out` hold that construct's **configuration**; they are never array literals or indexing. Configuration always comes before the construct's body or data. Inside a configuration, `;` separates parts and `,` separates items within one part.

```tern
loop [ int i = 0 .. 10 ] {
    out ("${i}\n");
}
```

Program execution begins in `main`.

---

## 2. Lexical structure

### 2.1 Source files

Tern source files use the `.tn` extension and are encoded in UTF-8. Identifiers are ASCII-only; non-ASCII characters may appear only in comments and string literals.

### 2.2 Identifiers

Identifiers are case-sensitive.

```ebnf
identifier = ( letter | "_" ) { letter | digit | "_" } ;
letter     = "a" … "z" | "A" … "Z" ;
digit      = "0" … "9" ;
```

A lone `_` is not an identifier; it is a separate token ([§2.3](#23-keywords)).

```tern
int age;
int totalScore;
[]char studentName;
```

### 2.3 Keywords

```text
int       char      bool
const     struct    enum
fn        return
when      loop
break     continue
import    export
new       delete
in        out
true      false     null
```

`extern` and `defer` are reserved for future versions and cannot be used as identifiers.

The underscore `_` marks the default arm of a `when` and a skipped destination in `in`.

The type keywords `int`, `char`, and `bool` also serve as format names in the format part of a `${...}` interpolation ([§8.6](#86-string-interpolation)).

### 2.4 Literals

| Kind | Examples | Type | Notes |
|---|---|---|---|
| Integer | `0`, `42`, `0xFF` | `int` | Decimal, or hexadecimal after `0x` |
| Character | `'A'`, `'7'`, `'\n'`, `'\0'` | `char` | The character's code: `'A'` is `65` |
| Boolean | `true`, `false` | `bool` | |
| Null | `null` | Any pointer or slice | |
| String | `"Hello, world!"` | `[]char` | A read-only slice of characters ([§5.4](#54-strings)) |

```ebnf
integer_lit = digit { digit } | "0x" hex_digit { hex_digit } ;
hex_digit   = digit | "a" … "f" | "A" … "F" ;
char_lit    = "'" ( char | escape ) "'" ;
string_lit  = '"' { char | escape | interpolation } '"' ;
escape      = "\" ( "n" | "t" | "r" | "0" | "\" | "'" | '"' | "$" ) ;
```

`char` in this grammar is any source character other than a newline, a backslash, or the literal's own quote.

- An integer literal must not exceed 2147483647 (2³¹ − 1), with one exception: `2147483648` may appear directly after a unary `-`, so the smallest `int` can be written `-2147483648`.
- Digit separators are not supported.
- A character literal holds exactly one ASCII character or escape.
- A string literal holds one element per byte of its UTF-8 encoding. Strings have no terminator; their length is part of the slice.

In a string, `${` always begins an interpolation ([§8.6](#86-string-interpolation)); write `\$` for a literal dollar sign.

| Escape | Character |
|---|---|
| `\n` | Newline |
| `\t` | Tab |
| `\r` | Carriage return |
| `\0` | Null character |
| `\\` | Backslash |
| `\'` | Single quote |
| `\"` | Double quote |
| `\$` | Dollar sign |

### 2.5 Comments

```tern
// A single-line comment.

/*
    A multiline
    comment.
*/
```

Multiline comments do not nest.

### 2.6 Statement termination

A statement ends with `;` unless its last part is a code block.

```tern
int x = 10;
x += 5;
out ("${x}\n");
in (x);
```

A construct whose last part is a block — a `when` or `loop`, a function, structure, or enum declaration — takes no semicolon after its closing brace:

```tern
when x > 0 => {
    out ("positive\n");
}

struct Point { int x, y; }
```

A `when` arm whose body is a single statement ends with that statement's own `;`:

```tern
when {
    x > 0 => count++;
    _     => { out ("none\n"); }
}
```

Structure literals and `when` expressions are values, not code blocks, so the statement containing them still ends with a semicolon:

```tern
Point p = { x: 10, y: 20 };
int sign = when { x < 0 => -1; _ => 1; };
```

---

## 3. Grammar

The grammar uses EBNF notation: `{ x }` means zero or more, `[ x ]` means optional, and `|` separates alternatives. Lexical rules are in [§2](#2-lexical-structure).

### 3.1 Programs

```ebnf
program     = { import_stmt } { declaration } [ export_stmt ] ;
declaration = variable_decl | function_decl | struct_decl | enum_decl ;
```

Only declarations appear at the top level of a module; executable statements belong inside functions. A top-level `variable_decl` declares global variables. An export statement, if present, must be the last item in its module.

### 3.2 Types

```ebnf
type      = { "@" | "[" [ integer_lit ] "]" } base_type ;
base_type = "int" | "char" | "bool" | type_name [ type_args ] ;
type_name = identifier [ "." identifier ] ;
type_args = "[" type { "," type } "]" ;
```

Type prefixes read left to right:

```tern
int
[4]int        // an array of 4 ints
[]int         // a slice of ints
[3][4]int     // an array of 3 elements, each a [4]int
[]@int        // a slice of pointers to int
@[]int        // a pointer to a slice of ints
@[3]int       // a pointer to an array of 3 ints
Point
math.Point
@Point
Vec[Token]    // a generic structure with its type argument
```

- `[N]` is a fixed-size array of `N` elements; `N` must be a positive integer literal ([§5.2](#52-fixed-size-arrays)).
- `[]` is a slice ([§5.3](#53-slices)).
- In `[3][4]int`, `m[i][j]` takes `i < 3` and `j < 4`.
- `math.Point` names the structure `Point` exported by the imported module `math` ([§10.2](#102-modules)).
- `Vec[Token]` names the generic structure `Vec` with `T` set to `Token` ([§5.11](#511-generics)).

### 3.3 Variable declarations

```ebnf
variable_decl = decl_body ";" ;
decl_body     = [ "const" ] type declarator { "," declarator } ;
declarator    = identifier [ "=" expression ] ;
```

```tern
int x;
int y = 10;
int i = 0, j = 10;

const int MIN = 1, MAX = 100;

[3]int numbers = [1, 2, 3];
[]char name = "Alex";
[3][3]int matrix;
```

One declaration may declare several variables of the same type ([§6.3](#63-several-variables-in-one-declaration)).

### 3.4 Conditionals

```ebnf
when_stmt    = "when" ( "{" cond_arm { cond_arm } "}"
                      | expression "=>" arm_body
                      | expression "{" subject_arm { subject_arm } "}" ) ;
cond_arm     = ( expression | "_" ) "=>" arm_body ;
subject_arm  = ( patterns | "_" ) "=>" arm_body ;
patterns     = pattern { "," pattern } ;
pattern      = expression | identifier identifier ;   (* a value, or a variant and its binding *)
arm_body     = block | statement ;
```

`when` has three forms:

```tern
// Conditions, tested top to bottom
when {
    x > 100 => out ("Large\n");
    x > 50  => out ("Medium\n");
    _       => out ("Small\n");
}

// One condition
when x > 0 => count++;

// A subject, matched against each arm's patterns
when ch {
    'a', 'e', 'i', 'o', 'u' => vowels++;
    _                       => others++;
}
```

An arm's body is a block or a single statement other than a declaration. In the expression after `when`, a structure literal with a type name is not recognized, so `when p { ... }` always begins the arms of a subject; wrap such a literal in parentheses. Semantics are defined in [§7.1](#71-conditional-execution); the expression form is in [§8.7](#87-when-expressions).

### 3.5 Loops

A loop's optional label and its configuration in square brackets are followed by its body. The number of parts in the configuration decides the loop's form.

```ebnf
loop_stmt   = "loop" [ identifier ] "[" [ loop_config ] "]" block ;
loop_config = expression                                        (* condition *)
            | "int" identifier "=" expression ".." expression   (* range *)
            | [ loop_setup ] ";" [ expression ] ";" [ simple_list ] ;
loop_setup  = decl_body | simple_list ;
simple_list = simple_stmt { "," simple_stmt } ;
```

```tern
loop [] { ... }                                  // forever
loop [ x > 0 ] { ... }                           // while x > 0
loop [ int i = 0 .. 10 ] { ... }                 // i = 0, 1, ..., 9
loop [ int i = 0; i < 10; i++ ] { ... }          // setup; condition; step
loop [ int i = 0, j = 10; i < j; i++, j-- ] { ... }
loop rows [ int r = 0 .. 8 ] { ... }             // labeled
```

A configuration with a single part is a range if it has the form `int name = start .. end`, and a condition otherwise. A configuration with two parts is a compile-time error. `loop` is a statement and produces no value. Semantics are defined in [§7.2](#72-loops).

### 3.6 Functions

```ebnf
function_decl  = "fn" identifier [ type_params ] "(" [ parameter_list ] ")" [ "->" type ] block ;
type_params    = "[" identifier { "," identifier } "]" ;
parameter_list = parameter { "," parameter } ;
parameter      = type identifier ;
```

```tern
fn add(int a, int b) -> int {
    return a + b;
}

fn greet() {
    out ("Hello!\n");
}

fn first[T]([]T items) -> T {
    return items[0];
}
```

A function without `-> type` returns no value. Each parameter has its own type: `fn add(int a, b)` is a syntax error.

### 3.7 Structures

```ebnf
struct_decl = "struct" identifier [ type_params ] "{" { field_decl } "}" ;
field_decl  = decl_body ";" ;
```

```tern
struct Point {
    int x, y;
}

struct Vec[T] {
    []T items;
    int len;
}
```

A field's default value, if given, must be a constant expression ([§6.5](#65-global-variables)).

### 3.8 Enums

```ebnf
enum_decl = "enum" identifier "{" variant { [ "," ] variant } "}" ;
variant   = identifier [ "{" { field_decl } "}" ] ;
```

```tern
enum Color { Red, Green, Blue }

enum Expr {
    Num { int value; }
    Add { @Expr left, right; }
}
```

Variants are separated by commas; the comma may be left out after a variant with fields. Semantics are defined in [§5.12](#512-enums).

### 3.9 Imports

```ebnf
import_stmt = "import" identifier [ "(" identifier { "," identifier } ")" ] ";" ;
```

```tern
import math;
import math (square, cube);
```

`import math;` loads the file `math.tn` from the same directory as the importing file.

### 3.10 Exports

```ebnf
export_stmt = "export" "(" identifier { "," identifier } ")" ";" ;
```

```tern
export (square, cube);
```

### 3.11 Input and output

```ebnf
input_expr   = "in" [ "[" expression "]" ] "(" input_target { "," input_target } ")" ;
input_target = postfix | "_" ;

output_stmt  = "out" [ "[" expression [ ";" expression ] "]" ] "(" expression ")" ";" ;
```

The optional configuration in `[...]` names a file, followed for `out` by an optional overwrite flag. Then comes the data in parentheses: a list of destinations for `in`, and exactly one expression, the text to write, for `out`.

```tern
in (age, _, score);
in [ "data.txt" ] (age, score);

out ("Age: ${age}\n");
out [ "log.txt" ] ("Age: ${age}\n");
out [ "log.txt"; true ] ("Fresh log\n");   // true: empty the file first
```

`in` is an expression that evaluates to the number of destinations filled ([§10.5](#105-input)), so it can stand alone as a statement or appear in a condition:

```tern
loop [ in (x) == 1 ] {
    out ("Read ${x}\n");
}
```

Semantics are defined in [§10.5](#105-input) and [§10.6](#106-output).

### 3.12 Statements and blocks

```ebnf
block       = "{" { statement } "}" ;

statement   = variable_decl
            | simple_stmt ";"
            | when_stmt
            | loop_stmt
            | return_stmt
            | "break" [ identifier ] ";"
            | "continue" [ identifier ] ";"
            | "delete" unary ";"
            | output_stmt ;

simple_stmt = expression [ assign_op expression ]
            | postfix ( "++" | "--" ) ;
assign_op   = "=" | "+=" | "-=" | "*=" | "/=" | "%="
            | "&=" | "|=" | "^=" | "<<=" | ">>=" ;
return_stmt = "return" [ expression ] ";" ;
```

- Assignment is a statement, not an expression: it produces no value and cannot be nested in another expression. Its left side must be assignable: a variable, a field (`p.x`), an indexed element (`a[i]`), or a dereference (`@p`).
- A simple statement without an assignment or `++`/`--` must be a function call or an `in` expression; anything else, such as `x + 1;`, is a compile-time error.
- `x++` and `x--` are statements equivalent to `x += 1;` and `x -= 1;`.
- The operand of `delete` must be assignable ([§9.3](#93-deallocation)).
- A `when` at the start of a statement is a `when` statement; anywhere else it is an expression ([§8.7](#87-when-expressions)).

A statement that starts with a type followed by an identifier is a declaration. The parser reads a type and checks whether an identifier comes next, which tells `Point p = ...` (declaration) from `p = ...` (assignment), `@int p;` from `@p = 5;`, and `Vec[Token] t;` from `a[i] = x;`. A statement that starts with `[` is always a declaration.

### 3.13 Expressions

Each level below corresponds to one row of the precedence table in [§4](#4-operator-precedence).

```ebnf
expression     = logical_or ;
logical_or     = logical_and { "||" logical_and } ;
logical_and    = equality { "&&" equality } ;
equality       = relational { ( "==" | "!=" ) relational } ;
relational     = additive { ( "<" | "<=" | ">" | ">=" ) additive } ;
additive       = multiplicative { ( "+" | "-" | "|" | "^" ) multiplicative } ;
multiplicative = unary { ( "*" | "/" | "%" | "&" | "<<" | ">>" ) unary } ;
unary          = ( "@" | "&" | "!" | "-" | "~" ) unary | postfix ;
postfix        = primary { [ type_args ] "(" [ arguments ] ")"
                         | "[" index "]"
                         | "." identifier } ;
index          = expression | [ expression ] ".." [ expression ] ;
arguments      = expression { "," expression } ;

primary        = integer_lit | char_lit | string_lit
               | "true" | "false" | "null"
               | identifier
               | array_lit
               | struct_lit
               | new_expr
               | input_expr
               | when_expr
               | "(" expression ")" ;

array_lit      = "[" expression { "," expression } "]" ;
struct_lit     = [ type_name [ "." identifier ] ] struct_body ;
struct_body    = "{" [ field_init { "," field_init } ] "}" ;
field_init     = identifier ":" expression ;
new_expr       = "new" ( type_name [ type_args ] [ "." identifier ] struct_body
                       | "[" expression "]" type ) ;
when_expr      = "when" ( "{" { ( expression | "_" ) "=>" expression ";" } "}"
                        | expression "{" { ( patterns | "_" ) "=>" expression ";" } "}" ) ;
```

- `&` is address-of where an operand is expected, and bitwise AND after an operand. `-` likewise is negation or subtraction.
- A `[...]` directly followed by `(` after a function name holds explicit type arguments: `append[int](&v, 'a')`.
- A structure literal may leave out its type name only where the type is already known ([§6.8](#68-structure-initialization)). A literal of a generic structure always leaves its name out, except after `new`.
- `@p.x` parses as `@(p.x)`, because postfix operators bind tighter than prefix ones. Write `(@p).x` to dereference first.

---

## 4. Operator precedence

From highest to lowest:

| Level | Operators | Description | Associativity |
|---|---|---|---|
| 1 | `()` `[]` `.` | Call, index, sub-slice, member access | Left |
| 2 | `@` `&` `!` `-` `~` (unary) | Dereference, address-of, logical NOT, negation, bitwise NOT | Right |
| 3 | `*` `/` `%` `&` `<<` `>>` | Multiplication, division, remainder, bitwise AND, shifts | Left |
| 4 | `+` `-` `\|` `^` | Addition, subtraction, bitwise OR, bitwise XOR | Left |
| 5 | `<` `<=` `>` `>=` | Relational comparison | Left |
| 6 | `==` `!=` | Equality | Left |
| 7 | `&&` | Logical AND | Left |
| 8 | `\|\|` | Logical OR | Left |

Parentheses override precedence:

```tern
int result = (a + b) * c;
```

Because the bitwise operators bind tighter than comparisons, `flags & MASK == 0` means `(flags & MASK) == 0`.

Assignment, `++`, and `--` are not operators: they form statements of their own ([§3.12](#312-statements-and-blocks)). `..` is not an operator either: it appears only in a sub-slice ([§5.6](#56-sub-slices)) and a range loop ([§7.3](#73-range-loops)).

---

## 5. Types

### 5.1 Primitive types

| Type | Size | Values |
|---|---|---|
| `int` | 4 bytes | −2147483648 to 2147483647, two's complement |
| `char` | 1 byte | 0 to 255 |
| `bool` | 1 byte | `true` or `false` |

```tern
int  count   = 42;
char letter  = 'A';     // 65
bool enabled = true;
```

`char` is a number: it takes part in arithmetic and comparisons like an `int` ([§5.10](#510-conversions)). What sets it apart is that it holds text: strings are slices of `char`, and a `char` prints as its character ([§8.6](#86-string-interpolation)).

```tern
char next = letter + 1;  // 'B'
int  digit = '7' - '0';  // 7
```

`bool` is not a number. Wherever a condition is expected (`when` conditions, loop conditions, `!`, `&&`, `||`), the operand must be a `bool`; to test a number, compare it: `n != 0`.

### 5.2 Fixed-size arrays

`[N]T` holds exactly `N` elements of type `T`, stored in place: inside the variable, the structure, or the enclosing array. `N` is a positive integer literal.

```tern
[3]int    numbers = [1, 2, 3];
[3][3]int matrix;
```

Fixed-size arrays are values: assigning or passing one copies all its elements.

### 5.3 Slices

`[]T` is a slice: a pointer to a run of `T` elements plus its length. A slice does not own its elements; copying a slice copies the pointer and length, so both copies refer to the same elements.

A slice is obtained from:

- A string literal ([§5.4](#54-strings)).
- An array literal assigned or passed where a slice is expected. The literal's elements live until the end of the enclosing block, like a local variable.
- `new [n]T` ([§9.2](#92-dynamic-allocation)).
- A fixed-size array, which converts to a slice of its elements. The slice is valid only while the array exists.
- A sub-slice of an array or slice ([§5.6](#56-sub-slices)).

```tern
[]int  a = [1, 2, 3];
[4]int b;
[]int  c = b;        // c refers to b's elements
c[0] = 7;            // b[0] is now 7
```

The default slice, and `null` assigned to a slice, has a null pointer and length `0`.

### 5.4 Strings

Strings are slices of characters, type `[]char`. There is no separate string type and no terminator; `.len` gives the length.

```tern
[]char name = "Alex";  // name.len is 4
```

The elements of a string literal are read-only and shared by every evaluation of the literal. Writing to them is undefined ([§9.9](#99-undefined-behavior)); copy the text into a fixed-size array first.

### 5.5 Length

Every array and slice has a read-only member `len` of type `int`, the number of elements. For `[N]T` it is the constant `N`.

```tern
[5]int a;
[]char s = "hi";
// a.len is 5, s.len is 2
```

Indexing an array or slice outside `0 … len - 1` is a runtime error.

### 5.6 Sub-slices

`s[a .. b]` is a slice of the elements of `s` from index `a` up to, but not including, `b`. Leaving out `a` starts at `0`; leaving out `b` ends at `s.len`.

```tern
[]char text = "Hello, world";
[]char hello = text[.. 5];      // "Hello"
[]char world = text[7 ..];      // "world"
[]char ll    = text[2 .. 4];    // "ll"
```

`s` may be a slice or a fixed-size array; the result is always a slice, `[]T`. It shares its elements with `s`: no elements are copied, and writing through one is seen through the other. A sub-slice of an array is valid only while the array exists.

The bounds are checked at runtime: `a > b`, `a < 0`, or `b > s.len` is a runtime error. `s[a .. a]` is an empty slice.

### 5.7 Structures

Structures group named fields.

```tern
struct Student {
    const int id;
    []char name;
    int score;
}
```

Fields may be of any type except one that contains the structure itself by value ([§5.9](#59-recursive-types)). Structures are data-only: they have no methods, constructors, or inheritance.

### 5.8 Nominal typing

Two structure values are compatible only if they have the same declared structure type. The same holds for enums.

```tern
struct Point  { int x, y; }
struct Vector { int x, y; }

Point p = {};
Vector v = p; // Error: identical fields, different types
```

### 5.9 Recursive types

A structure or enum may not contain itself by value, directly or indirectly, including through a fixed-size array.

```tern
struct Node {
    Node next; // Error
}
```

Use a pointer to build recursive data structures:

```tern
struct Node {
    int data;
    @Node next;
}
```

### 5.10 Conversions

Tern has no cast syntax. These conversions are applied implicitly wherever a value of one type is used where the other is expected:

| From | To | Result |
|---|---|---|
| `char` | `int` | The same number |
| `int` | `char` | The low 8 bits |
| `[N]T` | `[]T` | A slice of the array's elements |
| `null` | Any pointer or slice type | A null pointer, or an empty slice |

Converting a constant `int` outside `0 … 255` to `char` is a compile-time error: `char c = 300;` is rejected, while a value computed at runtime is converted silently.

Every other use of a value where a different type is expected is a compile-time error. In particular:

- `bool` never converts to or from a number. Use a comparison (`n != 0`) or a `when` expression (`when { ok => 1; _ => 0; }`).
- Conversions apply to values, not to what they point to: `[]char` and `[]int` never convert to each other, nor `@char` and `@int`, nor `[3]char` and `[3]int`.
- A constant array never converts to a slice, because the slice would allow its elements to be written ([§6.2](#62-constants)).

```tern
int  n = 'A';         // 65
char c = n + 1;       // 'B'
char d = 300;         // Error: 300 does not fit in a char
bool b = n;           // Error: an int is not a bool
[]int s = "text";     // Error: a []char is not a []int
```

### 5.11 Generics

Structures and functions may take type parameters, written in square brackets after the name:

```tern
struct Vec[T] {
    []T items;
    int len;
}

fn append[T](@Vec[T] v, T x) {
    when v.len == v.items.len => {
        []T bigger = new [v.items.len * 2 + 4]T;
        loop [ int i = 0 .. v.len ] { bigger[i] = v.items[i]; }
        delete v.items;
        v.items = bigger;
    }
    v.items[v.len] = x;
    v.len++;
}
```

- In a type, the type arguments are always written: `Vec[int]`, `Vec[Vec[char]]`.
- At a call, the type arguments are inferred from the arguments' types. Inference matches types exactly, without the conversions of [§5.10](#510-conversions); if a type parameter would be inferred as two different types, or cannot be inferred, the call is a compile-time error. Type arguments may also be written explicitly before the arguments: `append[int](&v, 'a')`, where `'a'` then converts to `int`.
- Generics are monomorphized: each distinct set of type arguments produces a separate copy of the structure or function, type-checked with the arguments substituted. A type error in that copy is reported at the use that created it.
- Type parameters have no constraints: any type may be used, and an operation that is invalid for the type given is a compile-time error in that copy.
- A generic function cannot share its name with another function.

```tern
Vec[int] numbers;
append(&numbers, 42);       // T is int
append(&numbers, 'a');      // Error: T is int and char
append[int](&numbers, 'a'); // T is int; 'a' converts
```

### 5.12 Enums

An enum is a tagged union: a value is exactly one of the enum's variants, and a variant may carry fields of its own.

```tern
enum Color { Red, Green, Blue }

enum Expr {
    Num { int value; }
    Add { @Expr left, right; }
    Neg { @Expr operand; }
}
```

A variant is named through its enum with `.`. A variant with fields is built like a structure literal; one without fields is written by name alone:

```tern
Color c = Color.Red;
Expr  e = Expr.Num { value: 5 };
@Expr p = new Expr.Neg { operand: new Expr.Num { value: 1 } };
```

An enum exported from another module is named the same way: `ast.Expr.Num { value: 5 }`.

- The default value of an enum is its first variant, with that variant's fields at their defaults.
- Enums are values: assigning or passing one copies the variant and its fields.
- Enums cannot be compared with `==` or `!=`. The only way to inspect the variant, and the only way to read its fields, is a `when` with the enum as its subject ([§7.1](#71-conditional-execution)).
- Enums take no type parameters in this version.

### 5.13 Pointers

Pointer types are written with `@`. The address-of operator is `&`; the dereference operator is `@`.

```tern
@int p;
@Point node;

int x = 10;
@int q = &x;
@q = 20;
```

Pointers support equality comparison, arithmetic, and indexing ([§9.4](#94-pointer-arithmetic)).

---

## 6. Declarations

### 6.1 Mutable variables

Variables are mutable unless declared `const`.

```tern
int x = 10;
x = 20;
```

### 6.2 Constants

The `const` modifier prevents modification of the variable's whole storage: a constant fixed-size array's elements and a constant structure's fields cannot be assigned either. For a constant slice or pointer, the slice or pointer itself is fixed; the elements it refers to are not made read-only.

Constants, including constant structure fields, must be initialized explicitly. Taking the address of a constant, or of any part of one, and converting a constant array to a slice, are compile-time errors.

```tern
const int MAX = 100;
const int MIN;               // Error: missing initializer
@int p = &MAX;               // Error: address of a constant
const [3]int A = [1, 2, 3];
[]int s = A;                 // Error: a constant array cannot become a slice
```

### 6.3 Several variables in one declaration

A declaration may declare several variables, separated by commas. The type, and `const` if present, apply to every name; each name may have its own initializer.

```tern
int i = 0, j = 10;
int x, y;              // both 0
const int LOW = 1, HIGH = 9;
[3]int a, b;           // both [3]int
@int p, q;             // both pointers to int
```

Names are declared from left to right, and each is in scope from the next declarator on, so `int i = 0, j = i + 1;` is valid. This form is allowed for local and global variables, structure and variant fields, and a loop's setup; parameters are declared one per type.

### 6.4 Default initialization

All storage is zero-initialized unless explicitly initialized.

| Type | Default |
|---|---|
| `int` | `0` |
| `char` | `'\0'` |
| `bool` | `false` |
| Pointer | `null` |
| Slice | `null`, length `0` |
| Fixed-size array | Every element at its default |
| Structure | Every field at its declared default, or its type's default |
| Enum | The first variant, with its fields at their defaults |

### 6.5 Global variables

A global variable's initializer, like a structure field's default, must be a constant expression:

- A literal, or `null`.
- A unary `-` applied to an integer literal.
- An enum variant, or an array, structure, or variant literal built only from constant expressions.

Calls, variables, other operators, `when`, and `new` are not allowed.

```tern
int limit = 100;
int lowest = -2147483648;
[]char greeting = "Hello";
int bad = limit * 2;  // Error: initializer is not constant
```

### 6.6 Scope

Tern uses lexical block scoping: every executable `{}` block introduces a new scope.

```tern
int x = 10;

when x > 0 => {
    int y = 20;
}

// y is not accessible here.
```

### 6.7 Shadowing

An inner scope may shadow an outer variable. The inner name refers to a separate variable.

```tern
int x = 10;

when x > 0 => {
    int x = 20; // Shadows the outer x
}
```

### 6.8 Structure initialization

Structures are initialized by field name. Omitted mutable fields receive their default values; constant fields must be initialized explicitly.

```tern
Point p = Point { x: 10, y: 20 };
Point q = { x: 10, y: 20 };       // type name left out
```

The type name may be left out wherever the expected structure type is already known:

- The initializer of a declaration, and the right side of an assignment.
- A `return` value.
- A field value inside another structure literal, and an element of an array literal whose type is known.
- A function argument, provided the call matches exactly one overload ([§6.9](#69-function-overloading)).

Elsewhere, and after `new`, the name is required. A variant literal always names its variant: `Expr.Num { value: 5 }`.

### 6.9 Function overloading

Functions may share a name if their parameter lists differ in count or types. Return type alone cannot distinguish overloads.

```tern
fn show(int x) {
    out ("${x}\n");
}

fn show([]char x) {
    out (x);
}
```

A call selects an overload in two steps:

1. If exactly one overload's parameter types match the argument types exactly, it is chosen.
2. Otherwise, if exactly one overload matches once the conversions in [§5.10](#510-conversions) are allowed, it is chosen.

A structure literal without a type name matches any structure parameter in its position. If no overload matches, or more than one does at the step that decides, the call is a compile-time error. With `fn f(int)` and `fn f(char)`, `f('a')` calls `f(char)` and `f(5)` calls `f(int)`. `main` and generic functions cannot be overloaded.

### 6.10 Parameters

Arguments are passed by value: an `int`, `char`, `bool`, fixed-size array, structure, or enum is copied into the parameter. Passing a slice or pointer copies the slice or pointer, not the elements it refers to.

---

## 7. Statements and control flow

### 7.1 Conditional execution

`when` handles all conditional execution. It has three forms.

**Conditions.** Arms are tested from top to bottom, and only the first arm whose condition is true executes. The optional `_` arm matches unconditionally and must be the last arm. If no arm matches, nothing executes.

```tern
when {
    age >= 18 => out ("Adult\n");
    _         => out ("Minor\n");
}
```

**One condition.** `when condition => body` runs the body if the condition is true. It cannot have a `_` arm.

```tern
when x > 0 => count++;

when line.len == 0 => {
    blank++;
    continue;
}
```

**A subject.** `when subject { ... }` evaluates the subject once and runs the first arm whose patterns match it. The subject is an `int`, a `char`, or an enum.

For an `int` or `char` subject, each pattern is a constant expression of the subject's type, compared with `==`; an arm may list several, separated by commas.

```tern
when ch {
    'a', 'e', 'i', 'o', 'u' => vowels++;
    ' ', '\n'               => { }
    _                       => consonants++;
}
```

For an enum subject, each arm names variants by name alone (`Num`, not `Expr.Num`). A variant with fields may be followed by a binding name, which inside the arm is a copy of the variant's fields, accessed with `.`. An arm without a binding may list several variants, separated by commas.

```tern
when e {
    Num n => out ("${n.value}");
    Add a => { show(a.left); out (" + "); show(a.right); }
    _     => out ("?");
}
```

- An enum subject must name every variant or end with a `_` arm. Naming a variant twice is a compile-time error.
- A `_` arm must be the last arm.
- The subject may be written through a pointer: `when @p { ... }`.

### 7.2 Loops

`loop` handles all repetition. Its configuration has zero, one, or three parts:

| Configuration | Form | Runs |
|---|---|---|
| `[]` | Infinite | Until `break`, `return`, or a runtime error |
| `[ condition ]` | Conditional | While the condition is true |
| `[ int i = start .. end ]` | Range | Once for each `i` from `start` up to, but not including, `end` |
| `[ setup; condition; step ]` | Three-part | Setup once, then while the condition is true, running the step after each iteration |

```tern
loop [ x > 0 ] {
    x--;
}
```

### 7.3 Range loops

A range loop counts a new `int` variable upward by one:

```tern
loop [ int i = 0 .. 3 ] {
    out ("${i}\n");        // 0, 1, 2
}
```

`start` and `end` are each evaluated once, before the first iteration. If `end` is not greater than `start`, the body never runs. The loop is equivalent to the three-part loop `[ int i = start; i < end; i++ ]`, except that `end` is not re-evaluated.

### 7.4 Three-part loops

```tern
loop [ int i = 0; i < 10; i++ ] {
    out ("${i}\n");
}
```

Execution always proceeds in this order:

1. Run the setup.
2. Evaluate the condition; if false, the loop ends.
3. Run the body.
4. Run the step.
5. Repeat from step 2.

Any part may be left empty: an empty setup or step does nothing, and an empty condition is always true.

```tern
loop [ ; i < 10; i++ ] { ... }   // i was declared earlier
```

The setup is either one declaration, which may declare several variables, or a comma-separated list of simple statements. The step is a comma-separated list of simple statements, run left to right.

```tern
loop [ int i = 0, j = 10; i < j; i++, j-- ] {
    // i and j move toward each other.
}
```

Variables declared in the setup or by a range are visible in the condition, the step, and the body, but not after the loop.

### 7.5 Labeled loops

A loop may be given a label, written between `loop` and its configuration. `break` and `continue` followed by a label act on that loop instead of the nearest one.

```tern
loop rows [ int r = 0 .. grid.len ] {
    loop [ int c = 0 .. grid[r].len ] {
        when grid[r][c] == target => break rows;
        when grid[r][c] < 0 => continue rows;
    }
}
```

A label that is unknown, or that does not belong to a loop enclosing the `break` or `continue`, is a compile-time error. Labels have their own namespace: a label may share its name with a variable.

### 7.6 Break

`break` ends the nearest enclosing loop, or the labeled one, immediately. The step is skipped.

```tern
loop [] {
    break;
}
```

### 7.7 Continue

`continue` skips the rest of the current body of the nearest enclosing loop, or the labeled one. In a three-part or range loop, the step then runs before the condition is evaluated again.

```tern
loop [ int i = 0 .. 10 ] {
    when i == 5 => continue;
    out ("${i}\n");
}
```

### 7.8 Return

`return` exits a function with a value. A function without a return type may use `return;` to exit early.

```tern
fn square(int x) -> int {
    return x * x;
}

fn greet() {
    out ("Hello!\n");
    return;
}
```

In a function with a return type, every path must end in `return`; otherwise the function is a compile-time error.

- A `when` arm ends every path if its body is a `return`, or a block that ends every path.
- A `when` with conditions ends every path if it has a `_` arm and every arm ends every path.
- A `when` with a subject ends every path if every arm does and it covers every case: an enum subject names every variant or has a `_` arm, and an `int` or `char` subject has a `_` arm.
- A `when` with one condition never ends every path.

---

## 8. Expressions and evaluation order

### 8.1 Arithmetic

Tern supports `+`, `-`, `*`, `/`, and `%` on `int` and `char`. A `char` operand is converted to `int` first, so the result is always an `int`. Arithmetic wraps around on overflow (32-bit two's complement).

- Division truncates toward zero.
- The result of `%` has the sign of the left operand.
- Division or remainder by zero is a runtime error, as is dividing the smallest `int` by `-1`.

```tern
int a = 7 / 2;   // 3
int b = -7 / 2;  // -3
int c = -7 % 2;  // -1
```

Storing a result in a `char` keeps its low 8 bits ([§5.10](#510-conversions)), so `char` arithmetic wraps from `255` to `0`.

### 8.2 Bitwise operators

`&`, `|`, `^`, `<<`, `>>`, and unary `~` apply to `int` and `char`; like arithmetic, they convert a `char` operand to `int` and produce an `int`.

| Operator | Result |
|---|---|
| `a & b` | Bitwise AND |
| `a \| b` | Bitwise OR |
| `a ^ b` | Bitwise exclusive OR |
| `~a` | Every bit inverted |
| `a << n` | `a` shifted left by `n` bits; bits shifted out are lost |
| `a >> n` | `a` shifted right by `n` bits, copying the sign bit (an arithmetic shift) |

A shift count outside `0 … 31` is a runtime error.

```tern
int flags = 0x0F;
int low   = flags & 0x3;   // 3
int mask  = 1 << 4;        // 16
int neg   = -16 >> 2;      // -4
```

### 8.3 Logical operators

`&&`, `||`, and `!` apply to `bool` and produce a `bool`. `&&` and `||` short-circuit.

### 8.4 Comparisons

Comparisons produce a `bool`. An `int` and a `char` may be compared with each other; the `char` is converted to `int` first.

| Operand kind | Supported operators |
|---|---|
| `int`, `char` | `==` `!=` `<` `<=` `>` `>=` |
| `bool` | `==` `!=` |
| Pointer | `==` `!=` |
| Slice | `==` `!=`, only against `null` |
| Array, structure, enum | None |

`s == null` is true for a slice whose pointer is null, such as the default slice. To test whether a slice is empty, compare its length: `s.len == 0`.

### 8.5 Assignment

Assignment uses `=`. Values of type `int`, `char`, `bool`, fixed-size arrays, structures, and enums are copied:

```tern
Point a = { x: 10, y: 20 };
Point b = a;

b.x = 50; // a.x is still 10
```

Assigning a pointer or slice copies the address and length, so both refer to the same elements:

```tern
@Point p = new Point {};
@Point q = p;
```

Assigning to a fixed-size array requires a value of the same size: `[3]int a = [1, 2];` is a compile-time error.

The compound operators `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, and `>>=` apply to `int` and `char`. `+=` and `-=` also apply to pointers ([§9.4](#94-pointer-arithmetic)).

### 8.6 String interpolation

A string may embed values with `${expression}` or `${expression : format}`. Interpolation is allowed only in the string that is the whole operand of an `out` statement; the values are written in place, and no string is ever built in memory.

Without a format, a value is written according to its type:

| Type | Writes |
|---|---|
| `int` | The decimal integer |
| `char` | The character |
| `bool` | `true` or `false` |
| `[]char`, `[N]char` | The characters as text |

A format writes a value another way:

| Format | Applies to | Writes |
|---|---|---|
| `int` | `int`, `char` | The decimal integer |
| `char` | `int`, `char` | The character with the value's low 8 bits |
| `bool` | `int`, `char`, `bool` | `false` for zero or `false`, `true` otherwise |

```tern
int age = 20;
[]char name = "Alex";
char initial = 'A';

out ("Hello, ${name}! Age: ${age}. Initial: ${initial} (code ${initial : int})\n");
```

Other types (other arrays and slices, structures, enums, pointers) cannot be formatted. The expression inside `${...}` may not contain a string literal.

### 8.7 When expressions

A `when` that does not start a statement is an expression: it evaluates to the value of the arm it chooses.

```tern
int sign = when { x < 0 => -1; x > 0 => 1; _ => 0; };

[]char name = when color {
    Red   => "red";
    Green => "green";
    Blue  => "blue";
};

int value = when e {
    Num n => n.value;
    _     => 0;
};
```

- It takes the condition form or the subject form; the one-condition form is not an expression.
- Each arm is `pattern => expression;`. Arms have no blocks or statements.
- It must be exhaustive: the condition form ends with a `_` arm, an enum subject names every variant or ends with `_`, and an `int` or `char` subject ends with `_`.
- Every arm's expression has the same type, which is the type of the `when`.
- Only the chosen arm's expression is evaluated.
- A `when` expression is not allowed in a constant expression.

### 8.8 Evaluation order

Evaluation is strictly left to right:

- The operands of a binary operator, left before right (except where `&&` and `||` skip the right operand).
- Function arguments, first to last, then the call.
- In an assignment, the target's subexpressions (such as `i` in `a[i]`), then the right side.
- Declarators in a declaration, and statements in a loop's setup or step list, first to last.
- `in` destinations, first to last.
- In a sub-slice, the sliced value, then the start, then the end.

`when` conditions and patterns are evaluated top to bottom, and only the first matching arm executes.

---

## 9. Memory model

### 9.1 Automatic storage

Local variables, including fixed-size arrays and array literals, have automatic storage, zero-initialized unless explicitly initialized. That storage becomes invalid when its block ends, and any pointer or slice still referring to it dangles.

### 9.2 Dynamic allocation

`new` allocates zero-initialized storage on the heap. It is the only way a Tern program allocates: no other construct allocates behind the program's back.

```tern
@Point p       = new Point { x: 1 };
@Expr  e       = new Expr.Num { value: 1 };
[]int  numbers = new [10]int;
```

| Expression | Type | Storage |
|---|---|---|
| `new Point { ... }` | `@Point` | One structure, initialized like a structure literal |
| `new Expr.Num { ... }` | `@Expr` | One enum value, initialized like a variant literal |
| `new [n]T` | `[]T` | `n` elements, zeroed |

`n` is evaluated at runtime. `n == 0` gives an empty slice; a negative `n`, or running out of memory, is a runtime error.

### 9.3 Deallocation

`delete` releases storage obtained from `new` and sets its operand to `null` (for a slice: null pointer, length `0`). The operand must be assignable.

```tern
@Point p = new Point {};
delete p;
// p == null
```

Deleting `null` has no effect. A slice may be deleted through any sub-slice that starts at its first element. Deleting anything not obtained from `new`, deleting the same storage twice (for example through a copy), or deleting a pointer or slice that does not start at the beginning of an allocation, is undefined ([§9.9](#99-undefined-behavior)).

### 9.4 Pointer arithmetic

Pointers support addition and subtraction of `int` offsets, scaled by the size of the pointed-to type. Indexing is defined in terms of arithmetic:

```text
p[i] ≡ @(p + i)
```

Subtracting two pointers into the same allocation yields their distance in elements, as an `int`. Pointer arithmetic and indexing are not bounds-checked; to get a pointer to a slice's elements, write `&s[0]`.

### 9.5 Dereferencing

```tern
int x = 10;
@int p = &x;

@p = 20;
```

Dereferencing `null` is a runtime error.

### 9.6 Member access through a pointer

Member access with `.` looks through one pointer, for any member: if `p` is a `@Point`, `p.x` means `(@p).x`, and if `s` is a `@[]int`, `s.len` means `(@s).len`. Deeper pointers need explicit dereferences: for `@@Point pp`, write `(@pp).x`.

```tern
@Point p = new Point { x: 10, y: 20 };

p.x = 30;          // Same as (@p).x = 30;
```

Accessing a member through a `null` pointer is a runtime error.

### 9.7 Pointer copies

Copying a pointer copies its address. Deleting one copy does not reset the others, which are left dangling.

```tern
@Point a = new Point {};
@Point b = a;

delete a; // a is null; b is dangling
```

### 9.8 Value copies

Every value has a size known at compile time, so every copy is a plain copy of that many bytes. Copying an `int`, `char`, `bool`, fixed-size array, structure, or enum copies its contents; copying a pointer or slice (including one stored in a structure) copies only the pointer and length. An enum's size is that of its largest variant plus its tag.

### 9.9 Undefined behavior

The following are undefined: the program may crash, misbehave, or appear to work. Neither the compiler nor the runtime is required to detect them.

- Using storage after it has been deleted, or after its block has ended.
- Writing to the elements of a string literal or of a command-line argument.
- Pointer arithmetic that leaves its allocation, and accessing memory through such a pointer.
- Deleting storage not obtained from `new`, deleting it twice, or deleting through a pointer or slice that does not start at the beginning of an allocation.

---

## 10. Program entry and runtime

### 10.1 Entry point

Every executable program starts in `main`, declared in the file passed to the compiler. `main` either takes no parameters or takes the command-line arguments as a `[][]char`, and either returns no value or returns an `int`, which becomes the process's exit status. A `main` without a return type exits with status `0`.

```tern
fn main() {
    out ("Hello, world!\n");
}

fn main([][]char args) -> int {
    when args.len < 2 => {
        out ("usage: ${args[0]} <file>\n");
        return 1;
    }
    out ("Reading ${args[1]}\n");
    return 0;
}
```

`args[0]` is the name the program was started with, and the arguments follow in order. The arguments' text lives for the whole run; writing to it is undefined ([§9.9](#99-undefined-behavior)).

### 10.2 Modules

Each source file is a module; no module declaration is needed. A module is loaded once however many files import it. Exported members are accessed with qualified names, including structure and enum types.

```tern
import math;

int r = math.square(5);
math.Point p = { x: 1, y: 2 };
```

Import cycles, direct or indirect, are a compile-time error.

### 10.3 Selective imports

Exported names may also be imported directly and then used unqualified; their qualified names remain available. Import aliases are not supported, and conflicting imported names are a compile-time error.

```tern
import math (square, cube);

int result = square(5);
```

### 10.4 Exports

A module lists its exported names in an optional export statement at the end of the file. Functions, structures, enums, and global variables can be exported. Declarations that are not exported are private to the module. Exporting an overloaded name exports every overload with that name.

An exported function or global variable may not mention a structure or enum type that is not itself exported.

```tern
export (square, cube);
```

### 10.5 Input

`in` and `out` are built in and need no import.

`in` fills its destinations in order. Without configuration it reads standard input; `in [ path ]` reads the file at `path`, which must be text (`[]char` or `[N]char`). What is read depends on each destination's type:

| Destination type | What is stored |
|---|---|
| `int` | The next word, read as a decimal integer with an optional leading `-` |
| `[]char` | The next word's characters, written into the slice's existing elements; the slice's length is then set to the word's length |
| `char` | The next single character, whatever it is, including a space, tab, or newline |
| `_` | Nothing: the next word is read and discarded |

A word is a run of characters other than spaces, tabs, and newlines. Reading a word first skips any spaces, tabs, and newlines before it, and stops at the first one after it, which is left unread. Reading a `char` skips nothing.

```tern
int age;
[32]char buffer;
[]char name = buffer;

in (name, age);   // input "Alex 20": name is "Alex", age is 20
in [ "people.txt" ] (name, age);
```

Reading a file character by character reads all of it, whitespace included:

```tern
char c;
int lines = 0;
loop [ in [ path ] (c) == 1 ] {
    when c == '\n' => lines++;
}
```

`in` evaluates to the number of destinations filled, counting `_`. When input ends early, the remaining destinations are left unchanged and the count is lower than the number of destinations; at end of input it is `0`.

It is a runtime error if an `int` word is not a decimal integer or is out of range, or if a word is longer than its destination slice.

### 10.6 Output

`out` writes exactly one expression: text — a `[]char` or `[N]char`, or a string with interpolation ([§8.6](#86-string-interpolation)) — exactly as given. It adds no newline; write `\n` where a line should end.

```tern
out ("Hello, world!\n");
out (greeting);
out ("Name: ");                                // a prompt: no newline
out [ "log.txt" ] ("Hello, world!\n");         // appended to log.txt
out [ "log.txt"; true ] ("New contents\n");    // log.txt emptied first
```

Without configuration, `out` writes to standard output. `out [ path ]` appends to the file at `path`, which must be text. `out [ path; overwrite ]` takes a `bool` as a second part: if it is `true`, the file is emptied before this write; if `false`, the write appends as usual.

### 10.7 Files

The runtime keeps at most one open input stream and one open output stream per path for the whole run, and closes them when the program exits. Streams are buffered, so reading a file one character at a time is not slower than reading it in words.

- The first `in` from a path opens it; later `in` statements on the same path continue where the previous one stopped.
- The first `out` to a path opens it for appending, creating it if needed; later `out` statements continue writing to it. An overwrite flag that is `true` empties the file at that statement, and writing continues from there.
- Standard output is flushed before every read from standard input, so a prompt appears before the program waits.

A file that cannot be opened is a runtime error. Reading and writing the same path in one run is not supported in this version.

### 10.8 Runtime errors

A runtime error writes a message naming the error and its source location (file, line, and column) to standard error and ends the program with exit status `1`. Runtime errors are:

- Division or remainder by zero, and dividing the smallest `int` by `-1`.
- A shift count outside `0 … 31`.
- Dereferencing `null`, including member access through `null`.
- Indexing an array or slice out of bounds, and a sub-slice with bounds out of range or in the wrong order.
- `new` with a negative size, or running out of memory.
- Malformed or oversized input ([§10.5](#105-input)).
- A file that cannot be opened.

Everything in [§9.9](#99-undefined-behavior) is undefined rather than a runtime error.

---

## 11. Diagnostics

The compiler reports syntax errors, type errors, and invalid operations. Every diagnostic:

1. Identifies the error category.
2. Reports the source location.
3. Highlights the offending expression or declaration.
4. Adds explanatory notes where useful.

Exact wording is not part of the language's semantics. Representative examples:

| Situation | Source | Diagnostic |
|---|---|---|
| Syntax error | `int x = 10` | `error: expected ';' after declaration` |
| Type mismatch | `Vector v = p;` where `p` is a `Point` | `error: cannot assign 'Point' to 'Vector'` |
| Size mismatch | `[3]int a = [1, 2];` | `error: cannot assign '[2]int' to '[3]int'` |
| Constant out of range | `char c = 300;` | `error: 300 does not fit in 'char'`<br>`note: a char holds 0 to 255` |
| Condition not a bool | `when n => count++;` where `n` is an `int` | `error: condition is 'int', not 'bool'`<br>`note: compare it, as in 'n != 0'` |
| Invalid comparison | `a == b` where both are `[]int` | `error: comparison is not supported for slice types`<br>`note: compare lengths with '.len', or compare with 'null'` |
| Constant modification | `MAX = 200;` where `MAX` is `const` | `error: cannot assign to constant 'MAX'` |
| Loop configuration | `loop [ int i = 0; i < 10 ] { }` | `error: a loop configuration has 0, 1, or 3 parts, not 2` |
| Unknown label | `break outer;` outside a loop labeled `outer` | `error: no enclosing loop is labeled 'outer'` |
| Missing variant | `when e { Num n => ...; }` | `error: 'when' does not cover 'Expr.Add'`<br>`note: add an arm for it, or a '_' arm` |
| Missing return | `fn f() -> int { }` | `error: function 'f' does not return a value on every path` |
| Inference conflict | `append(&numbers, 'a')` where `numbers` is a `Vec[int]` | `error: 'T' is inferred as both 'int' and 'char'`<br>`note: write the type argument: 'append[int](...)'` |
| Recursive structure | `struct Node { Node next; }` | `error: recursive structure definition`<br>`note: use '@Node' to store a pointer instead` |

---

## 12. Example program

```tern
struct Student {
    const int id;
    []char name;
    int score;
}

fn grade(int score) -> char {
    return when {
        score >= 90 => 'A';
        score >= 75 => 'B';
        score >= 50 => 'C';
        _           => 'F';
    };
}

fn main() {
    Student student = {
        id: 1,
        name: "Alex",
        score: 85
    };

    out ("Student: ${student.name}\n");
    out ("Score: ${student.score}\n");
    out ("Grade: ${grade(student.score)}\n");

    [3]int squares;

    loop [ int i = 0 .. squares.len ] {
        squares[i] = i * i;
        out ("Square ${i}: ${squares[i]}\n");
    }
}
```

**Expected output**

```text
Student: Alex
Score: 85
Grade: B
Square 0: 0
Square 1: 1
Square 2: 4
```

---

## Appendix A. Not in this version

These are deliberately left out of version 0.1.

| Feature | Notes |
|---|---|
| Floating-point numbers | Not planned |
| Cast syntax | Not planned: the conversions in [§5.10](#510-conversions) are implicit, and `bool` converts through comparisons and `when` |
| Constraints on type parameters | Generic code is checked per use |
| Generic enums | Enums take no type parameters |
| Reading a whole file in one step | Read it a `char` at a time ([§10.5](#105-input)); `in` never allocates |
| `extern` and `defer` | Reserved keywords |
| Import aliases and nested module paths | Modules are files in the same directory |
| Non-ASCII identifiers | |
| Digit separators | Such as `1_000_000` |
| Array sizes from named constants | Sizes are integer literals |
| Counting down or by other steps in a range loop | Use a three-part loop |
| Empty array literals | `[]` with no elements |
| Interpolation outside `out` | |
| Reading and writing the same file in one run | |

---

## Appendix B. Syntax reference

| Construct | Syntax |
|---|---|
| Variable | `int x = 10;` |
| Several variables | `int i = 0, j = 10;` |
| Constant | `const int x = 10;` |
| Character and truth value | `char c = 'A';`, `bool ok = true;` |
| Fixed-size array | `[3]int a = [1, 2, 3];` |
| Slice | `[]char s = "Hi";` |
| Sub-slice | `s[1 .. 3]`, `s[1 ..]`, `s[.. 3]` |
| Length | `s.len` |
| Structure | `struct Point { int x, y; }` |
| Structure literal | `Point p = { x: 1, y: 2 };` |
| Generic structure | `struct Vec[T] { []T items; int len; }` |
| Enum | `enum Color { Red, Green, Blue }` |
| Variant | `Color.Red`, `Expr.Num { value: 5 }` |
| Function | `fn name() { ... }` |
| Function with return type | `fn name() -> int { ... }` |
| Generic function | `fn first[T]([]T items) -> T { ... }` |
| Conditional | `when { condition => { ... } _ => { ... } }` |
| One condition | `when x > 0 => count++;` |
| Subject | `when ch { 'a', 'e' => ...; _ => ...; }` |
| Enum subject | `when e { Num n => ...; _ => ...; }` |
| Conditional expression | `int sign = when { x < 0 => -1; _ => 1; };` |
| Infinite loop | `loop [] { ... }` |
| Conditional loop | `loop [ x > 0 ] { ... }` |
| Range loop | `loop [ int i = 0 .. 10 ] { ... }` |
| Three-part loop | `loop [ int i = 0, j = 9; i < j; i++, j-- ] { ... }` |
| Labeled loop | `loop outer [ ... ] { ... break outer; }` |
| Input | `in (x);` |
| Input with count | `int n = in (x, y);` |
| Input from file | `in [ "data.txt" ] (x);` |
| Output | `out ("x is ${x}\n");` |
| Output to file | `out [ "log.txt" ] ("Hello\n");` |
| Overwrite a file | `out [ "log.txt"; true ] ("Hello\n");` |
| Command-line arguments | `fn main([][]char args) -> int { ... }` |
| Pointer | `@int p = &x;` |
| Dereference | `@p` |
| Field through pointer | `p.x` |
| Allocation | `new Point {}`, `new [n]int` |
| Deallocation | `delete p;` |
| Import | `import math;` |
| Selective import | `import math (square);` |
| Export | `export (square);` |
