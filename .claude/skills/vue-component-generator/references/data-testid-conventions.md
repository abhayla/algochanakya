# data-testid Conventions for Vue Components

All interactive Vue components MUST include `data-testid` attributes for E2E testing.

**For complete documentation, see:** `.claude/skills/e2e-test-generator/references/data-testid-conventions.md`

---

## Quick Reference

### Convention: `[screen]-[component]-[element]`

**Examples:**
```vue
<!-- Positions screen, Exit modal component -->
<div data-testid="positions-exit-modal">
  <input data-testid="positions-exit-modal-price-input" />
  <select data-testid="positions-exit-modal-type-dropdown">
    <option data-testid="positions-exit-modal-type-option-market">Market</option>
  </select>
  <button data-testid="positions-exit-modal-submit-button">Submit</button>
</div>
```

---

## Element Naming

| Element Type | Suffix |
|--------------|--------|
| Button | `-button` |
| Input field | `-input` |
| Dropdown/Select | `-dropdown` |
| Checkbox | `-checkbox` |
| Radio button | `-radio` |
| Link | `-link` |
| Modal/Dialog | `-modal` |
| Container/Wrapper | `-container` |
| Card | `-card` |
| Row | `-row` |
| Item in list | `-item` |

---

## Dynamic testid for Lists

```vue
<template>
  <div
    v-for="(item, index) in items"
    :key="item.id"
    :data-testid="`myscreen-mycomponent-item-${index}`"
  >
    <button :data-testid="`myscreen-mycomponent-item-${index}-edit-button`">
      Edit
    </button>
  </div>
</template>
```

---

## Modal Components

```vue
<template>
  <!-- Modal container -->
  <div data-testid="myscreen-mymodal">
    <!-- Backdrop -->
    <div
      @click="handleClose"
      data-testid="myscreen-mymodal-backdrop"
    ></div>

    <!-- Modal content -->
    <div data-testid="myscreen-mymodal-container">
      <button data-testid="myscreen-mymodal-close-button">×</button>
      <button data-testid="myscreen-mymodal-submit-button">Submit</button>
      <button data-testid="myscreen-mymodal-cancel-button">Cancel</button>
    </div>
  </div>
</template>
```

---

## Dropdown Options

```vue
<template>
  <select data-testid="myscreen-mycomponent-type-dropdown">
    <option
      v-for="option in options"
      :key="option.value"
      :data-testid="`myscreen-mycomponent-type-option-${option.value}`"
    >
      {{ option.label }}
    </option>
  </select>
</template>
```

---

## Rules

1. **All interactive elements** need data-testid
2. **Use kebab-case** for all testid values
3. **Be specific** - Include screen, component, and element names
4. **Dynamic IDs** - Use template literals for list items
5. **Consistent suffixes** - Use standard suffixes (-button, -input, etc.)
6. **No spaces** - Use hyphens to separate words
7. **Descriptive names** - Make it clear what the element is

---

## Anti-Patterns

### ❌ WRONG

```vue
<!-- Too generic -->
<button data-testid="button">Submit</button>

<!-- Missing screen name -->
<input data-testid="price-input" />

<!-- Using camelCase -->
<div data-testid="myComponent">

<!-- Missing testid -->
<button @click="submit">Submit</button>
```

### ✅ RIGHT

```vue
<!-- Specific and descriptive -->
<button data-testid="strategy-builder-submit-button">Submit</button>

<!-- Includes screen and component -->
<input data-testid="strategy-builder-leg-price-input" />

<!-- Uses kebab-case -->
<div data-testid="strategy-builder-leg-row">

<!-- Has testid -->
<button @click="submit" data-testid="strategy-builder-submit-button">
  Submit
</button>
```
