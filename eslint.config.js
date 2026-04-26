const tseslint = require("typescript-eslint");

function normalizedFilename(context) {
  return context.filename.replaceAll("\\", "/");
}

function sourceCode(context) {
  return context.sourceCode ?? context.getSourceCode();
}

function featureNameFor(filename) {
  const parts = filename.split("/");
  const index = parts.indexOf("features");
  return index >= 0 ? parts[index + 1] : undefined;
}

const aiDeskUiRules = {
  "no-ai-ui-escape-hatches": {
    meta: {
      type: "problem",
      messages: {
        arbitraryTailwind: "Tailwind arbitrary values require a token or ADR-backed class.",
        cjk: "Hard-coded CJK UI copy is not allowed; route copy through i18n.",
        tsAny: "Do not use `as any`; fix the type boundary instead.",
        tsSuppress: "Do not suppress TypeScript diagnostics.",
      },
    },
    create(context) {
      return {
        Program(node) {
          const text = sourceCode(context).getText();
          const checks = [
            {
              messageId: "arbitraryTailwind",
              pattern: /\b[a-z][a-z0-9-]*-\[[^\]]+\]/,
            },
            { messageId: "cjk", pattern: /[\u3400-\u9fff]/ },
            { messageId: "tsAny", pattern: /\bas\s+any\b/ },
            {
              messageId: "tsSuppress",
              pattern: /\/\/\s*@ts-(ignore|expect-error)|\/\*\s*@ts-(ignore|expect-error)/,
            },
          ];
          for (const check of checks) {
            if (check.pattern.test(text)) {
              context.report({ node, messageId: check.messageId });
            }
          }
        },
      };
    },
  },
  "no-cross-feature-import": {
    meta: {
      type: "problem",
      messages: {
        crossFeature:
          "Cross-feature imports must move through lib/ or packages/ui instead of reaching into another feature.",
      },
    },
    create(context) {
      const currentFeature = featureNameFor(normalizedFilename(context));
      return {
        ImportDeclaration(node) {
          if (!currentFeature || typeof node.source.value !== "string") {
            return;
          }
          const match = node.source.value.match(/^@\/features\/([^/]+)\//);
          if (match?.[1] && match[1] !== currentFeature) {
            context.report({ node, messageId: "crossFeature" });
          }
        },
      };
    },
  },
  "no-direct-radix-in-web": {
    meta: {
      type: "problem",
      messages: {
        directRadix:
          "apps/web must use @ai-desk/ui primitives instead of importing Radix directly.",
      },
    },
    create(context) {
      const filename = normalizedFilename(context);
      return {
        ImportDeclaration(node) {
          if (
            filename.includes("/apps/web/") &&
            typeof node.source.value === "string" &&
            node.source.value.startsWith("@radix-ui/react-")
          ) {
            context.report({ node, messageId: "directRadix" });
          }
        },
      };
    },
  },
  "no-direct-fetch-outside-client": {
    meta: {
      type: "problem",
      messages: {
        directFetch: "Use webFetch/apiFetch from apps/web/lib/api-client instead of fetch().",
      },
    },
    create(context) {
      const filename = normalizedFilename(context);
      const isApiClient = filename.endsWith("/apps/web/lib/api-client.ts");
      return {
        CallExpression(node) {
          if (!isApiClient && node.callee.type === "Identifier" && node.callee.name === "fetch") {
            context.report({ node, messageId: "directFetch" });
          }
        },
      };
    },
  },
  "no-handrolled-ui-primitives": {
    meta: {
      type: "problem",
      messages: {
        img: "Use next/image or a design-system media primitive instead of <img>.",
        inlineStyle: "Move inline styles to tokens/classes.",
        manualDialog: 'Use the Dialog primitive instead of role="dialog".',
      },
    },
    create(context) {
      return {
        JSXAttribute(node) {
          if (node.name.type !== "JSXIdentifier") {
            return;
          }
          if (node.name.name === "style") {
            context.report({ node, messageId: "inlineStyle" });
          }
          if (
            node.name.name === "role" &&
            node.value?.type === "Literal" &&
            node.value.value === "dialog"
          ) {
            context.report({ node, messageId: "manualDialog" });
          }
        },
        JSXOpeningElement(node) {
          if (node.name.type === "JSXIdentifier" && node.name.name === "img") {
            context.report({ node, messageId: "img" });
          }
        },
      };
    },
  },
};

module.exports = [
  {
    ignores: [
      "**/.next/**",
      "**/dist/**",
      "**/node_modules/**",
      "**/coverage/**",
      "**/playwright-report/**",
      "**/test-results/**",
      "apps/api/.venv/**",
      "packages/contracts/api/src/generated/**",
    ],
  },
  {
    files: ["apps/web/**/*.{ts,tsx}", "packages/ui/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        sourceType: "module",
      },
    },
    plugins: {
      "ai-desk-ui": {
        rules: aiDeskUiRules,
      },
    },
    rules: {
      "ai-desk-ui/no-ai-ui-escape-hatches": "error",
      "ai-desk-ui/no-cross-feature-import": "error",
      "ai-desk-ui/no-direct-fetch-outside-client": "error",
      "ai-desk-ui/no-direct-radix-in-web": "error",
      "ai-desk-ui/no-handrolled-ui-primitives": "error",
    },
  },
];
