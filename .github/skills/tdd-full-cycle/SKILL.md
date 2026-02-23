---
name: tdd-full-cycle
description: "Complete TDD Red→Green→Refactor cycle with autonomous agents for each phase. Use when implementing any new feature or bugfix following test-driven development. Covers all languages and frameworks."
risk: low
source: github/awesome-copilot
---

# TDD Full Cycle — Red → Green → Refactor

Autonomous three-phase TDD implementation using dedicated agents for each phase. Based on **TDD Red**, **TDD Green**, and **TDD Refactor** agents from github/awesome-copilot.

## The Cycle

```
RED ──► GREEN ──► REFACTOR ──► RED (next feature)
 │        │           │
 │        │           └── Clean up without breaking
 │        └── Minimal code to pass
 └── Failing tests that define behavior
```

---

## Phase 1 — RED (Write Failing Tests)

**Agent role**: Define expected behavior through tests **before** implementation.

### What RED agent does:
1. Reads the requirement/feature spec
2. Identifies all behaviors to implement (happy path + edge cases + errors)
3. Writes failing tests that precisely define each behavior
4. Verifies tests actually fail (not just compile errors)
5. Documents WHY each test exists

### RED agent rules:
- Tests must fail for the **right reason** (not import errors — actual assertion failures)
- Each test covers exactly one behavior
- Test names follow: `test_<action>_when_<condition>_should_<expected>`
- No implementation code written in this phase

### RED test template (pytest):
```python
def test_create_user_with_valid_data_should_return_201():
    """User creation with valid email and password returns HTTP 201."""
    # Arrange
    payload = {"email": "user@example.com", "password": "Secure123!"}
    
    # Act
    response = client.post("/users/", json=payload)
    
    # Assert
    assert response.status_code == 201
    assert "id" in response.json()
```

### RED checklist:
- [ ] All tests written and failing
- [ ] Failures are assertion failures, not syntax/import errors
- [ ] Edge cases covered: None input, empty string, boundary values
- [ ] Error cases covered: not found, unauthorized, validation failure
- [ ] Test intent documented in docstrings

---

## Phase 2 — GREEN (Make Tests Pass)

**Agent role**: Write the **minimal** code needed to pass all failing tests.

### What GREEN agent does:
1. Reads the failing tests
2. Identifies the minimal interface needed (function signatures, return types)
3. Implements just enough to pass — **no over-engineering**
4. Runs the test suite and iterates until all pass
5. Does NOT refactor or optimize in this phase

### GREEN agent rules:
- Write only what the tests require
- Use the simplest possible implementation
- Hardcode values if necessary to pass (refactoring comes next)
- No new functionality beyond what tests specify
- If a test is impossible to pass, question the test — don't change requirements

### GREEN implementation example:
```python
# Minimal implementation to pass test_create_user_with_valid_data_should_return_201
@router.post("/users/", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": str(user.id)}
```

### GREEN checklist:
- [ ] All previously failing tests now pass
- [ ] No previously passing tests broken
- [ ] Code compiles/runs without errors
- [ ] No business logic beyond test requirements

---

## Phase 3 — REFACTOR (Improve Without Breaking)

**Agent role**: Improve code quality while keeping all tests green.

### What REFACTOR agent does:
1. Reads the passing implementation
2. Identifies code smells (duplication, poor names, long functions, magic numbers)
3. Applies clean code principles
4. Runs tests after each change to verify nothing broke
5. Improves test quality too (not just production code)

### Refactoring targets:

**Production code:**
- Extract repeated logic into functions
- Rename variables/functions to reveal intent
- Remove magic numbers (replace with named constants)
- Apply Single Responsibility Principle
- Add proper error handling
- Optimize N+1 queries, O(n²) algorithms

**Test code:**
- Extract shared setup into fixtures
- Remove duplicate assertion logic
- Improve test names for clarity
- Add missing edge case tests discovered during implementation

### REFACTOR rules:
- Run tests after EVERY change (even small ones)
- If tests fail → revert immediately
- Refactor in small steps, not big rewrites
- Do not add new functionality during refactor

### REFACTOR checklist:
- [ ] All tests still passing after refactor
- [ ] No magic numbers or strings
- [ ] Functions have single responsibility
- [ ] Variable/method names are self-describing
- [ ] Code coverage maintained or improved
- [ ] No TODOs or dead code left

---

## Full Cycle Example

### Feature: "Add rate limiting to login endpoint"

```
RED Phase:
  test_login_exceeds_limit_should_return_429
  test_login_within_limit_should_return_200
  test_rate_limit_resets_after_window
  test_different_ips_have_independent_limits
  → All 4 tests FAILING ✓

GREEN Phase:
  Implement Redis-backed rate limiter with sliding window
  → All 4 tests PASSING ✓

REFACTOR Phase:
  - Extract RateLimiter class
  - Add configurable window/limit via environment variables
  - Improve error response format
  - Add tests for config validation
  → All tests still PASSING ✓
```

---

## Language-Specific Notes

| Language | Test Runner | Key Patterns |
|----------|-------------|-------------|
| Python | pytest | fixtures, parametrize, monkeypatch |
| TypeScript | Jest/Vitest | describe/it, beforeEach, jest.mock |
| Go | testing | t.Run, testify/assert, httptest |
| Rust | cargo test | #[cfg(test)], assert_eq!, mock_rs |
| Java | JUnit 5 | @Test, @BeforeEach, Mockito |
| C# | xUnit | [Fact], [Theory], Moq |

---

## Integration with OpenClaw

- Use with `polyglot-testing-pipeline` for the RED phase (test generation)
- Use with `agent-orchestration` — assign RED/GREEN/REFACTOR to sub-agents
- Use with `test-driven-development` skill (existing) for workflow guidance
- Use with `clean-code` skill during REFACTOR phase
