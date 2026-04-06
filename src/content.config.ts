import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const posts = defineCollection({
  loader: glob({ base: "./src/pages/posts", pattern: "**/*.{md,mdx}" }),
  schema: z.object({
    id: z.string(),
    title: z.string(),
  }),
});

export const collections = { posts };
