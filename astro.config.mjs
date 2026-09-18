import { defineConfig } from "astro/config";

// https://astro.build/config
export default defineConfig({
  trailingSlash: "never",
  build: { format: "file" },

  markdown: {
    shikiConfig: {
      // Dual themes emit --shiki-light / --shiki-dark custom properties instead
      // of inline colours, so src/styles/editorial.css owns the code-block
      // background in both colour schemes.
      themes: { light: "vitesse-light", dark: "vitesse-dark" },
      defaultColor: false,
    },
  },
});
