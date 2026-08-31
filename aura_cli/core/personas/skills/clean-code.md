---
name: Clean Code Principles
description: Use this skill when the user asks about writing clean code, code quality, naming conventions, function design, comments best practices, formatting standards, or needs guidance on clean code principles from Robert C. Martin.
version: 1.0.0
author: Aura Core Team
---

# Clean Code Principles Reference Guide

This guide summarizes the fundamental principles from Robert C. Martin's "Clean Code". The goal of clean code is to create code that is easy to read, understand, and maintain.

## 1. Meaningful Names

The name of a variable, function, or class should answer: why it exists, what it does, and how it is used.

### Guidelines

- **Use Intention-Revealing Names**: The name should tell what it does
  - Bad: `int d;` // elapsed time in days
  - Good: `int days_since_creation;`

- **Avoid Disinformation**: Don't use names that mislead
  - Don't call a list `account_list` unless it's actually a `List`

- **Make Meaningful Distinctions**: Different names should have different meanings
  - Bad: `ProductInfo`, `ProductData` (what's the difference?)
  - Good: `ProductSpecification`, `ProductShippingDetails`

- **Use Pronounceable and Searchable Names**: Long names are better than cryptic abbreviations
  - Bad: `genymdhms` (generate year, month, day, hour, minute, second)
  - Good: `generate_timestamp()`

- **Class Names Should Be Nouns**: `Customer`, `Account`, `PaymentProcessor`
- **Method Names Should Be Verbs**: `post_payment()`, `delete_user()`

## 2. Functions

Functions are the first line of organization in any program.

### Guidelines

- **Small**: Functions should be small. Ideally no more than 5-10 lines
- **Do One Thing (SRP for Functions)**: Functions should do one thing, do it well, and do it only
- **Single Level of Abstraction**: Code within a function should be at the same abstraction level
- **Use Descriptive Names**: The longer and more descriptive the name, the better
- **Fewer Arguments**: Zero arguments is ideal, then one, then two. Avoid three or more
- **No Side Effects**: Function should only do what it promises, nothing hidden
- **Output Arguments Are Confusing**: Prefer returning a value over modifying an argument

## 3. Comments

Comments are not inherently "good". Often they compensate for failure to express something in code.

### Guidelines

- **Comments Lie**: They are not compiled, so they become outdated
- **Prefer Expressive Code Over Comments**:
  - Bad: `# Check if user is over 18` followed by `if user.age > 18:`
  - Good: `if is_user_adult(user):`

### Acceptable Comments

- **Legal Comments**: Copyrights, etc.
- **Explanation of Intent**: Why a design decision was made
- **Clarification**: Clarifying external library code
- **Warning Comments**: `# Warning! Running this test deletes the database!`
- **TODO Comments**: For work that needs to be done

## 4. Formatting

Formatting is about communication. Well-formatted code is easy to read.

### Guidelines

- **Be Consistent**: Use one set of formatting rules consistently
- **Use Automatic Tools**: Adopt a code formatter (e.g., `black` for Python)
- **Vertical Proximity**: Related code should appear close vertically
- **Vertical Distance**: Separate concepts with blank lines
- **Indentation**: Crucial for showing hierarchy and code blocks

## 5. Objects and Data Structures

- **Hide Internal Structure (Abstraction)**: Objects should expose behavior and hide internal data
- **Data Structures vs Objects**:
  - Data Structures expose data and have no significant behavior
  - Objects hide data and expose behavior

- **Law of Demeter ("Don't Talk to Strangers")**: A method `f` of class `C` should only call methods of:
  1. Class `C` itself
  2. An object created by `f`
  3. An object passed as argument to `f`
  4. An object in an instance variable of `C`

  - **Violation**: `get_profile().get_address().get_city()` (train wreck)
  - **Fix**: `get_customer_city()` - the main object provides the service you need
