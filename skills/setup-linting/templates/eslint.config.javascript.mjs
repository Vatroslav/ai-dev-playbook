// ESLint 9 flat config for a JavaScript project. Copy to the repo root as eslint.config.mjs.
// Requires: eslint @eslint/js eslint-config-prettier globals
import js from "@eslint/js";
import prettierConfig from "eslint-config-prettier";
import globals from "globals";

export default [
  { ignores: ["dist/", "build/", "coverage/", "node_modules/"] },
  js.configs.recommended,
  {
    languageOptions: {
      // Keep only the environments the code actually runs in.
      globals: { ...globals.browser, ...globals.node },
    },
  },
  // Last: turns off style rules that would fight Prettier.
  prettierConfig,
];
