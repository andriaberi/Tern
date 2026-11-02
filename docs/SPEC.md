# Tern Language Specification

**Version** 0.2.0 · **Status** Draft · **File extension** `.tn`

Tern is a general-purpose programming language built around minimal syntax, predictable behavior, and explicit control over program execution and memory.

- A single primitive type, `val`: a 64-bit signed integer that also holds characters and booleans.
- Fixed-size arrays, slices, and data-only structures.
- A unified conditional statement, `when`, and a unified loop statement, `loop`.
- Functions with overloading.
- Explicit pointers and memory management, with no hidden allocation.
- File-based modules.
- Built-in input and output.

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
- [Appendix A. Not in this version](#appendix-a-not-in-this-version)
- [Appendix B. Syntax reference](#appendix-b-syntax-reference)

---

## 1. Overview

Tern follows a small set of syntactic conventions:

| Syntax | Purpose | Example |
|---|---|---|
| `()` | Parameters, arguments, and grouping | `add(5, 10)`, `(a + b) * c` |
| `[]` | Arrays, sizes, indexing, and configuration | `[1, 2, 3]`, `val[4]`, `numbers[0]`, `loop [ i < 10 ]` |
| `{}` | Executable blocks, structures, `when` arms, and name lists | `struct Point { ... }`, `import math { square };` |
| `=>` | Separates a `when` condition from its block | `x > 0 => { ... }` |
| `->` | Specifies a function's return type | `fn add(val a, val b) -> val` |
| `;` | Terminates simple statements and separates configuration parts | `val x = 10;`, `loop [ val i = 0; i < 10; i++ ]` |
| `,` | Separates items in a list | `val i = 0, j = 10;`, `add(1, 2)` |

Square brackets directly after `loop`, `in`, or `out` hold that construct's **configuration**; they are never array literals or indexing. Configuration always comes before the construct's body or data. Inside a configuration, `;` separates parts and `,` separates items within one part.

```tern
loop [ val i = 0 .. 10 ] {
    out "${i}\n";
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
val age;
val totalScore;
val[] studentName;
```

### 2.3 Keywords

```text
val       const     struct
fn        return
when      loop
break     continue
import    export
new       delete
in        out
true      false     null
```

The underscore `_` marks the default arm of a `when` and a skipped destination in `in`.

The format names `int`, `char`, and `bool` are **contextual words**: they have special meaning only in the format part of a `${...}` interpolation ([§8.5](#85-string-interpolation)) and are ordinary identifiers everywhere else.

### 2.4 Literals

| Kind | Examples | Type | Notes |
|---|---|---|---|
| Integer | `0`, `42`, `100` | `val` | Decimal only. Negative numbers use unary negation: `-10` |
| Character | `'A'`, `'7'`, `'\n'`, `'\0'` | `val` | The character's code: `'A'` is `65` |
| Boolean | `true`, `false` | `val` | `1` and `0` |
| Null | `null` | Any pointer or slice | |
| String | `"Hello, world!"` | `val[]` | A read-only slice of characters ([§5.4](#54-strings)) |

```ebnf
integer_lit = digit { digit } ;
char_lit    = "'" ( char | escape ) "'" ;
string_lit  = '"' { char | escape | interpolation } '"' ;
escape      = "\" ( "n" | "t" | "r" | "0" | "\" | "'" | '"' | "$" ) ;
```

`char` is any source character other than a newline, a backslash, or the literal's own quote.

- An integer literal must not exceed 9223372036854775807 (2⁶³ − 1). The smallest `val` is written `-9223372036854775807 - 1`.
- A character literal holds exactly one ASCII character or escape.
- A string literal holds one element per byte of its UTF-8 encoding. Strings have no terminator; their length is part of the slice.

In a string, `${` always begins an interpolation ([§8.5](#85-string-interpolation)); write `\$` for a literal dollar sign.

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

Simple statements end with a semicolon.

```tern
val x = 10;
x += 5;
```

A construct that ends in a block — `when`, `loop`, function declarations, and structure declarations — never takes a semicolon after its closing brace:

```tern
when {
    x > 0 => { out "positive\n"; }
}

struct Point { val x, y; }
```

Structure literals are data, not blocks, so the statement containing them still ends with a semicolon. So do `in` and `out`, whose `{}` and `[]` hold data and configuration rather than code.

```tern
Point p = { x: 10, y: 20 };
in { age };
```

---

## 3. Grammar

The grammar uses EBNF notation: `{ x }` means zero or more, `[ x ]` means optional, and `|` separates alternatives. Lexical rules are in [§2](#2-lexical-structure).

### 3.1 Programs

```ebnf
program     = { import_stmt } { declaration } [ export_stmt ] ;
declaration = variable_decl | function_decl | struct_decl ;
```

Only declarations appear at the top level of a module; executable statements belong inside functions. A top-level `variable_decl` declares global variables. An export statement, if present, must be the last item in its module.

### 3.2 Types

```ebnf
type         = { "@" } base_type { array_suffix } ;
base_type    = "val" | type_name ;
type_name    = identifier [ "." identifier ] ;
array_suffix = "[" [ integer_lit ] "]" ;
```

```tern
val
val[4]
val[]
val[3][4]
Point
math.Point
@val
@Point
```

- `[N]` is a fixed-size array of `N` elements; `N` must be a positive integer literal ([§5.2](#52-fixed-size-arrays)).
- `[]` is a slice ([§5.3](#53-slices)).
- The first suffix is the outermost: `val[3][4]` has 3 elements, each a `val[4]`, so `m[i][j]` takes `i < 3` and `j < 4`. Suffixes may mix: `val[][4]` is a slice of `val[4]`.
- `@` binds to the base type before any suffix, so `@val[]` is a slice of pointers to `val`, and `@@val` is a pointer to a pointer to `val`.
- `math.Point` names the structure `Point` exported by the imported module `math` ([§10.2](#102-modules)).

### 3.3 Variable declarations

```ebnf
variable_decl = decl_body ";" ;
decl_body     = [ "const" ] type declarator { "," declarator } ;
declarator    = identifier [ "=" expression ] ;
```

```tern
val x;
val y = 10;
val i = 0, j = 10;

const val MIN = 1, MAX = 100;

val[3] numbers = [1, 2, 3];
val[] name = "Alex";
val[3][3] matrix;
```

One declaration may declare several variables of the same type ([§6.3](#63-several-variables-in-one-declaration)).

### 3.4 Conditionals

```ebnf
when_stmt = "when" "{" when_arm { when_arm } "}" ;
when_arm  = ( expression | "_" ) "=>" block ;
```

```tern
when {
    x > 100 => {
        out "Large\n";
    }
    x > 50 => {
        out "Medium\n";
    }
    _ => {
        out "Small\n";
    }
}
```

`when` is a statement and produces no value. Semantics are defined in [§7.1](#71-conditional-execution).

### 3.5 Loops

A loop's configuration in square brackets is followed by its body. The number of parts in the configuration decides the loop's form.

```ebnf
loop_stmt   = "loop" "[" [ loop_config ] "]" block ;
loop_config = expression                                        (* condition *)
            | "val" identifier "=" expression ".." expression   (* range *)
            | [ loop_setup ] ";" [ expression ] ";" [ simple_list ] ;
loop_setup  = decl_body | simple_list ;
simple_list = simple_stmt { "," simple_stmt } ;
```

```tern
loop [] { ... }                                  // forever
loop [ x > 0 ] { ... }                           // while x > 0
loop [ val i = 0 .. 10 ] { ... }                 // i = 0, 1, ..., 9
loop [ val i = 0; i < 10; i++ ] { ... }          // setup; condition; step
loop [ val i = 0, j = 10; i < j; i++, j-- ] { ... }
```

A configuration with a single part is a range if it has the form `val name = start .. end`, and a condition otherwise. A configuration with two parts is a compile-time error. `loop` is a statement and produces no value. Semantics are defined in [§7.2](#72-loops).

### 3.6 Functions

```ebnf
function_decl  = "fn" identifier "(" [ parameter_list ] ")" [ "->" type ] block ;
parameter_list = parameter { "," parameter } ;
parameter      = type identifier ;
```

```tern
fn add(val a, val b) -> val {
    return a + b;
}

fn greet() {
    out "Hello!\n";
}
```

A function without `-> type` returns no value. Each parameter has its own type: `fn add(val a, b)` is a syntax error.

### 3.7 Structures

```ebnf
struct_decl = "struct" identifier "{" { field_decl } "}" ;
field_decl  = decl_body ";" ;
```

```tern
struct Point {
    val x, y;
}
```

A field's default value, if given, must be a constant expression ([§6.5](#65-global-variables)).

### 3.8 Imports

```ebnf
import_stmt = "import" identifier [ "{" identifier { "," identifier } "}" ] ";" ;
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
input_expr   = "in" [ "[" expression "]" ] "{" input_target { "," input_target } "}" ;
input_target = postfix | "_" ;

output_stmt  = "out" [ "[" expression [ ";" expression ] "]" ] expression ";" ;
```

The optional configuration in `[...]` names a file, followed for `out` by an optional overwrite flag. Then comes the data: a list of destinations for `in`, the text to write for `out`.

```tern
in { age, _, score };
in [ "data.txt" ] { age, score };

out "Age: ${age}\n";
out [ "log.txt" ] "Age: ${age}\n";
out [ "log.txt"; true ] "Fresh log\n";   // true: empty the file first
```

`in` is an expression that evaluates to the number of destinations filled ([§10.5](#105-input)), so it can stand alone as a statement or appear in a condition:

```tern
loop [ in { x } == 1 ] {
    out "Read ${x}\n";
}
```

The data is not an executable block. A `[` directly after `in` or `out` always begins configuration; to output an array literal, wrap it in parentheses: `out (['h', 'i']);`.

Semantics are defined in [§10.5](#105-input) and [§10.6](#106-output).

### 3.11 Statements and blocks

```ebnf
block       = "{" { statement } "}" ;

statement   = variable_decl
            | simple_stmt ";"
            | when_stmt
            | loop_stmt
            | return_stmt
            | "break" ";"
            | "continue" ";"
            | "delete" unary ";"
            | output_stmt ;

simple_stmt = expression [ assign_op expression ]
            | postfix ( "++" | "--" ) ;
assign_op   = "=" | "+=" | "-=" | "*=" | "/=" | "%=" ;
return_stmt = "return" [ expression ] ";" ;
```

- Assignment is a statement, not an expression: it produces no value and cannot be nested in another expression. Its left side must be assignable: a variable, a field (`p.x`), an indexed element (`a[i]`), or a dereference (`@p`).
- A simple statement without an assignment or `++`/`--` must be a function call or an `in` expression; anything else, such as `x + 1;`, is a compile-time error.
- `x++` and `x--` are statements equivalent to `x += 1;` and `x -= 1;`.
- The operand of `delete` must be assignable ([§9.3](#93-deallocation)).

A statement that starts with a type followed by an identifier is a declaration. The parser tells `Point p = ...` (declaration) from `p = ...` (assignment), and `Point[3] ps;` from `a[3] = 5;`, by reading a type and checking whether an identifier comes next.

### 3.12 Expressions

Each level below corresponds to one row of the precedence table in [§4](#4-operator-precedence).

```ebnf
expression     = logical_or ;
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
               | input_expr
               | "(" expression ")" ;

array_lit      = "[" expression { "," expression } "]" ;
struct_lit     = [ type_name ] struct_body ;
struct_body    = "{" [ field_init { "," field_init } ] "}" ;
field_init     = identifier ":" expression ;
new_expr       = "new" ( type_name struct_body | base_type "[" expression "]" ) ;
```

A structure literal may leave out its type name only where the type is already known ([§6.8](#68-structure-initialization)).

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

Parentheses override precedence:

```tern
val result = (a + b) * c;
```

Assignment, `++`, and `--` are not operators: they form statements of their own ([§3.11](#311-statements-and-blocks)). `..` is not an operator either: it appears only in a range loop ([§7.3](#73-range-loops)).

---

## 5. Types

### 5.1 Primitive type

Tern has a single primitive type, `val`: a 64-bit signed two's-complement integer. Characters and booleans are integers too.

```tern
val number  = 42;
val letter  = 'A';   // 65
val enabled = true;  // 1
```

A `val` carries no record of what it represents; the same value may be used as a number, a character, or a truth value. How it is printed is chosen by the format in an interpolation ([§8.5](#85-string-interpolation)).

```tern
val x = 'A';
x = x + 1;           // 66, the code of 'B'
```

Wherever a condition is expected (`when` arms, loop conditions, `!`, `&&`, `||`), the operand must be a `val`; zero is false and any other value is true.

### 5.2 Fixed-size arrays

`T[N]` holds exactly `N` elements of type `T`, stored in place: inside the variable, the structure, or the enclosing array. `N` is a positive integer literal.

```tern
val[3]    numbers = [1, 2, 3];
val[3][3] matrix;
```

Fixed-size arrays are values: assigning or passing one copies all its elements.

### 5.3 Slices

`T[]` is a slice: a pointer to a run of `T` elements plus its length. A slice does not own its elements; copying a slice copies the pointer and length, so both copies refer to the same elements.

A slice is obtained from:

- A string literal ([§5.4](#54-strings)).
- An array literal assigned or passed where a slice is expected. The literal's elements live until the end of the enclosing block, like a local variable.
- `new T[n]` ([§9.2](#92-dynamic-allocation)).
- A fixed-size array, which converts to a slice of its elements. The slice is valid only while the array exists.

```tern
val[]  a = [1, 2, 3];
val[4] b;
val[]  c = b;        // c refers to b's elements
c[0] = 7;            // b[0] is now 7
```

The default slice, and `null` assigned to a slice, has a null pointer and length `0`.

### 5.4 Strings

Strings are slices of characters, type `val[]`. There is no separate string type and no terminator; `.len` gives the length.

```tern
val[] name = "Alex";  // name.len is 4
```

The elements of a string literal are read-only and shared by every evaluation of the literal. Writing to them is undefined ([§9.9](#99-undefined-behavior)); copy the text into a fixed-size array first.

### 5.5 Length

Every array and slice has a read-only member `len`, the number of elements. For `T[N]` it is the constant `N`.

```tern
val[5] a;
val[] s = "hi";
// a.len is 5, s.len is 2
```

Indexing an array or slice outside `0 … len - 1` is a runtime error.

### 5.6 Structures

Structures group named fields.

```tern
struct Student {
    const val id;
    val[] name;
    val score;
}
```

Fields may be `val`, fixed-size arrays, slices, other structures, or pointers. Structures are data-only: they have no methods, constructors, or inheritance.

### 5.7 Nominal typing

Two structure values are compatible only if they have the same declared structure type.

```tern
struct Point  { val x, y; }
struct Vector { val x, y; }

Point p = {};
Vector v = p; // Error: identical fields, different types
```

### 5.8 Recursive structures

A structure may not contain itself by value, directly or indirectly, including through a fixed-size array.

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

### 5.9 Pointers

Pointer types are written with `@`. The address-of operator is `&`; the dereference operator is `@`.

```tern
@val p;
@Point node;

val x = 10;
@val q = &x;
@q = 20;
```

Pointers support equality comparison, arithmetic, and indexing ([§9.4](#94-pointer-arithmetic)).

### 5.10 Conversions

Tern has exactly two implicit conversions and no explicit conversion syntax:

| From | To |
|---|---|
| `T[N]` | `T[]` |
| `null` | Any pointer or slice type |

Every other use of a value where a different type is expected is a compile-time error.

---

## 6. Declarations

### 6.1 Mutable variables

Variables are mutable unless declared `const`.

```tern
val x = 10;
x = 20;
```

### 6.2 Constants

The `const` modifier prevents modification of the variable's whole storage: a constant fixed-size array's elements and a constant structure's fields cannot be assigned either. For a constant slice or pointer, the slice or pointer itself is fixed; the elements it refers to are not made read-only.

Constants, including constant structure fields, must be initialized explicitly. Taking the address of a constant, or of any part of one, is a compile-time error.

```tern
const val MAX = 100;
const val MIN;       // Error: missing initializer
@val p = &MAX;       // Error: address of a constant
```

### 6.3 Several variables in one declaration

A declaration may declare several variables, separated by commas. The type, and `const` if present, apply to every name; each name may have its own initializer.

```tern
val i = 0, j = 10;
val x, y;              // both 0
const val LOW = 1, HIGH = 9;
val[3] a, b;           // both val[3]
@val p, q;             // both pointers to val
```

Names are declared from left to right, and each is in scope from the next declarator on, so `val i = 0, j = i + 1;` is valid. This form is allowed for local and global variables, structure fields, and a loop's setup; parameters are declared one per type.

### 6.4 Default initialization

All storage is zero-initialized unless explicitly initialized.

| Type | Default |
|---|---|
| `val` | `0` |
| Pointer | `null` |
| Slice | `null`, length `0` |
| Fixed-size array | Every element at its default |
| Structure | Every field at its declared default, or its type's default |

### 6.5 Global variables

A global variable's initializer, like a structure field's default, must be a constant expression: a literal, `null`, or an array or structure literal built only from constant expressions. Calls, variables, operators, and `new` are not allowed.

```tern
val limit = 100;
val[] greeting = "Hello";
val bad = limit * 2;  // Error: initializer is not constant
```

### 6.6 Scope

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

### 6.7 Shadowing

An inner scope may shadow an outer variable. The inner name refers to a separate variable.

```tern
val x = 10;

when {
    x > 0 => {
        val x = 20; // Shadows the outer x
    }
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

Elsewhere, and after `new`, the name is required.

### 6.9 Function overloading

Functions may share a name if their parameter lists differ in count or types. Return type alone cannot distinguish overloads.

```tern
fn show(val x) {
    out "${x}\n";
}

fn show(val[] x) {
    out x;
}
```

A call selects the overload whose parameter types match the argument types exactly, allowing only the conversions in [§5.10](#510-conversions). A structure literal without a type name matches any structure parameter in its position. If no overload matches, or more than one does, the call is a compile-time error. `main` cannot be overloaded.

### 6.10 Parameters

Arguments are passed by value: a `val`, fixed-size array, or structure is copied into the parameter. Passing a slice or pointer copies the slice or pointer, not the elements it refers to.

---

## 7. Statements and control flow

### 7.1 Conditional execution

`when` handles all conditional execution.

```tern
when {
    age >= 18 => {
        out "Adult\n";
    }
    _ => {
        out "Minor\n";
    }
}
```

- Conditions are evaluated from top to bottom.
- Only the first arm whose condition is true executes.
- The optional `_` arm matches unconditionally and must be the last arm.
- If no arm matches, nothing executes.

### 7.2 Loops

`loop` handles all repetition. Its configuration has zero, one, or three parts:

| Configuration | Form | Runs |
|---|---|---|
| `[]` | Infinite | Until `break`, `return`, or a runtime error |
| `[ condition ]` | Conditional | While the condition is true |
| `[ val i = start .. end ]` | Range | Once for each `i` from `start` up to, but not including, `end` |
| `[ setup; condition; step ]` | Three-part | Setup once, then while the condition is true, running the step after each iteration |

```tern
loop [ x > 0 ] {
    x--;
}
```

### 7.3 Range loops

A range loop counts a new variable upward by one:

```tern
loop [ val i = 0 .. 3 ] {
    out "${i}\n";        // 0, 1, 2
}
```

`start` and `end` are each evaluated once, before the first iteration. If `end` is not greater than `start`, the body never runs. The loop is equivalent to the three-part loop `[ val i = start; i < end; i++ ]`, except that `end` is not re-evaluated.

### 7.4 Three-part loops

```tern
loop [ val i = 0; i < 10; i++ ] {
    out "${i}\n";
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
loop [ val i = 0, j = 10; i < j; i++, j-- ] {
    // i and j move toward each other.
}
```

Variables declared in the setup or by a range are visible in the condition, the step, and the body, but not after the loop.

### 7.5 Break

`break` ends the nearest enclosing loop immediately. The step is skipped.

```tern
loop [] {
    break;
}
```

### 7.6 Continue

`continue` skips the rest of the current body. In a three-part or range loop, the step then runs before the condition is evaluated again.

```tern
loop [ val i = 0 .. 10 ] {
    when {
        i == 5 => { continue; }
    }
    out "${i}\n";
}
```

### 7.7 Return

`return` exits a function with a value. A function without a return type may use `return;` to exit early.

```tern
fn square(val x) -> val {
    return x * x;
}

fn greet() {
    out "Hello!\n";
    return;
}
```

In a function with a return type, every path must end in `return`; otherwise the function is a compile-time error. A `when` ends every path only if it has a `_` arm and every arm ends every path.

---

## 8. Expressions and evaluation order

### 8.1 Arithmetic

Tern supports `+`, `-`, `*`, `/`, and `%` on `val`. Arithmetic wraps around on overflow (two's complement).

- Division truncates toward zero.
- The result of `%` has the sign of the left operand.
- Division or remainder by zero is a runtime error, as is dividing the smallest `val` by `-1`.

```tern
val a = 7 / 2;   // 3
val b = -7 / 2;  // -3
val c = -7 % 2;  // -1
```

### 8.2 Logical operators

Tern supports `&&`, `||`, and `!` on `val`. They treat zero as false and anything else as true, and produce `1` or `0`. `&&` and `||` short-circuit.

### 8.3 Comparisons

Comparisons produce `1` or `0`.

| Operand kind | Supported operators |
|---|---|
| `val` | `==` `!=` `<` `<=` `>` `>=` |
| Pointer | `==` `!=` |
| Array, slice, structure | None |

To test whether a slice is empty, compare its length: `s.len == 0`.

### 8.4 Assignment

Assignment uses `=`. Values of type `val`, fixed-size arrays, and structures are copied:

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

Assigning to a fixed-size array requires a value of the same size: `val[3] a = [1, 2];` is a compile-time error.

The compound operators `+=`, `-=`, `*=`, `/=`, and `%=` apply to `val`. `+=` and `-=` also apply to pointers ([§9.4](#94-pointer-arithmetic)).

### 8.5 String interpolation

A string may embed values with `${expression}` or `${expression : format}`. Interpolation is allowed only in the string that is the whole operand of an `out` statement; the values are written in place, and no string is ever built in memory.

| Format | Applies to | Writes |
|---|---|---|
| *(none)* | `val` | The decimal integer |
| *(none)* | `val[]`, `val[N]` | The elements as text |
| `int` | `val` | The decimal integer |
| `char` | `val` | The character |
| `bool` | `val` | `false` for zero, `true` otherwise |

```tern
val age = 20;
val[] name = "Alex";
val initial = 'A';

out "Hello, ${name}! Age: ${age}. Initial: ${initial : char}\n";
```

Writing a character, or text, writes the low 8 bits of each value as one byte. Other types (other arrays, structures, pointers) cannot be formatted. The expression inside `${...}` may not contain a string literal.

### 8.6 Evaluation order

Evaluation is strictly left to right:

- The operands of a binary operator, left before right (except where `&&` and `||` skip the right operand).
- Function arguments, first to last, then the call.
- In an assignment, the target's subexpressions (such as `i` in `a[i]`), then the right side.
- Declarators in a declaration, and statements in a loop's setup or step list, first to last.
- `in` destinations, first to last.

`when` conditions are evaluated top to bottom, and only the first matching arm executes.

---

## 9. Memory model

### 9.1 Automatic storage

Local variables, including fixed-size arrays and array literals, have automatic storage, zero-initialized unless explicitly initialized. That storage becomes invalid when its block ends, and any pointer or slice still referring to it dangles.

### 9.2 Dynamic allocation

`new` allocates zero-initialized storage on the heap. It is the only way a Tern program allocates: no other construct allocates behind the program's back.

```tern
@Point p       = new Point { x: 1 };
val[]  numbers = new val[10];
```

| Expression | Type | Storage |
|---|---|---|
| `new Point { ... }` | `@Point` | One structure, initialized like a structure literal |
| `new T[n]` | `T[]` | `n` elements, zeroed |

`n` is evaluated at runtime. `n == 0` gives an empty slice; a negative `n`, or running out of memory, is a runtime error.

### 9.3 Deallocation

`delete` releases storage obtained from `new` and sets its operand to `null` (for a slice: null pointer, length `0`). The operand must be assignable.

```tern
@Point p = new Point {};
delete p;
// p == null
```

Deleting `null` has no effect. Deleting anything not obtained from `new`, deleting the same storage twice (for example through a copy), or deleting a pointer that does not point to the start of an allocation, is undefined ([§9.9](#99-undefined-behavior)).

### 9.4 Pointer arithmetic

Pointers support addition and subtraction of `val` offsets, scaled by the size of the pointed-to type. Indexing is defined in terms of arithmetic:

```text
p[i] ≡ @(p + i)
```

Subtracting two pointers into the same allocation yields their distance in elements. Pointer arithmetic and indexing are not bounds-checked; to get a pointer to a slice's elements, write `&s[0]`.

### 9.5 Dereferencing

```tern
val x = 10;
@val p = &x;

@p = 20;
```

Dereferencing `null` is a runtime error.

### 9.6 Structure pointers

Member access with `.` looks through one pointer: if `p` is a `@Point`, `p.x` means `(@p).x`. Deeper pointers need explicit dereferences: for `@@Point pp`, write `(@pp).x`.

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

Every value has a size known at compile time, so every copy is a plain copy of that many bytes. Copying a `val`, fixed-size array, or structure copies its contents; copying a pointer or slice (including one stored in a structure) copies only the pointer and length.

### 9.9 Undefined behavior

The following are undefined: the program may crash, misbehave, or appear to work. Neither the compiler nor the runtime is required to detect them.

- Using storage after it has been deleted, or after its block has ended.
- Writing to the elements of a string literal.
- Pointer arithmetic that leaves its allocation, and accessing memory through such a pointer.
- Deleting storage not obtained from `new`, deleting it twice, or deleting an offset pointer.

---

## 10. Program entry and runtime

### 10.1 Entry point

Every executable program starts in `main`, declared in the file passed to the compiler. `main` takes no parameters and either returns no value or returns a `val`, which becomes the process's exit status. A `main` without a return type exits with status `0`.

```tern
fn main() {
    out "Hello, world!\n";
}

fn main() -> val {
    return 0;
}
```

### 10.2 Modules

Each source file is a module; no module declaration is needed. A module is loaded once however many files import it. Exported members are accessed with qualified names, including structure types.

```tern
import math;

val r = math.square(5);
math.Point p = { x: 1, y: 2 };
```

Import cycles, direct or indirect, are a compile-time error.

### 10.3 Selective imports

Exported names may also be imported directly and then used unqualified; their qualified names remain available. Import aliases are not supported, and conflicting imported names are a compile-time error.

```tern
import math { square, cube };

val result = square(5);
```

### 10.4 Exports

A module lists its exported names in an optional export statement at the end of the file. Functions, structures, and global variables can be exported. Declarations that are not exported are private to the module. Exporting an overloaded name exports every overload with that name.

An exported function or global variable may not mention a structure type that is not itself exported.

```tern
export { square, cube };
```

### 10.5 Input

`in` and `out` are built in and need no import.

`in` reads words separated by spaces, tabs, or newlines, and stores one word in each destination, in order. `_` reads a word and discards it. Without configuration it reads standard input; `in [ path ]` reads the file at `path`, which must be text (`val[]` or `val[N]`).

| Destination type | What is stored |
|---|---|
| `val` | The word read as a decimal integer, with an optional leading `-` |
| `val[]` | The word's bytes, written into the slice's existing elements; the slice's length is then set to the word's length |

```tern
val age;
val[32] buffer;
val[] name = buffer;

in { name, age };   // input "Alex 20": name is "Alex", age is 20
in [ "people.txt" ] { name, age };
```

`in` evaluates to the number of destinations filled, counting `_`. When input ends early, the remaining destinations are left unchanged and the count is lower than the number of destinations; at end of input it is `0`.

It is a runtime error if a `val` word is not a decimal integer or is out of range, or if a word is longer than its destination slice.

### 10.6 Output

`out` writes text — a `val[]` or `val[N]`, or a string with interpolation ([§8.5](#85-string-interpolation)) — exactly as given. It adds no newline; write `\n` where a line should end.

```tern
out "Hello, world!\n";
out greeting;
out "Name: ";                                // a prompt: no newline
out [ "log.txt" ] "Hello, world!\n";         // appended to log.txt
out [ "log.txt"; true ] "New contents\n";    // log.txt emptied first
```

Without configuration, `out` writes to standard output. `out [ path ]` appends to the file at `path`, which must be text. `out [ path; overwrite ]` takes a `val` as a second part: if it is true, the file is emptied before this write; if false, the write appends as usual.

### 10.7 Files

The runtime keeps at most one open input stream and one open output stream per path for the whole run, and closes them when the program exits.

- The first `in` from a path opens it; later `in` statements on the same path continue where the previous one stopped.
- The first `out` to a path opens it for appending, creating it if needed; later `out` statements continue writing to it. An overwrite flag that is true empties the file at that statement, and writing continues from there.
- Standard output is flushed before every read from standard input, so a prompt appears before the program waits.

A file that cannot be opened is a runtime error. Reading and writing the same path in one run is not supported in this version.

### 10.8 Runtime errors

A runtime error writes a message naming the error and its source location (file, line, and column) to standard error and ends the program with exit status `1`. Runtime errors are:

- Division or remainder by zero, and dividing the smallest `val` by `-1`.
- Dereferencing `null`, including member access through `null`.
- Indexing an array or slice out of bounds.
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
| Syntax error | `val x = 10` | `error: expected ';' after declaration` |
| Type mismatch | `Vector v = p;` where `p` is a `Point` | `error: cannot assign 'Point' to 'Vector'` |
| Size mismatch | `val[3] a = [1, 2];` | `error: cannot assign 'val[2]' to 'val[3]'` |
| Invalid comparison | `a == b` where both are `val[]` | `error: comparison is not supported for slice types`<br>`note: compare lengths with '.len'` |
| Constant modification | `MAX = 200;` where `MAX` is `const` | `error: cannot assign to constant 'MAX'` |
| Loop configuration | `loop [ val i = 0; i < 10 ] { }` | `error: a loop configuration has 0, 1, or 3 parts, not 2` |
| Missing return | `fn f() -> val { }` | `error: function 'f' does not return a value on every path` |
| Recursive structure | `struct Node { Node next; }` | `error: recursive structure definition`<br>`note: use '@Node' to store a pointer instead` |

---

## 12. Example program

```tern
struct Student {
    const val id;
    val[] name;
    val score;
}

fn grade(val score) -> val {
    when {
        score >= 90 => { return 'A'; }
        score >= 75 => { return 'B'; }
        score >= 50 => { return 'C'; }
        _           => { return 'F'; }
    }
}

fn main() {
    Student student = {
        id: 1,
        name: "Alex",
        score: 85
    };

    out "Student: ${student.name}\n";
    out "Score: ${student.score}\n";
    out "Grade: ${grade(student.score) : char}\n";

    val[3] squares;

    loop [ val i = 0 .. squares.len ] {
        squares[i] = i * i;
        out "Square ${i}: ${squares[i]}\n";
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

These are deliberately left out of version 0.2.

| Feature | Notes |
|---|---|
| Floating-point numbers | Not planned |
| Bitwise operators and shifts | `&`, `\|`, `^`, `~`, `<<`, `>>` |
| Command-line arguments | `main` takes no parameters |
| Import aliases and nested module paths | Modules are files in the same directory |
| Non-ASCII identifiers | |
| Array sizes from named constants | Sizes are integer literals |
| Sub-slices | Such as `s[1 .. 3]` |
| Counting down or by other steps in a range loop | Use a three-part loop |
| Empty array literals | `[]` with no elements |
| Interpolation outside `out` | |
| Reading and writing the same file in one run | |

---

## Appendix B. Syntax reference

| Construct | Syntax |
|---|---|
| Variable | `val x = 10;` |
| Several variables | `val i = 0, j = 10;` |
| Constant | `const val x = 10;` |
| Fixed-size array | `val[3] a = [1, 2, 3];` |
| Slice | `val[] s = "Hi";` |
| Length | `s.len` |
| Structure | `struct Point { val x, y; }` |
| Structure literal | `Point p = { x: 1, y: 2 };` |
| Function | `fn name() { ... }` |
| Function with return type | `fn name() -> val { ... }` |
| Conditional | `when { condition => { ... } _ => { ... } }` |
| Infinite loop | `loop [] { ... }` |
| Conditional loop | `loop [ x > 0 ] { ... }` |
| Range loop | `loop [ val i = 0 .. 10 ] { ... }` |
| Three-part loop | `loop [ val i = 0, j = 9; i < j; i++, j-- ] { ... }` |
| Input | `in { x };` |
| Input with count | `val n = in { x, y };` |
| Input from file | `in [ "data.txt" ] { x };` |
| Output | `out "x is ${x}\n";` |
| Output to file | `out [ "log.txt" ] "Hello\n";` |
| Overwrite a file | `out [ "log.txt"; true ] "Hello\n";` |
| Pointer | `@val p = &x;` |
| Dereference | `@p` |
| Field through pointer | `p.x` |
| Allocation | `new Point {}`, `new val[n]` |
| Deallocation | `delete p;` |
| Import | `import math;` |
| Selective import | `import math { square };` |
| Export | `export { square };` |
