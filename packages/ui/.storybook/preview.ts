import type { Preview } from "@storybook/react-vite";

import "../styles.css";

const withTheme: Preview["decorators"][number] = (Story, context) => {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = String(context.globals.theme ?? "midnight");
  }

  return Story();
};

const preview: Preview = {
  decorators: [withTheme],
  parameters: {
    a11y: {
      test: "error",
    },
    backgrounds: {
      default: "midnight",
      values: [
        { name: "midnight", value: "#10110f" },
        { name: "dawn", value: "#f2efe7" },
      ],
    },
    layout: "padded",
  },
  globalTypes: {
    theme: {
      description: "Workspace theme",
      toolbar: {
        icon: "mirror",
        items: [
          { title: "Midnight", value: "midnight" },
          { title: "Dawn", value: "dawn" },
        ],
      },
    },
  },
  initialGlobals: {
    theme: "midnight",
  },
};

export default preview;
