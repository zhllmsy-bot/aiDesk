import { addons } from "storybook/manager-api";
import { create } from "storybook/theming";

addons.setConfig({
  theme: create({
    base: "dark",
    brandTitle: "ai-desk design system",
    brandUrl: "https://github.com",
  }),
});
