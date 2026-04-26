const tseslint = require("typescript-eslint");

function normalizedFilename(context) {
  return context.filename.replaceAll("\\", "/");
}

function sourceCode(context) {
  return context.sourceCode ?? context.getSourceCode();
}

function staticClassNameFromAttributes(attributes) {
  const className = attributes.find(
    (attribute) =>
      attribute.type === "JSXAttribute" &&
      attribute.name.type === "JSXIdentifier" &&
      attribute.name.name === "className",
  );
  if (!className) {
    return "";
  }
  if (className.value?.type === "Literal" && typeof className.value.value === "string") {
    return className.value.value;
  }
  if (className.value?.type === "JSXExpressionContainer") {
    const expression = className.value.expression;
    if (expression.type === "Literal" && typeof expression.value === "string") {
      return expression.value;
    }
    if (expression.type === "TemplateLiteral") {
      return expression.quasis.map((quasi) => quasi.value.raw).join(" ");
    }
  }
  return "";
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
        rawI18nString:
          "Hard-coded CJK, smart punctuation, or emoji UI copy is not allowed; route copy through i18n.",
        tsAny: "Do not use `as any`; fix the type boundary instead.",
        tsSuppress: "Do not suppress TypeScript diagnostics.",
      },
    },
    create(context) {
      function checkClassName(node, value) {
        if (typeof value === "string" && /\b[a-z][a-z0-9-]*-\[[^\]]+\]/.test(value)) {
          context.report({ node, messageId: "arbitraryTailwind" });
        }
      }

      function checkRawUiString(node, value) {
        if (typeof value !== "string") {
          return;
        }
        if (/[\u3400-\u9fff，。；！？“”‘’—–]|\p{Extended_Pictographic}/u.test(value)) {
          context.report({ node, messageId: "rawI18nString" });
        }
      }

      return {
        Program(node) {
          for (const comment of sourceCode(context).getAllComments()) {
            if (/@ts-(ignore|expect-error)/.test(comment.value)) {
              context.report({ node: comment, messageId: "tsSuppress" });
            }
          }
        },
        JSXAttribute(node) {
          if (node.name.type !== "JSXIdentifier" || node.name.name !== "className") {
            return;
          }

          if (node.value?.type === "Literal") {
            checkClassName(node.value, node.value.value);
          }

          if (node.value?.type === "JSXExpressionContainer") {
            const expression = node.value.expression;
            if (expression.type === "Literal") {
              checkClassName(expression, expression.value);
            }
            if (expression.type === "TemplateLiteral") {
              for (const quasi of expression.quasis) {
                checkClassName(quasi, quasi.value.raw);
              }
            }
          }
        },
        JSXText(node) {
          checkRawUiString(node, node.value);
        },
        Literal(node) {
          checkRawUiString(node, node.value);
        },
        TSAnyKeyword(node) {
          context.report({ node, messageId: "tsAny" });
        },
        TSAsExpression(node) {
          if (node.typeAnnotation.type === "TSAnyKeyword") {
            context.report({ node, messageId: "tsAny" });
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
  "no-raw-button": {
    meta: {
      type: "problem",
      messages: {
        rawButton:
          "Use Button or ButtonLink from @ai-desk/ui instead of a raw interactive element.",
      },
    },
    create(context) {
      const filename = normalizedFilename(context);
      if (!filename.includes("/apps/web/")) {
        return {};
      }

      return {
        JSXOpeningElement(node) {
          if (node.name.type === "JSXIdentifier" && node.name.name === "button") {
            context.report({ node, messageId: "rawButton" });
            return;
          }

          if (node.name.type !== "JSXIdentifier" || node.name.name !== "a") {
            return;
          }

          const role = node.attributes.find(
            (attribute) =>
              attribute.type === "JSXAttribute" &&
              attribute.name.type === "JSXIdentifier" &&
              attribute.name.name === "role" &&
              attribute.value?.type === "Literal" &&
              attribute.value.value === "button",
          );
          if (role) {
            context.report({ node, messageId: "rawButton" });
          }
        },
      };
    },
  },
  "no-raw-input": {
    meta: {
      type: "problem",
      messages: {
        rawInput: "Use Input, TextField, SearchInput, Textarea, or Select from @ai-desk/ui.",
      },
    },
    create(context) {
      const filename = normalizedFilename(context);
      if (!filename.includes("/apps/web/")) {
        return {};
      }

      return {
        JSXOpeningElement(node) {
          if (
            node.name.type === "JSXIdentifier" &&
            ["input", "select", "textarea"].includes(node.name.name)
          ) {
            context.report({ node, messageId: "rawInput" });
          }
        },
      };
    },
  },
  "no-raw-card": {
    meta: {
      type: "problem",
      messages: {
        rawCard:
          "Use Card, StatCard, SurfaceNote, or EmptyState from @ai-desk/ui for framed surfaces.",
      },
    },
    create(context) {
      const filename = normalizedFilename(context);
      const shouldEnforce =
        filename.includes("/apps/web/features/review/") ||
        filename.includes("/apps/web/components/layout/") ||
        filename.endsWith("/apps/web/features/projects/components/audit-canvas-screen.tsx");
      if (!shouldEnforce) {
        return {};
      }

      return {
        JSXOpeningElement(node) {
          if (
            node.name.type !== "JSXIdentifier" ||
            !["article", "div", "section"].includes(node.name.name)
          ) {
            return;
          }
          const className = staticClassNameFromAttributes(node.attributes);
          if (
            /\b[\w-]*card[\w-]*\b/.test(className) ||
            (/\bborder\b/.test(className) && /\bp-\d/.test(className))
          ) {
            context.report({ node, messageId: "rawCard" });
          }
        },
      };
    },
  },
  "require-focus-visible": {
    meta: {
      type: "problem",
      messages: {
        focusVisible:
          "Interactive elements outside @ai-desk/ui must include a focus-visible treatment.",
      },
    },
    create(context) {
      const filename = normalizedFilename(context);
      if (!filename.includes("/apps/web/")) {
        return {};
      }

      return {
        JSXOpeningElement(node) {
          if (node.name.type !== "JSXIdentifier") {
            return;
          }

          const isAnchor =
            node.name.name === "a" &&
            node.attributes.some(
              (attribute) =>
                attribute.type === "JSXAttribute" &&
                attribute.name.type === "JSXIdentifier" &&
                attribute.name.name === "href",
            );

          const isInteractiveRole = node.attributes.some(
            (attribute) =>
              attribute.type === "JSXAttribute" &&
              attribute.name.type === "JSXIdentifier" &&
              attribute.name.name === "role" &&
              attribute.value?.type === "Literal" &&
              ["button", "tab"].includes(String(attribute.value.value)),
          );

          if (!isAnchor && !isInteractiveRole) {
            return;
          }

          const className = staticClassNameFromAttributes(node.attributes);
          if (!/\bfocus-visible:/.test(className)) {
            context.report({ node, messageId: "focusVisible" });
          }
        },
      };
    },
  },
  "no-raw-segmented-control": {
    meta: {
      type: "problem",
      messages: {
        rawSegmentedControl:
          "Use SegmentedControl from @ai-desk/ui instead of hand-rolled button groups.",
      },
    },
    create(context) {
      const filename = normalizedFilename(context);
      if (!filename.includes("/apps/web/")) {
        return {};
      }

      function isRawInteractive(element) {
        if (element.type !== "JSXElement" || element.openingElement.name.type !== "JSXIdentifier") {
          return false;
        }
        const name = element.openingElement.name.name;
        if (name === "button") {
          return true;
        }
        if (name !== "a") {
          return false;
        }
        return element.openingElement.attributes.some(
          (attribute) =>
            attribute.type === "JSXAttribute" &&
            attribute.name.type === "JSXIdentifier" &&
            attribute.name.name === "role" &&
            attribute.value?.type === "Literal" &&
            attribute.value.value === "button",
        );
      }

      return {
        JSXElement(node) {
          const interactiveChildren = node.children.filter(
            (child) => child.type === "JSXElement" && isRawInteractive(child),
          );
          if (interactiveChildren.length >= 3) {
            context.report({ node, messageId: "rawSegmentedControl" });
          }
        },
      };
    },
  },
  "no-non-lucide-icons": {
    meta: {
      type: "problem",
      messages: {
        iconImport: "Use lucide-react as the single icon source for UI icons.",
      },
    },
    create(context) {
      return {
        ImportDeclaration(node) {
          if (typeof node.source.value !== "string") {
            return;
          }
          if (
            /(^|\/)(react-icons|heroicons|phosphor-react|@mui\/icons-material|@tabler\/icons)/.test(
              node.source.value,
            )
          ) {
            context.report({ node, messageId: "iconImport" });
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
      "ai-desk-ui/no-non-lucide-icons": "error",
      "ai-desk-ui/no-raw-button": "error",
      "ai-desk-ui/no-raw-card": "error",
      "ai-desk-ui/no-raw-input": "error",
      "ai-desk-ui/no-raw-segmented-control": "error",
      "ai-desk-ui/require-focus-visible": "error",
    },
  },
];
