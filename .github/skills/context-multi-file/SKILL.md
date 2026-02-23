---
name: context-multi-file
description: "Context Architect pattern for autonomous multi-file changes. Plans and executes coordinated changes across multiple files by mapping dependencies, identifying impact, and applying changes in correct order. Use when refactoring, renaming, or implementing features that span multiple files."
risk: medium
source: github/awesome-copilot
---

# Context Architect — Multi-File Autonomous Changes

Plan and execute coordinated changes across multiple files while respecting dependencies and avoiding conflicts. Based on the **Context Architect** agent from github/awesome-copilot.

## When to Use

- Renaming a function/class/type used in 5+ files
- Refactoring a module interface that many files import
- Implementing a feature that requires changes in model + service + controller + tests
- Migrating from one library to another across the whole codebase
- Adding a new required field to a data model and updating all usages

## Core Process

```
1. SCAN     — Map all files that need changing
2. ANALYZE  — Build dependency graph, find change order
3. PLAN     — Create ordered change manifest
4. EXECUTE  — Apply changes bottom-up (leaves first)
5. VALIDATE — Verify nothing broke
```

---

## Stage 1 — SCAN

**Identify all affected files:**

```
Query: "Where is UserService used?"
→ src/controllers/user.controller.ts
→ src/routes/user.routes.ts
→ src/middleware/auth.middleware.ts
→ tests/unit/user.controller.spec.ts
→ tests/integration/user.flow.spec.ts
→ src/admin/user.admin.ts
```

**Categories of changes:**
| Type | Description |
|------|-------------|
| **Direct** | File contains the thing being changed |
| **Import** | File imports from changed module |
| **Type** | File uses the changed type/interface |
| **Test** | File tests the changed code |
| **Config** | File references via string (routes, config) |

---

## Stage 2 — ANALYZE

Build a dependency graph to determine change order:

```
UserService (CORE — change first)
    ↑ imported by
    ├── auth.middleware.ts (depends on UserService)
    ├── user.controller.ts (depends on UserService)
    │       ↑ imported by
    │       └── user.routes.ts (depends on controller)
    └── admin/user.admin.ts (depends on UserService)
         ↑ imported by
         └── admin/routes.ts

Tests (change last — after production code):
    ├── user.controller.spec.ts
    └── user.flow.spec.ts
```

**Change order (bottom-up):**
1. `UserService` (core)
2. `auth.middleware.ts`, `user.admin.ts` (direct dependents)
3. `user.controller.ts` (depends on middleware)
4. `user.routes.ts`, `admin/routes.ts` (top-level)
5. Test files (last)

---

## Stage 3 — PLAN

Create a detailed change manifest:

```yaml
change_manifest:
  goal: "Add pagination to UserService.getAll()"
  
  changes:
    - file: src/services/user.service.ts
      type: modify
      changes:
        - "Add PaginationOptions parameter to getAll()"
        - "Return PaginatedResult<User> instead of User[]"
        - "Add corresponding method to IUserService interface"
    
    - file: src/controllers/user.controller.ts
      type: modify
      depends_on: [user.service.ts]
      changes:
        - "Extract page/limit from query params"
        - "Pass PaginationOptions to service.getAll()"
        - "Return paginated response with metadata"
    
    - file: src/models/pagination.model.ts
      type: create
      changes:
        - "Create PaginationOptions interface"
        - "Create PaginatedResult<T> generic interface"
    
    - file: tests/unit/user.controller.spec.ts
      type: modify
      depends_on: [user.controller.ts]
      changes:
        - "Update mock for service.getAll() to return PaginatedResult"
        - "Add tests for pagination parameters"
```

---

## Stage 4 — EXECUTE

Apply changes in dependency order:

### Pre-execution checkpoint:
```bash
git stash  # or git commit --allow-empty -m "checkpoint: before multi-file change"
```

### Per-file execution:
1. Read current file content
2. Apply change (replace, insert, or create)
3. Verify file compiles/parses correctly
4. Move to next file

### If a change fails:
```
Error in user.controller.ts: Type 'User[]' not assignable to 'PaginatedResult<User>'
→ Re-read change manifest
→ Was pagination.model.ts created successfully?
→ Was user.service.ts updated first?
→ Fix the dependency, retry
```

---

## Stage 5 — VALIDATE

After all changes applied:

```bash
# TypeScript
npx tsc --noEmit

# Linting
npx eslint src/ --ext .ts

# Tests
npx jest --no-coverage

# If API project:
# Start server and run smoke tests
```

Expected output:
```
✅ TypeScript: 0 errors
✅ ESLint: 0 warnings  
✅ Tests: 47 passed, 0 failed
✅ New tests added: 3
```

---

## Conflict Prevention Rules

1. **Never edit the same file twice in one pass** — plan all changes to a file upfront
2. **Imports first, exports last** — change what's imported before what imports it
3. **Types before implementations** — update interfaces/types first
4. **Tests last** — always update after production code
5. **One concept at a time** — don't mix unrelated changes in a single multi-file operation

---

## Change Patterns Reference

### Pattern: Rename Symbol
```
1. Find all usages (grep/LSP)
2. Update declaration
3. Update all references (alphabetical by file)
4. Run tests
```

### Pattern: Extract Interface
```
1. Create new interface file
2. Add interface to existing class
3. Update all injection points to use interface
4. Update tests to mock interface
```

### Pattern: Add Required Parameter
```
1. Add parameter with default value (backward compatible)
2. Update all callers to pass explicit value
3. Remove default value (make it required)
4. Verify no callers missed
```

---

## Integration with OpenClaw

- Use with `agent-orchestration` — Context Architect is the planning sub-agent
- Use with `code-refactoring-refactor-clean` for the actual refactoring logic
- Use with `polyglot-testing-pipeline` to update tests after multi-file changes
- Use with `tdd-full-cycle` when the multi-file change is feature-driven
