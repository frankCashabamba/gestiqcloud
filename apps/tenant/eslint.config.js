import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import importPlugin from "eslint-plugin-import";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "*.config.ts",
      "*.config.js",
      "vite-env.d.ts",
      "eslint.config.js",
      "src/**/*.test.ts",
      "src/**/*.test.tsx",
      "src/**/__tests__/**",
      "src/sw.js",
    ],
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parserOptions: {
        project: ["./tsconfig.json"],
        tsconfigRootDir: import.meta.dirname,
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      import: importPlugin,
    },
    settings: {
      react: { version: "detect" },
      "import/resolver": {
        typescript: {
          project: "./tsconfig.json",
        },
      },
    },
    rules: {
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,

      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/explicit-module-boundary-types": "off",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "off",
      "jsx-a11y/anchor-is-valid": "off",
      "jsx-a11y/click-events-have-key-events": "off",
      "jsx-a11y/no-static-element-interactions": "off",
      "jsx-a11y/label-has-associated-control": "off",
      "jsx-a11y/no-autofocus": "off",
      "no-empty": "off",
      "no-case-declarations": "error",
      "no-useless-escape": "error",
      "prefer-const": "error",
      "react/no-unescaped-entities": "off",
      "@typescript-eslint/no-empty-object-type": "off",
      "@typescript-eslint/no-require-imports": "off",

      "no-restricted-imports": [
        "off",
        {
          patterns: [
            {
              group: ["../../*"],
              message:
                "Avoid deep relative imports. Use alias imports like @shared/, @ui/, @assets/, etc.",
            },
          ],
        },
      ],

      "import/order": [
        "off",
        {
          groups: [
            "builtin",
            "external",
            "internal",
            ["parent", "sibling", "index"],
            "type",
          ],
          pathGroups: [
            { pattern: "react", group: "builtin", position: "before" },
            { pattern: "react-dom/**", group: "builtin", position: "before" },
            { pattern: "@ui/**", group: "internal", position: "before" },
            { pattern: "@shared/**", group: "internal", position: "before" },
            { pattern: "@assets/**", group: "internal", position: "before" },
            { pattern: "@pwa/**", group: "internal", position: "before" },
            { pattern: "@endpoints/**", group: "internal", position: "before" },
            { pattern: "@api-types/**", group: "internal", position: "before" },
          ],
          pathGroupsExcludedImportTypes: ["react", "react-dom"],
          "newlines-between": "always",
          alphabetize: { order: "asc", caseInsensitive: true },
        },
      ],
      "import/no-duplicates": "off",
    },
  }
);
