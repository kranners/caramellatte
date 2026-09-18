import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const posts = defineCollection({
  loader: glob({ base: "./src/posts", pattern: "**/*.{md,mdx}" }),
  schema: z.object({
    title: z.string(),
    /* Basename of a drawing in src/assets/titles; replaces the typeset heading. */
    titleSvg: z.string().optional(),
  }),
});

export const collections = { posts };
