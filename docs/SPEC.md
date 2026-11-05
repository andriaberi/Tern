# Tern Language Specification — Core

**Version:** 0.1.0-core · **Status:** Draft · **File extension:** `.tn`

Tern is a small systems language designed to be implemented, including in itself. It has:

- Three primitive types: `int` (32-bit signed), `char` (8-bit, 0 to 255), and `bool`.
- Fixed-size arrays, slices, structures, and tagged unions (enums) with pattern matching.
- A conditional, `when`, usable as a statement or an expression, and one loop statement, `loop`.
- Explicit pointers, including pointer arithmetic, and manual memory management with no hidden allocation.
- File-based modules.
- Built-in input and output (standard input, standard output, standard error, and files), and command-line arguments.

Tern has no floating-point numbers, casts, overloading, or generics.

## Contents

1. [Overview](#1-overview)
2. [Lexical structure](#2-lexical-structure)
3. [Grammar](#3-grammar)
4. [Operator precedence](#4-operator-precedence)
5. [Types](#5-types)
6. [Declarations and scope](#6-declarations-and-scope)
7. [Statements and control flow](#7-statements-and-control-flow)
8. [Expressions](#8-expressions)
9. [Memory](#9-memory)
10. [Programs, modules, and I/O](#10-programs-modules-and-io)
11. [Runtime errors and undefined behavior](#11-runtime-errors-and-undefined-behavior)
12. [Diagnostics](#12-diagnostics)
13. [Example program](#13-example-program)
- [Appendix A. Not in this version](#appendix-a-not-in-this-version)
- [Appendix B. Syntax reference](#appendix-b-syntax-reference)

---

## 1. Overview

| Syntax | Purpose | Example |
|---|---|---|
| `()` | Parameters, arguments, `in`/`out`/`err` data, export lists; grouping | `add(5, 10)`, `out ("Hi\n")`, `(a + b) * c` |
| `[]` | Array and slice types, array literals, indexing, configuration | `[4]int`, `[1, 2, 3]`, `a[0]`, `loop [i < 10]` |
| `{}` | Blocks, structure and enum bodies, structure literals, `when` arms | `struct Point { int x, y; }`, `Point { x: 1 }` |
| `=>` | Separates a `when` pattern from its body | `x > 0 => count++;` |
| `->` | A function's return type | `fn add(int a, int b) -> int { ... }` |
| `;` | Ends statements; separates configuration parts | `int x = 10;`, `loop [int i = 0; i < 10; i++]` |
| `,` | Separates items in a list | `int i = 0, j = 10;`, `add(1, 2);` |
| `..` | A range of indexes or loop values | `s[1 .. 3]`, `loop [int i = 0 .. 10]` |

Square brackets directly after `loop` (or its label), `in`, or `out` hold that construct's **configuration**. They are never array literals or indexing. Inside a configuration, `;` separates parts and `,` separates items within a part.

Program execution begins in `main`.

---

## 2. Lexical structure

### 2.1 Source files

Source files use the `.tn` extension and are UTF-8. Identifiers are ASCII; other characters may appear only in comments and string literals.

### 2.2 Identifiers

```ebnf
identifier = ( letter | "_" ) { letter | digit | "_" } ;
letter     = "a" … "z" | "A" … "Z" ;
digit      = "0" … "9" ;
```

Identifiers are case-sensitive. A lone `_` is not an identifier but a separate token: it marks the default arm of a `when` and a skipped destination of `in`.

### 2.3 Keywords

```text
int       char       bool
const     struct     enum
fn        return
when      loop
break     continue
import    export
new       delete
in        out        err
true      false      null
```

`extern` and `defer` are reserved and cannot be used as identifiers.

### 2.4 Literals

```ebnf
integer_lit = digit { digit } | "0x" hex_digit { hex_digit } ;
hex_digit   = digit | "a" … "f" | "A" … "F" ;
char_lit    = "'" ( char | escape ) "'" ;
string_lit  = "\"" { char | escape | interpolation } "\"" ;
escape      = "\\" ( "n" | "t" | "r" | "0" | "\\" | "'" | "\"" | "$" | "x" hex_digit hex_digit ) ;
```

| Kind | Examples | Type |
|---|---|---|
| Integer | `0`, `42`, `0xFF` | `int` |
| Character | `'A'`, `'\n'`, `'\xFF'` | `char` |
| Boolean | `true`, `false` | `bool` |
| Null | `null` | Any pointer or slice ([§5.11](#511-conversions)) |
| String | `"Hello"`, `"Hi\n"` | `[]char` |

- A decimal literal must not exceed `2147483647`. The one exception is `2147483648`, which may appear directly after a unary `-` and then denotes `-2147483648`.
- A hexadecimal literal may be up to `0xFFFFFFFF` and denotes the `int` with that 32-bit pattern: `0xFFFFFFFF` is `-1`.
- In a character literal, `char` is one printable ASCII character (codes 32 to 126) other than `'` and `\`. The literal's value is the character's code, or the escape's value; `'\xFF'` is the byte `FF`.
- In a string literal, `char` is any source character other than a newline, `\`, or `"`. The string holds one element per byte of its UTF-8 encoding and has no terminator.
- In a string, `$` begins an interpolation ([§10.5](#105-output)); a `$` not followed by `{` is an ordinary character, and `\$` is always a literal `$`.

| Escape | Value |
|---|---|
| `\n`, `\t`, `\r`, `\0` | Newline, tab, carriage return, zero |
| `\\`, `\'`, `\"`, `\$` | Backslash, single quote, double quote, dollar sign |
| `\xHH` | The byte with hexadecimal value `HH` |

### 2.5 Comments

`//` starts a comment that runs to the end of the line. `/*` starts one that runs to the next `*/`; these do not nest.

### 2.6 Statement termination

A statement ends with `;` unless its last part is a block: a block statement, a `loop`, a `when` with its arms in braces, or a one-condition `when` whose body is a block. A one-condition `when` whose body is a single statement ends with that statement's `;`.

- Function, structure, and enum declarations end with their closing brace and take no `;`.

```tern
when x > 0 => count++;
when x > 0 => {
    count++;
}
```

Structure literals and `when` expressions are expressions, so the statement containing them still ends with `;`:

```tern
Point p = Point { x: 10, y: 20 };
int sign = when { x < 0 => -1; _ => 1; };
```

---

## 3. Grammar

EBNF: `{ x }` is zero or more, `[ x ]` is optional, `|` separates alternatives.

### 3.1 Programs and declarations

```ebnf
program       = { import_decl } { declaration } [ export_decl ] ;
declaration   = variable_decl | function_decl | struct_decl | enum_decl ;

import_decl   = "import" identifier ";" ;
export_decl   = "export" "(" identifier { "," identifier } ")" ";" ;

variable_decl = decl_body ";" ;
decl_body     = [ "const" ] type declarator { "," declarator } ;
declarator    = identifier [ "=" expression ] ;

function_decl = "fn" identifier "(" [ param { "," param } ] ")" [ "->" type ] block ;
param         = type identifier ;
struct_decl   = "struct" identifier "{" { field_decl } "}" ;
enum_decl     = "enum" identifier "{" variant { "," variant } "}" ;
variant       = identifier [ "{" { field_decl } "}" ] ;
field_decl    = type declarator { "," declarator } ";" ;
```

- A variant without fields must be followed by a comma unless it is the last variant. Any other comma after a variant is optional.
- Each parameter has its own type: `fn add(int a, b)` is a syntax error.

### 3.2 Types

```ebnf
type      = { "@" | "[" [ integer_lit ] "]" } base_type ;
base_type = "int" | "char" | "bool" | identifier [ "." identifier ] ;
```

Prefixes read left to right: `[4]int` is an array of four ints, `[]@Node` a slice of pointers to `Node`, `@[]char` a pointer to a slice of chars. In `[]N`, `N` is a positive integer literal. `m.Point` names the structure `Point` exported by the imported module `m`.

### 3.3 Statements

```ebnf
block          = "{" { statement } "}" ;

statement      = variable_decl
               | simple_stmt ";"
               | block
               | when_stmt
               | loop_stmt
               | "return" [ expression ] ";"
               | "break" [ identifier ] ";"
               | "continue" [ identifier ] ";"
               | "delete" expression ";"
               | out_stmt
               | err_stmt ;

simple_stmt    = expression [ assign_op expression | "++" | "--" ] ;
simple_list    = simple_stmt { "," simple_stmt } ;
assign_op      = "=" | "+=" | "-=" | "*=" | "/=" | "%=" 
               | "&=" | "|=" | "^=" | "<<=" | ">>=" ;

when_stmt      = "when" ( "{" cond_arm { cond_arm } "}"
               | expression "=>" statement
               | expression "{" subject_arm { subject_arm } "}" ) ;
cond_arm       = ( expression | "_" ) "=>" statement ;
subject_arm    = ( pattern { "," pattern } | "_" ) "=>" statement ;
pattern        = [ "-" ] ( integer_lit | char_lit ) | identifier [ identifier ] ;

loop_stmt      = "loop" [ identifier ] "[" [ loop_config ] "]" block ;
loop_config    = expression                         (* condition *)
               | "int" identifier "=" expression ".." expression   (* range *)
               | [ loop_setup ] ";" [ expression ] ";" [ simple_list ] ;
loop_setup     = decl_body | simple_list ;

out_stmt       = "out" [ "[" expression [ ";" expression ] "]" ] "(" expression ")" ";" ;
err_stmt       = "err" "(" expression ")" ";" ;
```

### 3.4 Expressions

Each level is one row of the table in [§4](#4-operator-precedence).

```ebnf
expression     = logical_or ;
logical_or     = logical_and { "||" logical_and } ;
logical_and    = equality { "&&" equality } ;
equality       = relational { ( "==" | "!=" ) relational } ;
relational     = additive { ( "<" | "<=" | ">" | ">=" ) additive } ;
additive       = multiplicative { ( "+" | "-" | "|" | "^" ) multiplicative } ;
multiplicative = unary { ( "*" | "/" | "%" | "&" | "<<" | ">>" ) unary } ;
unary          = ( "@" | "&" | "-" | "!" | "~" ) unary | postfix ;
postfix        = primary { "(" [ expression { "," expression } ] ")"
                       | "[" index "]"
                       | "." identifier } ;
index          = expression | [ expression ] ".." [ expression ] ;

primary        = integer_lit | char_lit | string_lit
               | "true" | "false" | "null"
               | identifier
               | array_lit | struct_lit | new_expr | in_expr | when_expr
               | "(" expression ")" ;

array_lit      = "[" expression { "," expression } "]" ;
qualified      = identifier [ "." identifier [ "." identifier ] ] ;
struct_lit     = qualified struct_body ;
struct_body    = "{" [ field_init { "," field_init } ] "}" ;
field_init     = identifier ":" expression ;
new_expr       = "new" ( "[" expression "]" type | qualified [ struct_body ] ) ;
in_expr        = "in" [ "[" expression "]" ] "(" in_target { "," in_target } ")" ;
in_target      = expression | "_" ;

when_expr      = "when" ( "{" value_arm { value_arm } "}"
               | expression "{" subject_value_arm { subject_value_arm } "}" ) ;
value_arm      = ( expression | "_" ) "=>" expression ";" ;
subject_value_arm = ( pattern { "," pattern } | "_" ) "=>" expression ";" ;
```

### 3.5 Parsing rules

The grammar is decided by tokens alone, using these rules:

1. **Declarations.** A statement is a declaration if it begins with `const`, `int`, `char`, `bool`, or `[`; or with a type name followed by an identifier; or with one or more `@` followed by either of those. A type name is `identifier` or `identifier . identifier`. So `Point p;`, `m.Point p;`, and `@@Node n;` are declarations, while `p = q;` and `@p = 5;` are not. The same test decides whether a three-part loop's setup is a declaration.
2. **`when` statements and expressions.** A `when` at the start of a statement is a `when` statement; anywhere else it is a `when` expression.
3. **Structure literals.** Where a primary begins with an identifier, the parser reads up to three dot-separated identifiers. If the next token is `{`, they are the `qualified` name of a structure literal; otherwise the dots are member accesses. The exception is the expression directly after `when`, where a `{` that is not inside parentheses or square brackets ends the expression and begins the arms: write `when (E.V { ... }) { ... }` to use a literal there.
4. **Loop configurations.** The parser reads the first part of the configuration. If `..` follows, the loop is a range; the first part must then be `int name = start`. If `;` follows, the loop is three-part, and the configuration must contain exactly two `;` at its top level. If `]` follows, the first part is a condition and must be an expression. A configuration with exactly one top-level `;` (two parts) is a compile-time error.
5. **Prefix and postfix.** Postfix operators bind tighter than prefix ones: `@p.x` is `@(p.x)` and `-a[i]` is `-(a[i])`. `&` and `*` are unary where an operand is expected and binary after one.
6. **Simple statements.** A simple statement without an assignment, `++`, or `--` must be a call or an `in` expression; `x + 1;` is a compile-time error.
7. **Arm bodies.** The statement after `=>` in a `when` statement may not be a declaration.
8. **`_` in `in`.** `_` is accepted as an `in_target`, and nowhere else in an expression.

---

## 4. Operator precedence

From highest to lowest:

| Level | Operators | Description | Associativity |
|---|---|---|---|
| 1 | `()` `[]` `.` | Call, index, sub-slice, member access | Left |
| 2 | `@` `&` `!` `~` `-` | Dereference, address-of, NOT, negation, bitwise NOT | Right |
| 3 | `*` `/` `%` `&` `<<` `>>` | Multiplication, division, remainder, AND, shifts | Left |
| 4 | `+` `-` `\|` `^` | Addition, subtraction, OR, XOR | Left |
| 5 | `<` `<=` `>` `>=` | Relational | Left |
| 6 | `==` `!=` | Equality | Left |
| 7 | `&&` | Logical AND | Left |
| 8 | `\|\|` | Logical OR | Left |

Because bitwise operators bind tighter than comparisons, `flags & MASK == 0` means `(flags & MASK) == 0`. Assignment, `++`, and `--` are statements, not operators, and `..` appears only in sub-slices and range loops.

---

## 5. Types

### 5.1 Primitive types

| Type | Size | Values |
|---|---|---|
| `int` | 4 bytes | -2147483648 to 2147483647, two's complement |
| `char` | 1 byte | 0 to 255 |
| `bool` | 1 byte | `true`, `false` |

`char` is a number: it takes part in arithmetic and comparisons, converted to `int` first. It prints as its character, and strings are slices of it. `bool` is not a number: conditions, `!`, `&&`, and `||` require a `bool`. To test a number, compare it: `n != 0`.

### 5.2 Fixed-size arrays

`[N]T` holds exactly `N` elements of type `T`, stored in place. Arrays are values: assigning or passing one copies all its elements. Assigning an array requires the same element type and size.

**Array literals.** `[e1, …, en]` has at least one element.

- If it has an expected type ([§5.11](#511-conversions)) of `[N]T` or `[]T`, each element is converted to `T` as in an assignment; for `[N]T`, `N` must equal `n`. The literal takes its type from that context, so `[3]char abc = [97, 98, 99];` is valid.
- Otherwise its type is `[n]T`, where `T` is the elements' common type ([§5.11](#511-conversions)).

### 5.3 Slices

`[]T` is a pointer to a run of `T` elements plus a length. A slice does not own its elements; copying a slice copies the pointer and length. A slice is obtained from:

- A string literal ([§5.4](#54-strings)).
- An array literal whose expected type is a slice ([§9.1](#91-automatic-storage)).
- `new [n]T` ([§9.2](#92-dynamic-allocation)).
- A fixed-size array, by conversion. The slice is valid only while the array exists.
- A sub-slice ([§5.6](#56-sub-slices)).

The default slice has a null pointer and length `0`.

### 5.4 Strings

Strings are `[]char`. There is no terminator; `.len` gives the length. The elements of a string literal are read-only and shared by every evaluation of it; writing to them is undefined ([§11.2](#112-undefined-behavior)).

### 5.5 Length and indexing

Every array and slice has a read-only `int` member `.len`; for `[N]T` it is `N`. `a[i]` is the element at index `i`, which must be in `0 .. len - 1` (a runtime error otherwise). Indexing a pointer is described in [§5.10](#510-pointers).

### 5.6 Sub-slices

`s[a .. b]` is the slice of `s` from index `a` up to, but not including, `b`. Without `a`, it starts at `0`; without `b`, it ends at `s.len`. `s` is an array, a slice, or a pointer to one of those ([§5.10](#510-pointers)), and the result is a `[]T` sharing its elements. `a < 0`, `b > s.len`, or `a > b` is a runtime error. Sub-slicing a constant array is a compile-time error ([§6.2](#62-constants)).

### 5.7 Structures

```tern
struct Student {
    int id;
    []char name;
    int score = 50;
}
```

- Field names are distinct. A field may have any type that does not contain the structure itself by value ([§5.9](#59-recursive-types)).
- A field's default, if given, is a constant expression ([§6.4](#64-global-variables)).
- Structures are data only, and nominally typed: two structure types with identical fields are still different types.

A structure literal names its type and initializes fields by name; each must be a field of that type and may appear at most once. Omitted fields take their defaults:

```tern
Student s = Student { id: 1, name: "Alex" };  // score is 50
```

### 5.8 Enums

An enum is a tagged union: a value is exactly one of its variants, and a variant may carry fields.

```tern
enum Color { Red, Green, Blue }

enum Expr {
    Num { int value; },
    Add { @Expr left, right; },
    Neg { @Expr operand; },
}
```

- An enum has at least one variant. Variant names within an enum are distinct, as are field names within a variant.
- A variant without fields is written `Color.Red`. A variant with fields is built like a structure literal: `Expr.Num { value: 5 }`, where omitted fields take their defaults. From another module: `m.Expr.Num { value: 5 }`.
- The default enum value is its first variant, with that variant's fields at their defaults.
- Enums are values: assigning or passing one copies the variant and its fields. Its size is that of its largest variant plus a tag.
- Enums cannot be compared. A `when` with the enum as its subject ([§7.4](#74-when-with-a-subject), [§8.5](#85-when-expressions)) is the only way to find the variant and read its fields.

### 5.9 Recursive types

A structure or enum may not contain itself by value, directly or indirectly, including through a fixed-size array. Use a pointer or a slice instead:

```tern
struct Node {
    int data;
    @Node next;
}
```

### 5.10 Pointers

`@T` is a pointer to `T`. `&x` takes the address of an assignable, non-constant `x` ([§7.1](#71-assignment)), and `@p` dereferences `p`.

**Looking through a pointer.** Member access, indexing, and sub-slicing look through one pointer:

- If `p` is a `@Point`, `p.x` means `(@p).x`. If `s` is a `@[]T`, `s.len` means `(@s).len`.
- If `p` points to an array or slice, `p[i]` means `(@p)[i]` and `p[a .. b]` means `(@p)[a .. b]`, with bounds checks.
- Deeper pointers need explicit dereferences: `(@p).x`.

**Pointer arithmetic.** For a pointer `p` of type `@T` and an `int` or `char` `n`:

- `p + n` and `p - n`, with the pointer on the left, are `@T` values moved by `n` elements of `T`.
- If `q` is also a `@T`, `p - q` is their distance in elements, an `int`.
- If `p` does not point to an array or slice, `p[i]` means `@(p + i)`. This is not bounds-checked.
- A pointer obtained from `&a[i]`, where `a` is an array or slice, may move anywhere within the whole run of elements that the element belongs to (the array, the `new` allocation, the array literal's storage, the string literal, or the command-line argument), or to one past its last element. Any other pointer may move only to one past its object. Leaving that range, or doing arithmetic on `null`, is undefined ([§11.2](#112-undefined-behavior)), as is dereferencing a pointer one past the end. `p - q` requires both pointers to be in the same range.

**Comparison.** Pointers support `==` and `!=` only, against a pointer of the same type or `null`. Dereferencing `null`, including member access through it, is a runtime error.

### 5.11 Conversions

Tern has no cast syntax. A value is converted when it is **assigned**:

- as a declaration's initializer, or the right side of an assignment;
- as a function argument, or a `return` value;
- as a field value in a structure or variant literal;
- as an element of an array literal, or as an arm of a `when` expression, that itself has an expected type.

The type it is assigned to is its **expected type**. These conversions apply:

| From | To | Result |
|---|---|---|
| `char` | `int` | The same number |
| `int` | `char` | The low 8 bits |
| `[N]T` | `[]T` | A slice of the array's elements |
| `null` | Any pointer or slice | A null pointer, or a null slice |

- An integer literal, optionally negated, outside `0 .. 255` converted to `char` is a compile-time error: `char c = 300;` and `char d = -1;` are rejected. Other `int` values convert silently.
- A constant array never converts to a slice.
- Conversions apply to **values**, not to what they refer to: `[]char` and `[]int`, `@char` and `@int`, and `[3]char` and `[3]int` never convert to each other. (An array *literal* is not converted; it is typed by its context, [§5.2](#52-fixed-size-arrays).)
- `bool` never converts to or from a number.
- Any other use of a value where a different type is expected is a compile-time error.

**Common type.** The elements of an array literal, and the arms of a `when` expression, that have no expected type must have a **common type**:

- their type, if they all have the same one;
- `int`, if each is an `int` or a `char`;
- `T`, if each is `null` or of one pointer or slice type `T`, and at least one is not `null`.

Anything else is a compile-time error.

**`null`.** `null` may appear only where it has an expected type that is a pointer or slice; as an operand of `==` or `!=` whose other operand is a pointer or slice; or among expressions whose common type is a pointer or slice.

---

## 6. Declarations and scope

### 6.1 Variables

Variables are mutable unless declared `const`, and are zero-initialized unless given an initializer. A declaration may declare several variables of one type, separated by commas; the type, and `const` if present, apply to each, and each may have its own initializer:

```tern
int x;
int i = 0, j = i + 1;
[3]int numbers = [1, 2, 3];
[]char name = "Alex";
@int p, q;          // both pointers to int
```

Declarators are processed left to right, and each name is in scope from the next declarator on. This form is allowed for local and global variables, structure and variant fields, and a loop's setup. Parameters are declared one per type.

### 6.2 Constants

A `const` variable must have an initializer, and none of its storage can be modified: not its fields, and not its elements if it is a fixed-size array. For a constant slice or pointer, the slice or pointer itself is fixed; the elements it refers to are not.

Taking the address of a constant or of any part of one, converting a constant array to a slice, and sub-slicing a constant array are compile-time errors.

### 6.3 Default values

| Type | Default |
|---|---|
| `int`, `char` | `0` |
| `bool` | `false` |
| Pointer, slice | `null` (a slice has length `0`) |
| Fixed-size array | Every element at its default |
| Structure | Every field at its declared default, or its type's default |
| Enum | The first variant, with its fields at their defaults |

### 6.4 Global variables

A top-level variable declaration declares globals, which live for the whole run. Their initializers, like field defaults, must be **constant expressions**:

- An integer, character, string, or boolean literal; `null`; or a unary `-` applied to an integer literal.
- A variant without fields, such as `Color.Red`.
- A structure, variant, or array literal built only from constant expressions. An array literal here must initialize a fixed-size array, not a slice.

Calls, variables, other operators, `when` expressions, `in`, and `new` are not constant expressions.

### 6.5 Scope and names

- **Top-level names.** In each module, the names of functions, globals, structures, enums, and imported modules are distinct. They are visible throughout the module, regardless of the order of declarations.
- **Locals.** A local variable is visible from the end of its declarator to the end of its block. Parameters belong to the function body's outermost block. Variables declared in a loop's configuration are described in [§7.5](#75-loops).
- **Shadowing.** A local may shadow a name from an enclosing block, a parameter (in a nested block), or a top-level name, but not the name of an imported module. Declaring the same name twice in one block is a compile-time error.
- **Other namespaces.** Field names belong to their structure or variant, variant names to their enum, and loop labels have a namespace of their own.

### 6.6 Functions

```tern
fn add(int a, int b) -> int {
    return a + b;
}
```

- Function names are distinct within a module; there is no overloading.
- A call must pass exactly as many arguments as there are parameters. Each argument is assigned to its parameter as in [§5.11](#511-conversions), so values are copied: a slice or pointer is copied, not what it refers to.
- A function without a return type may be called only as a statement.
- Recursion, including mutual recursion, is allowed.

---

## 7. Statements and control flow

### 7.1 Assignment

The left side of an assignment, `++`, `--`, `&`, `in`, or `delete` must be **assignable**: a variable, a field (`p.x`), an element (`a[i]`), or a dereference (`@p`), and not part of a constant's own storage. The elements a constant slice or pointer refers to are not part of it, so they may be assigned ([§6.2](#62-constants)). `.len` is never assignable.

- `=` assigns as in [§5.11](#511-conversions).
- `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, and `>>=` require an `int` or `char` target. `+=` and `-=` also accept a pointer target with an `int` or `char` right side ([§5.10](#510-pointers)). `a op= b` computes `a op b` and assigns the result back.
- `x++` and `x--` mean `x += 1` and `x -= 1`, and so apply to `int`, `char`, and pointers.

### 7.2 `when` with conditions

```tern
when {
    x > 100 -> out ("large\n");
    x > 50  -> out ("medium\n");
    _       -> out ("small\n");
}
```

Each condition is a `bool`. Arms are tested from top to bottom, and only the first arm whose condition is true runs. The optional `_` arm matches always and must be last. If no arm matches, nothing runs.

### 7.3 `when` with one condition

`when condition -> body` runs the body if the `bool` condition is true. It has no `_` arm.

```tern
when x > 0 => count++;

when line.len == 0 => {
    blank++;
    continue;
}
```

### 7.4 `when` with a subject

`when subject { ... }` evaluates the subject once and runs the first arm with a matching pattern. The subject is an `int`, a `char`, or an enum.

**`int` and `char` subjects.** Each pattern is an integer or character literal, optionally preceded by `-`, and matches if it equals the subject. An arm may list several patterns, separated by commas.

- For a `char` subject, a pattern outside `0 .. 255` is a compile-time error.
- A value may not appear twice in one `when`, in the same arm or in different arms. `'A'` and `65` are the same value.

```tern
when ch {
    'a', 'e', 'i', 'o', 'u' -> vowels++;
    ' ', '\n'           -> { }
    _                   -> others++;
}
```

**Enum subjects.** Each pattern is the name of one of the subject's variants, written alone (`Num`, not `Expr.Num`).

- An arm with a single variant that has fields may add a binding name. The binding is a new variable scoped to the arm, holding a copy of the variant's fields, accessed with `.`. Changing it does not change the subject. Its type has no name, so the binding is used only through its fields; it cannot be assigned, passed, or its address taken as a whole.
- An arm that lists several variants, or names a variant without fields, has no binding.
- Each variant may be named at most once. The arms must name every variant or end with a `_` arm, and a `_` arm after arms that already name every variant is a compile-time error.

```tern
when e {
    Num n   -> out ("${n.value}");
    Add a   -> { show(a.left); out (" + "); show(a.right); }
    Neg n   -> { out ("-"); show(n.operand); }
}
```

In both forms, `_` must be the last arm.

### 7.5 Loops

| Configuration | Runs |
|---|---|
| `[]` | Until `break`, `return`, or a runtime error |
| `[ condition ]` | While the `bool` condition is true, tested before each iteration |
| `[ int i = start .. end ]` | Once for each `i` from `start` up to, but not including, `end` |
| `[ setup; condition; step ]` | Setup once, then while the condition is true, running the step after each iteration |

**Range loops.** `start` and `end` are `int` or `char` expressions, each evaluated once, before the first iteration. If `end <= start`, the body does not run. The variable `i` is new, visible only in the body, and constant: it cannot be assigned.

**Three-part loops.** Execution proceeds in this order:

1. Run the setup.
2. Evaluate the condition, a `bool`; if it is false, the loop ends.
3. Run the body.
4. Run the step.
5. Repeat from step 2.

- Any part may be empty: an empty setup or step does nothing, and an empty condition is always true.
- The setup is either one declaration, which may declare several variables, or a comma-separated list of simple statements. The step is a comma-separated list of simple statements, run left to right.
- Variables declared in the setup are visible in the condition, the step, and the body, but not after the loop.

```tern
loop [int i = 0, j = 10; i < j; i++, j--] {
    out ("${i} ${j}\n");
}
```

### 7.6 Labels, `break`, and `continue`

A loop may have a label between `loop` and its configuration. `break` ends the nearest enclosing loop immediately, skipping any step. `continue` skips the rest of the body: a range loop moves to its next value, and a three-part loop runs its step before testing the condition again. With a label, `break` and `continue` act on the enclosing loop with that label instead.

```tern
loop rows [int r = 0 .. grid.len] {
    loop [int c = 0 .. grid[r].len] {
        when grid[r][c] == target -> break rows;
        when grid[r][c] < 0 -> continue rows;
    }
}
```

`break` or `continue` outside a loop, or with a label that no enclosing loop has, is a compile-time error. A loop's label must differ from the labels of the loops that enclose it.

### 7.7 Return and termination

In a function without a return type, `return` takes no value, and reaching the end of the body returns. In a function with one, `return` takes a value, assigned to the return type as in [§5.11](#511-conversions).

A statement **terminates** if it is:

- a `return`;
- a block whose last statement terminates;
- a `when` with conditions that has a `_` arm, where every arm's body terminates;
- a `when` with a subject where every arm's body terminates, and that names every variant or has a `_` arm (an enum subject), or has a `_` arm (an `int` or `char` subject);
- a `loop` with no condition (`[]`, or a three-part loop with an empty condition) and no `break` that targets it.

A one-condition `when` never terminates. The body of a function with a return type must terminate; otherwise it is a compile-time error. A statement that directly follows, in the same block, a statement that terminates or a `break` or `continue` is unreachable, and is a compile-time error.

---

## 8. Expressions

### 8.1 Arithmetic

`+`, `-`, `*`, `/`, and `%` apply to `int` and `char`; a `char` operand is converted to `int`, and the result is an `int`. Arithmetic wraps on overflow (32-bit two's complement): negating `-2147483648` gives `-2147483648`. `+` and `-` with a pointer operand are pointer arithmetic ([§5.10](#510-pointers)).

- Division truncates toward zero, and `%` has the sign of its left operand: `-7 / 2` is `-3` and `-7 % 2` is `-1`.
- Division or remainder by zero is a runtime error, as is `-2147483648 / -1`; `-2147483648 % -1` is `0`.

### 8.2 Bitwise operators

`&`, `|`, `^`, `<<`, `>>`, and unary `~` apply to `int` and `char`, converting a `char` to `int` and producing an `int`. `>>` is an arithmetic shift that copies the sign bit, and `<<` discards bits shifted out. A shift count outside `0 .. 31` is a runtime error.

### 8.3 Logical operators

`&&`, `||`, and `!` take and produce `bool`. `&&` and `||` evaluate their right operand only when needed.

### 8.4 Comparisons

| Operands | Operators |
|---|---|
| `int` and `char`, in any mix | `==` `!=` `<` `<=` `>` `>=` |
| `bool` | `==` `!=` |
| Pointers of the same type, or a pointer and `null` | `==` `!=` |
| A slice and `null` | `==` `!=` |

Arrays, structures, and enums cannot be compared. `s == null` is true when the slice's pointer is null. To test whether a slice is empty, use `s.len == 0`.

### 8.5 `when` expressions

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
- Each arm is `pattern => expression;`, with patterns, bindings, and `_` as in [§7.2](#72-when-with-conditions) and [§7.4](#74-when-with-a-subject). A binding is scoped to its arm's expression.
- It must be exhaustive: the condition form ends with a `_` arm, an enum subject names every variant or ends with `_`, and an `int` or `char` subject ends with `_`.
- If the `when` has an expected type, each arm's expression is assigned to it ([§5.11](#511-conversions)), and that is the type of the `when`. Otherwise its type is the common type of its arms.
- Only the chosen arm's expression is evaluated.

### 8.6 Evaluation order

Evaluation is left to right:

- **Operators.** The left operand of a binary operator before the right (unless `&&` or `||` skips it).
- **Calls.** Arguments first to last, then the call.
- **Indexing.** The indexed value, then the index. In a sub-slice: the value, then the start, then the end.
- **Literals.** Array literal elements first to last; structure and variant literal fields in the order written.
- **Assignment.** The target's subexpressions are evaluated and checked (bounds, null), then the right side, then the store. In a compound assignment, `++`, or `--`, the target's subexpressions are evaluated once, then the target is read, then the right side is evaluated, the operation applied, and the result stored.
- **Declarations and lists.** Declarators in a declaration, and statements in a loop's setup or step list, first to last.
- **`when`.** The subject once, then patterns or conditions from top to bottom until one matches.
- **Range loops.** The start, then the end.
- **`in`, `out`, and `err`.** As described in [§10.4](#104-input) and [§10.5](#105-output).

---

## 9. Memory

### 9.1 Automatic storage

Local variables have automatic storage that becomes invalid when their block ends. An array literal whose expected type is a slice gets new storage each time it is evaluated, which lives until the end of the enclosing block (for an array literal in a loop's configuration, until the loop ends), like a local variable. Its elements are writable. A pointer or slice that outlives the storage it refers to dangles.

### 9.2 Dynamic allocation

`new` allocates zero-initialized heap storage. It is the only construct that allocates.

| Expression | Type | Allocates |
|---|---|---|
| `new Point { x: 1 }` | `@Point` | One structure, initialized like the literal |
| `new Color.Red`, `new Expr.Num { value: 1 }` | `@Color`, `@Expr` | One enum value, initialized like the variant literal |
| `new [n]T` | `[]T` | `n` zeroed elements of `T` |

- After `new`, a qualified name naming a structure requires a body (write `{}` for all defaults). A variant with fields requires one, and a variant without fields may not have one.
- In `new [n]T`, `n` is an `int` evaluated at runtime. `n == 0` gives a null slice and allocates nothing. A negative `n` or running out of memory is a runtime error.

### 9.3 Deallocation

`delete x;` releases storage obtained from `new` and sets `x` to `null`. `x` must be assignable and be a pointer or slice.

- Storage from `new` of a structure or variant is deleted through a pointer equal to the one `new` returned.
- Storage from `new [n]T` is deleted through a slice whose pointer is the allocation's first element, of any length. A pointer to an element, such as `&s[0]`, cannot delete it.
- Deleting `null`, or a null slice, has no effect.
- Any other `delete` is undefined ([§11.2](#112-undefined-behavior)). This includes deleting the same storage twice, for example through a copy: deleting one copy does not reset the others.

### 9.4 Copies

Every value has a size known at compile time, and every copy is a plain copy of that many bytes. Copying an `int`, `char`, `bool`, array, structure, or enum copies its contents; copying a pointer or slice, including one inside a structure, copies only the pointer (and length).

---

## 10. Programs, modules, and I/O

### 10.1 Entry point

Execution starts in `main`, declared in the file passed to the compiler. `main` takes either no parameters or a single `[][]char`, the command-line arguments, and returns either nothing (exit status `0`) or an `int`, which becomes the exit status. Only statuses `0` to `255` are portable; the operating system decides what others become.

```tern
fn main([][]char args) -> int {
    when args.len < 2 => {
        err ("usage: ${args[0]} <file>\n");
        return 1;
    }
    out ("reading ${args[1]}\n");
    return 0;
}
```

`args[0]` is the name the program was started with. The arguments' text lives for the whole run, and writing to it is undefined.

### 10.2 Modules

Each source file is a module. `import m;` loads `m.tn` from the directory of the importing file, so a module's file name must be an identifier. A module is loaded once, however many files import it.

- An imported module's exported names are used only through the module name: `m.f(x)`, `m.count`, `m.Point`, `m.Expr.Num { ... }`.
- Names are not imported transitively: `m.n.f` is invalid.
- Importing the same module twice in one file is a compile-time error, as is an import cycle, direct or indirect.
- An exported global variable is the same variable in every module that uses it.
- Only the entry file's `main` is the entry point. In any other module, `main` is an ordinary function.

### 10.3 Exports

`export (a, b, ...);` is optional, must be the last item in its module, and lists top-level functions, globals, structures, and enums to export. Everything else is private to the module. An exported declaration may not mention a structure or enum type that is not exported: not in a function's parameters or return type, a global's type, or an exported type's fields.

### 10.4 Input

```tern
int n = in (a, b);          // standard input
in [ path ] (c);           // the file at path
```

`in` is an expression of type `int`. Without configuration it reads standard input; `in [ path ]` reads the file at `path`, which is a `[]char` or `[N]char`. Each destination is assignable and is an `int` or a `char`, or it is `_`.

| Destination | Reads |
|---|---|
| `int` | The next word, as a decimal integer with an optional leading `-` |
| `char` | The next byte, whatever it is, including whitespace |
| `_` | The next word, discarded |

- A **word** is a run of bytes other than spaces, tabs, carriage returns, and newlines. Reading one first skips those bytes, then reads up to the next one, which is left unread. Reading a `char` skips nothing.
- The configuration is evaluated first. Then each destination's subexpressions are evaluated just before that destination is filled, after the previous one has been filled, so `in (a, a[i])` uses the new `i` if `i` was read first.
- `in` evaluates to the number of destinations filled, counting `_`. If the input ends first, the remaining destinations are neither evaluated nor changed. At end of input the result is `0`.
- An `int` word that is not a decimal integer, or is out of range, is a runtime error.

```tern
char c;
int lines = 0;
loop [in [path] (c) == 1] {
    when c == '\n' => lines++;
}
```

### 10.5 Output

```tern
out ("Hello, ${name}!\n");      // standard output
err ("error: ${msg}\n");        // standard error
out [ "log.txt" ] (line);        // appended to log.txt
out [ "out.c"; true ] ("// start\n"); // out.c emptied first
```

`out` and `err` write one piece of text exactly as given, with no added newline. The text is a `[]char` or `[N]char` expression, or a string literal with interpolations.

- **`out` configuration.** Without one, `out` writes to standard output. `out [ path ]` appends to the file at `path`, a `[]char` or `[N]char`. `out [ path; flag ]` takes a `bool`; if it is `true`, the file is emptied before this write.
- **`err`** writes to standard error and takes no configuration.
- **Interpolation.** `${expression}` is allowed only in a string literal that is the whole text of an `out` or `err`. The expression may not contain a string literal or a `{` or `}` token, so `when` expressions and structure literals cannot be interpolated directly; assign them to a variable first. The interpolation ends at the first `}` outside a character literal.
- **Formatting.** An interpolated value is written by its type: an `int` as a decimal number, a `char` as its byte, a `bool` as `true` or `false`, and a `[]char` or `[N]char` as its text. Other types cannot be interpolated. To print a character's code, convert it to `int`: `${c + 0}`.
- **Order.** The configuration is evaluated first (the path, then the flag). Then the text is written piece by piece from left to right, each interpolation evaluated just before it is written.

### 10.6 Files and streams

- The runtime keeps at most one input stream and one output stream per path, opened on first use, and flushed and closed when the program ends, whether `main` returns or a runtime error occurs. Streams are buffered, so reading one byte at a time is cheap.
- Later `in` statements on a path continue where the previous one stopped, and later `out` statements continue writing. An overwrite flag of `true` empties the file at that statement, and writing continues from there.
- Standard error is unbuffered. Standard output is flushed before every read from standard input and every write to standard error, including runtime error messages, so output appears in program order on a terminal.
- Paths are used as given, relative to the working directory, and compared byte for byte.
- A file that cannot be opened is a runtime error. So is reading a path that `out` has already written in this run, or writing a path that `in` has already read.

---

## 11. Runtime errors and undefined behavior

### 11.1 Runtime errors

A runtime error writes a message naming the error and its source location (file, line, and column) to standard error and ends the program with exit status `1`. Runtime errors are:

- Division or remainder by zero, and `-2147483648 / -1`.
- A shift count outside `0 .. 31`.
- Dereferencing `null`, including member access through it.
- An index out of bounds on an array or slice, and a sub-slice with bounds out of range or in the wrong order.
- `new [n]T` with a negative `n`, and running out of memory.
- An `int` input word that is malformed or out of range.
- A file that cannot be opened, and reading and writing the same path in one run.

### 11.2 Undefined behavior

The program may crash, misbehave, or appear to work. Neither the compiler nor the runtime has to detect these:

- Using storage after it has been deleted, or after its block has ended.
- Writing to the elements of a string literal or a command-line argument.
- Pointer arithmetic on `null` or outside the range allowed by [§5.10](#510-pointers), dereferencing a pointer one past the end, and subtracting pointers from different ranges.
- A `delete` not allowed by [§9.3](#93-deallocation).
- Exceeding the available stack space, such as through unbounded recursion.
- Reading and writing one file through two different spellings of its path.

---

## 12. Diagnostics

Each compile-time error reports its category and source location and highlights the offending code, with notes where useful. Exact wording is not part of the language. Examples:

| Situation | Source | Diagnostic |
|---|---|---|
| Syntax error | `int x = 10` | `error: expected ';' after declaration` |
| Type mismatch | `Vector v = p;` where `p` is a `Point` | `error: cannot assign 'Point' to 'Vector'` |
| Size mismatch | `[3]int a = [1, 2];` | `error: cannot assign '[2]int' to '[3]int'` |
| Constant out of range | `char c = 300;` | `error: 300 does not fit in 'char'` |
| Condition not a bool | `when n => count++;` with `n` an `int` | `error: condition is 'int', not 'bool'` / `note: compare it, as in 'n != 0'` |
| Constant modification | `MAX = 200;` | `error: cannot assign to constant 'MAX'` |
| Loop configuration | `loop [int i = 0; i < 10]` | `error: loop configuration has 0, 1, or 3 parts, not 2` |
| Unknown label | `break outer;` | `error: no enclosing loop is labeled 'outer'` |
| Missing variant | `when e { Num n => ...; }` | `error: 'when' does not cover 'Expr.Add'` |
| Non-exhaustive expression | `int s = when { x < 0 => -1; }` | `error: 'when' expression needs a '_' arm` |
| No common type | `when { a => p; _ => 0; }` with `p` a `@int` | `error: arms have types '@int' and 'int'` |
| Duplicate pattern | `'A', 65 => ...` | `error: value 65 is already matched` |
| Missing return | `fn f() -> int {}` | `error: function 'f' does not return a value on every path` |
| Unreachable code | `return 1; x++;` | `error: unreachable statement` |
| Recursive structure | `struct Node { Node next; }` | `error: recursive structure definition` / `note: use '@Node' instead` |

---

## 13. Example program

```tern
enum Token {
    Num { int value; },
    Plus,
    Minus,
    End,
}

struct Lexer {
    []char src;
    int pos;
}

fn is_digit(char c) -> bool {
    return c >= '0' && c <= '9';
}

fn next(@Lexer lx) -> Token {
    loop [lx.pos < lx.src.len && lx.src[lx.pos] == ' '] {
        lx.pos++;
    }
    when lx.pos == lx.src.len => return Token.End;

    char c = lx.src[lx.pos];
    lx.pos++;
    when c {
        '+' => return Token.Plus;
        '-' => return Token.Minus;
    }
    when !is_digit(c) => {
        err ("unexpected '${c}'\n");
        return Token.End;
    }

    int value = c - '0';
    loop [; lx.pos < lx.src.len && is_digit(lx.src[lx.pos]); lx.pos++] {
        value = value * 10 + (lx.src[lx.pos] - '0');
    }
    return Token.Num { value: value };
}

fn eval([]char src) -> int {
    Lexer lx = Lexer { src: src };
    int total = 0, sign = 1;
    loop [] {
        Token t = next(&lx);
        when t {
            Num n => total += sign * n.value;
            Plus  => sign = 1;
            Minus => sign = -1;
            End   => return total;
        }
    }
}

fn main() {
    []char expr = "12 + 30 - 2";
    int result = eval(expr);
    []char kind = when { result < 0 => "negative"; _ => "non-negative"; };
    out ("${expr} = ${result} (${kind})\n");
}
```

**Expected output**

```text
12 + 30 - 2 = 40 (non-negative)
```

---

## Appendix A. Not in this version

| Feature | Instead |
|---|---|
| Floating-point numbers, cast syntax | Implicit `char`/`int` conversions; compare to get a `bool` |
| Overloading | Distinct names: `emit_int`, `emit_text` |
| Generics | Write each container type, or use linked lists |
| Structure literals without a type name | Always write the type: `Point { ... }` |
| Constant structure fields | Declare the whole variable `const` |
| Selective imports, import aliases, nested module paths | Qualified names: `m.f` |
| Reading words into `[]char` | Read a `char` at a time |
| Interpolation formats, interpolation outside `out` and `err` | `${c + 0}` for a character's code |
| Counting down or by other steps in a range loop | A three-part loop |
| Named constants as array sizes or `when` patterns | Literals |
| Empty array literals, digit separators | — |
| `extern`, `defer` | Reserved keywords |

---

## Appendix B. Syntax reference

| Construct | Syntax |
|---|---|
| Variable, constant | `int x = 10;`, `const int MAX = 100;` |
| Several variables | `int i = 0, j = 10;` |
| Array, slice | `[3]int a = [1, 2, 3];`, `[]char s = "Hi";` |
| Sub-slice, length | `s[1 .. 3]`, `s[1 ..]`, `s[.. 3]`, `s.len` |
| Structure | `struct Point { int x, y; }` |
| Structure literal | `Point p = Point { x: 1, y: 2 };` |
| Enum, variant | `enum Color { Red, Green }`, `Color.Red`, `Expr.Num { value: 5 }` |
| Function | `fn name(int a) -> int { ... }` |
| Conditions | `when { a => ...; _ => ...; }` |
| One condition | `when x > 0 => count++;` |
| Subject | `when ch { 'a', 'e' => ...; _ => ...; }` |
| Enum subject | `when e { Num n => ...; _ => ...; }` |
| Conditional expression | `int sign = when { x < 0 => -1; _ => 1; };` |
| Loops | `loop [] { }`, `loop [x > 0] { }`, `loop [int i = 0 .. 10] { }` |
| Three-part loop | `loop [int i = 0; i < 9; i++] { }` |
| Labeled loop | `loop outer [] { ... break outer; }` |
| Pointer | `@int p = &x;`, `@p = 5;`, `p.x` |
| Pointer arithmetic | `p + 1`, `p - 1`, `p - q` |
| Allocation | `new Point {}`, `new Color.Red`, `new [n]int` |
| Deallocation | `delete p;` |
| Input | `in (x);`, `int n = in [path] (c);` |
| Output | `out ("x is ${x}\n");`, `out [path; true] (text);` |
| Standard error | `err ("error: ${msg}\n");` |
| Arguments | `fn main([][]char args) -> int { ... }` |
| Modules | `import m;`, `m.f(x)`, `export (f, Point);` |