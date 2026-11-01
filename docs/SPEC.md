# Tern Language Specification

**Version** 0.0.1 · **Status** Draft · **File extension** `.tn`

Tern is a general-purpose programming language built around minimal syntax, predictable behavior, and explicit control over program execution and memory.

- A universal primitive type, `val`.
- Homogeneous arrays and data-only structures.
- A unified conditional construct, `when`, and a unified loop construct, `loop`.
- Functions with overloading.
- Explicit pointers and memory management.
- File-based modules.
- Built-in input and output constructs.

Tern does not support floating-point numbers.

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
- [Appendix A. Outstanding details](#appendix-a-outstanding-details)
- [Appendix B. Syntax reference](#appendix-b-syntax-reference)

---

## 1. Overview

Tern follows a small set of syntactic conventions:

| Syntax | Purpose | Example |
|---|---|---|
| `()` | Parameters, arguments, and grouping | `add(5, 10)`, `(a + b) * c` |
| `[]` | Arrays, indexing, and keyword configuration | `[1, 2, 3]`, `numbers[0]`, `loop [ ... ]` |
| `{}` | Executable blocks, structures, `when` arms, and name lists | `struct Point { ... }`, `import math { square };` |
| `=>` | Introduces an executable block | `fn main() => { ... }` |
| `->` | Specifies a function's return type | `fn add(val a, val b) -> val` |
| `;` | Terminates simple statements | `val x = 10;` |

Square brackets directly after `loop`, `in`, or `out` hold that construct's configuration; they are never array literals or indexing. Configuration always comes before the construct's body or data.

```tern
loop [
    init: val i = 0;
    cond: i < 10;
    step: i++;
] => {
    out "${i : int}";
}
```

Program execution begins in `main`.

---

## 2. Lexical structure

### 2.1 Source files

Tern source files use the `.tn` extension and are encoded in UTF-8. The rules for non-ASCII Unicode characters in identifiers are not yet specified.

### 2.2 Identifiers

Identifiers are case-sensitive.

```ebnf
identifier = ( letter | "_" ) { letter | digit | "_" } ;
```

```tern
val age;
val totalScore;
val[] studentNames;
```

### 2.3 Keywords

```text
val       const     struct
fn        return
when      loop
init      cond      step
break     continue
import    export
new       delete
in        out
true      false     null
```

The underscore `_` marks the default arm of a `when` and a skipped destination in `in`.

The clause names `file` and `overwrite`, and the format names `int`, `char`, and `bool`, are **contextual words**: they have special meaning only inside an `in [...]` or `out [...]` configuration or a `${...}` interpolation, and are ordinary identifiers everywhere else.

### 2.4 Literals

| Kind | Examples | Notes |
|---|---|---|
| Integer | `0`, `42`, `100` | Negative numbers use unary negation: `-10` |
| Character | `'A'`, `'7'`, `'\n'`, `'\0'` | |
| Boolean | `true`, `false` | |
| Null pointer | `null` | |
| String | `"Hello, world!"` | A character array, not a separate primitive type |

```ebnf
integer_lit = digit { digit } ;
char_lit    = "'" ( char | escape ) "'" ;
string_lit  = '"' { char | escape | interpolation } '"' ;
escape      = "\" ( "n" | "t" | "r" | "0" | "\" | "'" | '"' | "$" ) ;
```

`char` is any source character other than a newline, a backslash, or the literal's own quote. In a string, `${` always begins an interpolation ([§8.5](#85-string-interpolation)); write `\$` for a literal dollar sign.

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

### 2.6 Statement termination

Simple statements end with a semicolon.

```tern
val x = 10;
x += 5;
```

A construct that ends in an executable block `{}` — `when`, `loop`, and function declarations — never takes a semicolon after its closing brace, even when its value is assigned or returned:

```tern
val result = when {
    x > 0;
}

return loop [ cond: x > 0; ] => {
    x--;
}
```

Structure initializers are data, not executable blocks, so the statement containing them still ends with a semicolon:

```tern
Point p = Point { x: 10, y: 20 };
```

Because a closing `}` ends the statement, a `when` or `loop` cannot be followed by more of an expression. To use one inside a larger expression, wrap it in parentheses; the statement then ends with `;` as usual:

```tern
val next = (when { x > 0; }) + 1;
```

---

## 3. Grammar

The grammar uses EBNF notation: `{ x }` means zero or more, `[ x ]` means optional, and `|` separates alternatives. Lexical rules are in [§2](#2-lexical-structure).

### 3.1 Programs

```ebnf
program     = { import_stmt } { declaration } [ export_stmt ] ;
declaration = variable_decl | function_decl | struct_decl ;
```

Only declarations appear at the top level of a module; executable statements belong inside functions. A top-level `variable_decl` declares a global variable. An export statement, if present, must be the last item in its module.

### 3.2 Types

```ebnf
type      = { "@" } base_type { "[]" } ;
base_type = "val" | identifier ;
```

```tern
val
val[]
val[][]
Point
@val
@Point
```

`@` binds to the base type before any `[]`, so `@val[]` is an array of pointers to `val`, and `@@val` is a pointer to a pointer to `val`. A dynamically allocated array is referred to by a pointer to its first element ([§9.4](#94-pointer-arithmetic)).

### 3.3 Variable declarations

```ebnf
variable_decl = [ "const" ] type identifier ( ";" | "=" rhs ) ;
rhs           = block_expr | expression ";" ;
block_expr    = when_expr | loop_expr ;
```

`rhs` encodes the termination rule from [§2.6](#26-statement-termination): an initializer that is a `when` or `loop` ends at its closing `}`; any other initializer ends with `;`.

```tern
val x;
val y = 10;

const val MAX = 100;

val[] numbers = [1, 2, 3];
val[][] matrix;
```

### 3.4 Conditional expressions

```ebnf
when_expr = "when" "{" { when_arm } "}" ;
when_arm  = ( expression | "_" ) ( "=>" block | ";" ) ;
```

```tern
val result = when {
    x > 100 => {
        out "Large";
    }
    x > 50 => {
        out "Medium";
    }
    _ => {
        out "Small";
    }
}
```

Semantics are defined in [§7.1](#71-conditional-execution) and [§7.2](#72-conditional-result-values).

### 3.5 Loop expressions

Loops use square brackets for configuration and curly braces for the body.

```ebnf
loop_expr   = "loop" "[" { loop_clause } "]" "=>" block ;
loop_clause = "init" ":" ( statement | block )
            | "cond" ":" expression ";"
            | "step" ":" ( statement | block ) ;
```

```tern
val iterations = loop [
    init: val i = 0;
    cond: i < 10;
    step: i++;
] => {
    out "${i : int}";
}
```

Every clause is optional and may appear at most once. Clause order does not affect execution order. Semantics are defined in [§7.3](#73-loops).

### 3.6 Functions

```ebnf
function_decl  = "fn" identifier "(" [ parameter_list ] ")" [ "->" type ] "=>" block ;
parameter_list = parameter { "," parameter } ;
parameter      = type identifier ;
```

```tern
fn add(val a, val b) -> val => {
    return a + b;
}

fn greet() => {
    out "Hello!";
}
```

A function without `-> type` returns no value.

### 3.7 Structures

```ebnf
struct_decl = "struct" identifier "{" { field_decl } "}" ;
field_decl  = [ "const" ] type identifier [ "=" expression ] ";" ;
```

```tern
struct Point {
    val x;
    val y;
}
```

### 3.8 Imports

```ebnf
import_stmt = "import" module_path [ "{" identifier { "," identifier } "}" ] ";" ;
module_path = identifier ;
```

```tern
import math;
import math { square, cube };
```

`import math;` loads the file `math.tn` from the same directory as the importing file.

### 3.9 Exports

```ebnf
export_stmt = "export" "{" identifier { "," identifier } "}" ";" ;
```

```tern
export { square, cube };
```

### 3.10 Input and output

```ebnf
input_stmt    = "in" [ "[" { input_clause } "]" ]
                "{" input_target { "," input_target } "}" ";" ;
input_clause  = "file" ":" expression ";" ;
input_target  = postfix | "_" ;

output_stmt   = "out" [ "[" { output_clause } "]" ] expression ";" ;
output_clause = "file" ":" expression ";"
              | "overwrite" ":" expression ";" ;
```

The optional `[...]` configuration comes first, followed by the data: a list of destinations for `in`, a string for `out`. Each clause may appear at most once.

```tern
in { age, _, score };
in [ file: "data.txt"; ] { age, score };

out "Age: ${age : int}";
out [ file: "log.txt"; overwrite: true; ] "Age: ${age : int}";
```

The data is not an executable block, so `in` and `out` do not use `=>`, and both statements end with `;`, including `in`, whose `{}` holds a list of names rather than code.

A `[` directly after `in` or `out` always begins configuration. To output an array literal, wrap it in parentheses: `out (['h', 'i']);`.

Clauses are described in [§10.5](#105-input) and [§10.6](#106-output).

### 3.11 Statements and blocks

```ebnf
block     = "{" { statement } "}" ;

statement = variable_decl
          | expression_stmt
          | step_stmt
          | return_stmt
          | "break" ";"
          | "continue" ";"
          | "delete" expression ";"
          | input_stmt
          | output_stmt ;

expression_stmt = rhs
                | unary assign_op block_expr ;
step_stmt       = postfix ( "++" | "--" ) ";" ;
return_stmt     = "return" ( ";" | rhs ) ;
```

The second form of `expression_stmt` allows assigning a `when` or `loop` result without a trailing semicolon: `x = when { ... }`.

`x++` and `x--` are statements, not expressions: they are equivalent to `x += 1;` and `x -= 1;` and produce no value.

A statement that starts with a type is a declaration. The parser tells `Point p = ...` (declaration) from `p = ...` (assignment) by looking past the type: a declaration always has an identifier immediately after its type.

### 3.12 Expressions

Each level below corresponds to one row of the precedence table in [§4](#4-operator-precedence).

```ebnf
expression     = assignment ;
assignment     = logical_or [ assign_op assignment ] ;
assign_op      = "=" | "+=" | "-=" | "*=" | "/=" | "%=" ;
logical_or     = logical_and { "||" logical_and } ;
logical_and    = equality { "&&" equality } ;
equality       = relational { ( "==" | "!=" ) relational } ;
relational     = additive { ( "<" | "<=" | ">" | ">=" ) additive } ;
additive       = multiplicative { ( "+" | "-" ) multiplicative } ;
multiplicative = unary { ( "*" | "/" | "%" ) unary } ;
unary          = ( "@" | "&" | "!" | "-" ) unary | postfix ;
postfix        = primary { "(" [ arguments ] ")" | "[" expression "]" | "." identifier } ;
arguments      = expression { "," expression } ;

primary        = integer_lit | char_lit | string_lit
               | "true" | "false" | "null"
               | identifier
               | array_lit
               | struct_lit
               | new_expr
               | "(" expression ")"
               | "(" block_expr ")" ;

array_lit      = "[" [ expression { "," expression } ] "]" ;
struct_lit     = identifier "{" [ field_init { "," field_init } ] "}" ;
field_init     = identifier ":" expression ;
new_expr       = "new" ( struct_lit | base_type "[" expression "]" ) ;
```

The left operand of an assignment must be a variable, a field (`p.x`, `(@p).x`), an indexed element (`a[i]`), or a dereference (`@p`).

---

## 4. Operator precedence

From highest to lowest:

| Level | Operators | Description | Associativity |
|---|---|---|---|
| 1 | `()` `[]` `.` | Call, index, member access | Left |
| 2 | `@` `&` `!` `-` (unary) | Dereference, address-of, logical NOT, negation | Right |
| 3 | `*` `/` `%` | Multiplication, division, remainder | Left |
| 4 | `+` `-` | Addition, subtraction | Left |
| 5 | `<` `<=` `>` `>=` | Relational comparison | Left |
| 6 | `==` `!=` | Equality | Left |
| 7 | `&&` | Logical AND | Left |
| 8 | `\|\|` | Logical OR | Left |
| 9 | `=` and compound assignment | Assignment | Right |

Parentheses override precedence:

```tern
val result = (a + b) * c;
```

`++` and `--` are not operators in this table: they form statements of their own ([§3.11](#311-statements-and-blocks)).

---

## 5. Types

### 5.1 Primitive type

Tern has a single primitive type, `val`, which holds one of three interpretations: **integer**, **character**, or **boolean**.

```tern
val number  = 42;
val letter  = 'A';
val enabled = true;
```

A mutable `val` may change its interpretation. The runtime tracks each value's current interpretation; there is no explicit conversion syntax.

```tern
val x = 10;
x = 'A';
x = false;
```

### 5.2 Arrays

Arrays are declared with `[]`; each additional `[]` adds a dimension.

```tern
val[]   numbers = [1, 2, 3];
val[][] matrix;
```

Arrays are homogeneous: every element of a primitive array shares the same interpretation. The rules for changing an existing element's interpretation are not yet final.

### 5.3 Strings

Strings are arrays of characters. There is no separate string type.

```tern
val[] name = "Alex";
```

### 5.4 Structures

Structures group named fields.

```tern
struct Student {
    const val id;
    val[] name;
    val score;
}
```

Fields may be primitives, arrays, other structures, or pointers. Structures are data-only: they have no methods, constructors, or inheritance.

### 5.5 Nominal typing

Two structure values are compatible only if they have the same declared structure type.

```tern
struct Point  { val x; val y; }
struct Vector { val x; val y; }

Point p = Point {};
Vector v = p; // Error: identical fields, different types
```

### 5.6 Recursive structures

A structure may not contain itself by value, directly or indirectly.

```tern
struct Node {
    Node next; // Error
}
```

Use a pointer to build recursive data structures:

```tern
struct Node {
    val data;
    @Node next;
}
```

### 5.7 Pointers

Pointer types are written with `@`. The address-of operator is `&`; the dereference operator is `@`.

```tern
@val p;
@Point node;

val x = 10;
@val q = &x;
@q = 20;
```

Pointers support equality comparison, arithmetic, and indexing ([§9.4](#94-pointer-arithmetic)).

---

## 6. Declarations

### 6.1 Mutable variables

Variables are mutable unless declared `const`.

```tern
val x = 10;
x = 20;
```

### 6.2 Constants

The `const` modifier prevents reassignment. Constants, including constant structure fields, must be initialized explicitly.

```tern
const val MAX = 100;
const val MIN;       // Error: missing initializer
```

### 6.3 Default initialization

All storage is zero-initialized unless explicitly initialized. An uninitialized `val` is the integer `0`.

| Kind | Default |
|---|---|
| Integer | `0` |
| Character | `'\0'` |
| Boolean | `false` |
| Pointer | `null` |
| Array, structure | All storage zeroed |

### 6.4 Scope

Tern uses lexical block scoping: every executable `{}` block introduces a new scope.

```tern
val x = 10;

when {
    x > 0 => {
        val y = 20;
    }
}

// y is not accessible here.
```

### 6.5 Shadowing

An inner scope may shadow an outer variable. The inner name refers to a separate variable.

```tern
val x = 10;

when {
    x > 0 => {
        val x = 20; // Shadows the outer x
    }
}
```

### 6.6 Structure initialization

Structures are initialized by field name. Omitted mutable fields receive their default values; constant fields must be initialized explicitly.

```tern
Point p = Point {
    x: 10,
    y: 20
};
```

### 6.7 Function overloading

Functions may share a name if their parameter lists differ in count or types. Return type alone cannot distinguish overloads.

```tern
fn show(val x) => {
    out "${x : int}";
}

fn show(val[] x) => {
    out "${x : char[]}";
}
```

---

## 7. Statements and control flow

### 7.1 Conditional execution

`when` handles all conditional execution.

```tern
when {
    age >= 18 => {
        out "Adult";
    }
    _ => {
        out "Minor";
    }
}
```

- Conditions are evaluated from top to bottom.
- Only the first matching arm is selected.
- The optional `_` arm matches unconditionally and must be the last arm.

### 7.2 Conditional result values

A `when` expression evaluates to the zero-based index of the selected arm, or `-1` if no arm matched. An arm ending in `;` is selected without executing a block.

```tern
val result = when {
    x > 100;
    x > 50;
    x > 0;
    _;
}
```

| Selected arm | Result |
|---|---|
| First | `0` |
| Second | `1` |
| Third | `2` |
| Fourth | `3` |
| No match | `-1` |

Arms cannot specify custom result values.

### 7.3 Loops

Tern has a single loop construct, configured by three optional clauses:

| Clause | Purpose | When omitted |
|---|---|---|
| `init` | Runs once before the loop | Nothing runs |
| `cond` | Decides whether the next iteration begins | Treated as `true` |
| `step` | Runs after each iteration | Nothing runs |

```tern
loop [
    init: val i = 0;
    cond: i < 10;
    step: i++;
] => {
    out "${i : int}";
}
```

Execution always proceeds in this order:

1. Run `init`.
2. Evaluate `cond`; if false, the loop ends.
3. Run the body.
4. Run `step`.
5. Repeat from step 2.

### 7.4 While-style loops

A loop with only a `cond` clause behaves like a traditional `while` loop.

```tern
loop [
    cond: x > 0;
] => {
    x--;
}
```

### 7.5 Infinite loops

An empty configuration creates an unconditional loop, which runs until `break`, `return`, or a runtime error ends it.

```tern
loop [] => {
    out "Running";
}
```

### 7.6 Multi-statement clauses

`init` and `step` may each contain a block. Variables declared in `init` are visible to `cond`, `step`, and the body, but not after the loop.

```tern
loop [
    init: {
        val i = 0;
        val j = 10;
    }
    cond: i < j;
    step: {
        i++;
        j--;
    }
] => {
    // Loop body.
}
```

### 7.7 Loop result values

A `loop` expression evaluates to the number of iterations entered. If `cond` is initially false, the result is `0`.

```tern
val count = loop [
    init: val i = 0;
    cond: i < 5;
    step: i++;
] => {
    out "${i : int}";
}

// count is 5
```

### 7.8 Break

`break` ends the nearest enclosing loop immediately. The `step` clause is skipped. The iteration in which `break` occurred counts toward the loop's result.

```tern
loop [] => {
    break;
}
// evaluates to 1
```

### 7.9 Continue

`continue` skips the rest of the current body. The `step` clause then runs before `cond` is evaluated again. The interrupted iteration counts toward the loop's result.

```tern
loop [
    init: val i = 0;
    cond: i < 10;
    step: i++;
] => {
    when {
        i == 5 => { continue; }
    }
}
```

### 7.10 Return

`return` exits a function with a value. A function without a return type may use `return;` to exit early.

```tern
fn square(val x) -> val => {
    return x * x;
}

fn greet() => {
    out "Hello!";
    return;
}
```

---

## 8. Expressions and evaluation order

### 8.1 Arithmetic

Tern supports `+`, `-`, `*`, `/`, and `%`. All arithmetic is integer arithmetic; division truncates toward zero.

```tern
val a = 7 / 2;   // 3
val b = -7 / 2;  // -3
```

### 8.2 Logical operators

Tern supports `&&`, `||`, and `!`. `&&` and `||` short-circuit.

### 8.3 Comparisons

| Operand kind | Supported operators |
|---|---|
| Primitive | `==` `!=` `<` `<=` `>` `>=` |
| Pointer | `==` `!=` |
| Array, structure | None |

### 8.4 Assignment

Assignment uses `=`. Structures and arrays are copied by value:

```tern
Point a = Point { x: 10, y: 20 };
Point b = a;

b.x = 50; // a.x is still 10
```

Assigning a pointer copies the address, so both pointers refer to the same allocation:

```tern
@Point p = new Point {};
@Point q = p;
```

### 8.5 String interpolation

Strings may embed values with `${expression : format}`.

| Format | Meaning |
|---|---|
| `int` | Integer |
| `char` | Character |
| `bool` | Boolean |
| `char[]` | Character array (string) |

```tern
val age = 20;
val[] name = "Alex";

out "Hello, ${name : char[]}! Age: ${age : int}";
```

Only primitives and strings can be formatted directly; other arrays, structures, and pointers cannot.

### 8.6 Evaluation order

- `when` conditions are evaluated top to bottom, and only the first matching arm executes.
- `loop` runs `init` once, evaluates `cond` before each iteration, and runs `step` after each body.
- `continue` runs `step`; `break` skips it.
- `&&` and `||` short-circuit.

The evaluation order of function arguments and of expressions with multiple side effects is not yet specified.

---

## 9. Memory model

### 9.1 Automatic storage

Local variables have automatic storage, zero-initialized unless explicitly initialized. That storage becomes invalid when its scope ends.

### 9.2 Dynamic allocation

`new` allocates zero-initialized storage on the heap.

```tern
@Point p       = new Point {};
@val   numbers = new val[10];
```

The runtime may use C allocation functions internally.

### 9.3 Deallocation

`delete` releases dynamic storage and sets the pointer variable to `null`.

```tern
@Point p = new Point {};
delete p;
// p == null
```

Deleting `null` has no effect. Deleting an offset pointer (one that does not point to the start of an allocation) is invalid.

### 9.4 Pointer arithmetic

Pointers support addition and subtraction of integer offsets, scaled by the size of the pointed-to type. Indexing is defined in terms of arithmetic:

```text
p[i] ≡ @(p + i)
```

```tern
@val numbers = new val[10];

numbers[0] = 10;
numbers[1] = 20;
```

Subtracting two pointers into the same allocation yields their distance in elements.

### 9.5 Dereferencing

```tern
val x = 10;
@val p = &x;

@p = 20;
```

Dereferencing `null` is a runtime error, as is any other invalid memory access.

### 9.6 Structure pointers

Field access through a pointer requires an explicit dereference. Tern has no implicit pointer member access.

```tern
@Point p = new Point { x: 10, y: 20 };

(@p).x = 30; // OK
p.x = 30;    // Error
```

### 9.7 Pointer copies

Copying a pointer copies its address. Deleting one copy does not reset the others, which are left dangling.

```tern
@Point a = new Point {};
@Point b = a;

delete a; // a is null; b is dangling
```

### 9.8 Value copies

Arrays and structures have value semantics: assignment copies their contents and never creates an alias. The representation of dynamically sized arrays, and how deep copies are implemented, is not yet specified.

---

## 10. Program entry and runtime

### 10.1 Entry point

Every executable program starts in `main`.

```tern
fn main() => {
    out "Hello, world!";
}
```

### 10.2 Modules

Each source file is a module; no module declaration is needed. Members are accessed with qualified names.

```tern
import math;

math.square(5);
```

### 10.3 Selective imports

Exported names may be imported directly and then used unqualified. Import aliases are not supported, and conflicting imported names are a compile-time error.

```tern
import math { square, cube };

val result = square(5);
```

### 10.4 Exports

A module lists its exported names in an optional export statement at the end of the file. Declarations that are not exported are private to the module. Exporting an overloaded name exports every overload with that name.

```tern
export { square, cube };
```

### 10.5 Input

`in` reads values into a list of destinations, in order. `_` skips a value.

```tern
in { age, _, score };
in [ file: "data.txt"; ] { age, score };
```

| Clause | Meaning | Default |
|---|---|---|
| `file` | File to read from | Standard input |

How incoming values are parsed and separated is not yet specified.

### 10.6 Output

`out` writes one string, which may be any `char[]` expression, including an interpolated string.

```tern
out "Hello, world!";
out greeting;
out [ file: "log.txt"; ] "Hello, world!";
out [ file: "log.txt"; overwrite: true; ] "New contents";
```

| Clause | Meaning | Default |
|---|---|---|
| `file` | File to write to | Standard output |
| `overwrite` | Replace the file's contents instead of appending | `false` |

Writing to a file appends by default, so repeated `out` statements, such as one per loop iteration, build up the file line by line.

### 10.7 Runtime errors

Runtime errors are reported through the project's C-based error-handling system, which is specified separately. They include:

- Division by zero.
- Null-pointer dereference.
- Invalid memory access.
- Invalid deallocation.

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
| Syntax error | `val x = 10` | `error: expected ';' after declaration` |
| Type mismatch | `Vector v = p;` where `p` is a `Point` | `error: cannot assign 'Point' to 'Vector'` |
| Invalid comparison | `a == b` where both are `val[]` | `error: comparison is not supported for array types` |
| Constant modification | `MAX = 200;` where `MAX` is `const` | `error: cannot assign to constant 'MAX'` |
| Recursive structure | `struct Node { Node next; }` | `error: recursive structure definition`<br>`note: use '@Node' to store a pointer instead` |

---

## 12. Example program

```tern
struct Student {
    const val id;
    val[] name;
    val score;
}

fn classify(val score) -> val => {
    return when {
        score >= 90;
        score >= 75;
        score >= 50;
        _;
    }
}

fn main() => {
    Student student = Student {
        id: 1,
        name: "Alex",
        score: 85
    };

    out "Student: ${student.name : char[]}";
    out "Score: ${student.score : int}";

    val category = classify(student.score);

    when {
        category == 0 => { out "Excellent"; }
        category == 1 => { out "Good"; }
        category == 2 => { out "Pass"; }
        _             => { out "Fail"; }
    }

    val iterations = loop [
        init: val i = 0;
        cond: i < 3;
        step: i++;
    ] => {
        out "Iteration ${i : int}";
    }

    out "Total iterations: ${iterations : int}";
}
```

**Expected output**

```text
Student: Alex
Score: 85
Good
Iteration 0
Iteration 1
Iteration 2
Total iterations: 3
```

---

## Appendix A. Outstanding details

These need decisions before the specification is implementation-ready. They are semantic and implementation questions; none requires changing the established syntax.

| Area | Open question |
|---|---|
| Input | How primitives are parsed and how inputs are separated |
| Integers | Width, overflow, and arithmetic edge cases |
| Characters | Encoding and string termination |
| Arrays | Length, resizing, bounds checking, and interpretation changes |
| Memory | Ownership and copying of dynamic arrays |
| Pointers | Bounds, dangling pointers, and invalid arithmetic |
| Functions | Argument evaluation order and overload resolution |
| Entry point | Permitted signatures for `main` |
| I/O | Whether `in` and `out` require an explicit import |
| Runtime | Detailed error-handling behavior |

---

## Appendix B. Syntax reference

| Construct | Syntax |
|---|---|
| Variable | `val x = 10;` |
| Constant | `const val x = 10;` |
| Array | `val[] a = [1, 2, 3];` |
| Structure | `struct Point { val x; val y; }` |
| Function | `fn name() => { ... }` |
| Function with return type | `fn name() -> val => { ... }` |
| Conditional | `when { condition => { ... } }` |
| Loop | `loop [ cond: condition; ] => { ... }` |
| Input | `in { x };` |
| Input from file | `in [ file: "data.txt"; ] { x };` |
| Output | `out "Hello";` |
| Output to file | `out [ file: "log.txt"; ] "Hello";` |
| Pointer | `@val p = &x;` |
| Dereference | `@p` |
| Allocation | `new Point {}` |
| Deallocation | `delete p;` |
| Import | `import math;` |
| Selective import | `import math { square };` |
| Export | `export { square };` |
