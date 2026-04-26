const strictTokenProperties = [
  "/color$/",
  "/^background/",
  "/^padding/",
  "/^margin/",
  "/^font-size/",
  "/^border-radius/",
  "/^box-shadow/",
  "z-index",
];

export default {
  plugins: ["stylelint-declaration-strict-value"],
  rules: {
    "color-no-hex": true,
    "declaration-no-important": true,
    "no-descending-specificity": true,
    "selector-max-specificity": "0,3,0",
    "scale-unlimited/declaration-strict-value": [
      strictTokenProperties,
      {
        disableFix: true,
        ignoreFunctions: true,
        ignoreKeywords: ["currentColor", "inherit", "initial", "none", "transparent", "unset"],
        ignoreValues: ["0", "/^var\\(--/"],
      },
    ],
  },
};
