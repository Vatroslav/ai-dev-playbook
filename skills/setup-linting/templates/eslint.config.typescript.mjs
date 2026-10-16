// ESLint 9 flat config for a TypeScript project. Copy to the repo root as eslint.config.mjs.
// Requires: eslint @eslint/js typescript-eslint eslint-config-prettier
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import prettierConfig from "eslint-config-prettier";

export default [
  { ignores: ["dist/", "build/", "coverage/", "node_modules/", ".next/"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  // Last: turns off style rules that would fight Prettier.
  prettierConfig,
];
