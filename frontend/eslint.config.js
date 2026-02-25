import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import prettier from 'eslint-config-prettier'
import pluginPrettier from 'eslint-plugin-prettier'
import globals from 'globals'

export default [
  // Global ignores
  {
    ignores: ['node_modules/', 'dist/', 'coverage/'],
  },

  // Base JS recommended rules
  js.configs.recommended,

  // Vue 3 recommended rules (flat config)
  ...pluginVue.configs['flat/recommended'],

  // Prettier - disable conflicting ESLint rules
  prettier,

  // Project-specific overrides
  {
    files: ['src/**/*.{js,vue}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
    },
    plugins: {
      prettier: pluginPrettier,
    },
    rules: {
      // Prettier integration - report formatting issues as ESLint errors
      'prettier/prettier': 'warn',

      // Allow console.log - this is a dev tool
      'no-console': 'off',

      // Allow single-word component names (e.g., OFOView.vue, Dashboard.vue)
      'vue/multi-word-component-names': 'off',

      // Allow unused vars prefixed with underscore
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    },
  },
]
